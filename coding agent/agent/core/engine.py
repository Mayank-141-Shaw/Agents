import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, Callable
from agent.config import AgentConfig, get_config
from agent.core.context import ContextManager
from agent.core.logger import SessionLogger
from agent.llm.base import BaseLLMProvider, LLMResponse
from agent.llm.gemini import GeminiProvider
from agent.llm.ollama import OllamaProvider
from agent.llm.openai_compatible import OpenAICompatibleProvider
from agent.tools.base import ToolRegistry, default_registry, ToolResult

class AgentEngine:
    """Core autonomous agent decision and tool execution engine."""

    def __init__(self, config: Optional[AgentConfig] = None, registry: Optional[ToolRegistry] = None):
        self.config = config or get_config()
        self.registry = registry or default_registry
        self.provider = self._init_provider()
        self.context = ContextManager(workspace_dir=self.config.workspace_dir)
        self.logger = SessionLogger(logs_dir=self.config.logs_dir)

    def _init_provider(self) -> BaseLLMProvider:
        prov = self.config.provider.lower()
        if prov == "gemini":
            if not self.config.google_api_key:
                raise ValueError("Google API key is missing. Please provide your Google API key to use the agent.")
            return GeminiProvider(
                api_key=self.config.google_api_key,
                model=self.config.model_name
            )
        elif prov == "ollama":
            return OllamaProvider(
                base_url=self.config.ollama_base_url,
                model=self.config.model_name
            )
        else:
            return OpenAICompatibleProvider(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
                model=self.config.model_name
            )

    async def run_step(self, user_input: str, step_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> str:
        """Run full autonomous agent loop until resolution or max steps reached."""
        self.context.add_user_message(user_input)
        self.logger.log_step("user_input", {"content": user_input})

        tools_schema = self.registry.get_openai_schemas()
        final_answer = ""

        for step in range(1, self.config.max_steps + 1):
            if step_callback:
                step_callback({"type": "step_start", "step": step, "max_steps": self.config.max_steps})

            messages = self.context.get_messages()
            
            try:
                response: LLMResponse = await self.provider.chat(
                    messages=messages,
                    tools=tools_schema,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
            except Exception as e:
                err_msg = f"LLM provider error at step {step}: {str(e)}"
                self.logger.log_step("llm_error", {"error": err_msg})
                if step_callback:
                    step_callback({"type": "error", "error": err_msg})
                return f"Execution error: {err_msg}"

            assistant_text = response.content or ""
            tool_calls = response.tool_calls

            self.context.add_assistant_message(assistant_text, tool_calls=tool_calls if tool_calls else None)
            self.logger.log_step("assistant_response", {
                "text": assistant_text,
                "tool_calls": [tc.dict() for tc in tool_calls]
            })

            if step_callback:
                step_callback({
                    "type": "assistant_thinking",
                    "step": step,
                    "content": assistant_text,
                    "tool_calls_count": len(tool_calls)
                })

            if not tool_calls:
                # No tool calls requested, model completed response
                final_answer = assistant_text
                break

            # Execute requested tool calls sequentially
            for tc in tool_calls:
                if step_callback:
                    step_callback({"type": "tool_executing", "tool_name": tc.name, "arguments": tc.arguments})

                tool_res: ToolResult = await self.registry.execute(tc.name, tc.arguments)
                
                output = tool_res.output if tool_res.success else f"ERROR: {tool_res.error}"
                self.context.add_tool_result(tc.name, tc.id, output)
                self.logger.log_step("tool_result", {
                    "tool_name": tc.name,
                    "success": tool_res.success,
                    "output": output[:500]
                })

                if step_callback:
                    step_callback({
                        "type": "tool_completed",
                        "tool_name": tc.name,
                        "success": tool_res.success,
                        "output": output[:300]
                    })

        return final_answer or "Task completed."
