import httpx
from typing import List, Dict, Any, Optional
from agent.llm.base import BaseLLMProvider, Message, LLMResponse, ToolCallRequest
from agent.llm.parser import parse_tool_calls_from_text

class OllamaProvider(BaseLLMProvider):
    """Client for local Ollama instance."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:latest"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> LLMResponse:
        payload_messages = []
        for m in messages:
            msg_dict = {"role": m.role, "content": m.content}
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments
                        }
                    } for tc.tc in m.tool_calls
                ]
            payload_messages.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if tools:
            # Transform OpenAI schemas to Ollama tools format
            ollama_tools = []
            for t in tools:
                if "function" in t:
                    ollama_tools.append({"type": "function", "function": t["function"]})
            payload["tools"] = ollama_tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(f"{self.base_url}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()

        message_obj = data.get("message", {})
        content = message_obj.get("content", "")
        tool_calls: List[ToolCallRequest] = []

        # Native tool calls return
        if "tool_calls" in message_obj and message_obj["tool_calls"]:
            for idx, tc in enumerate(message_obj["tool_calls"]):
                fn = tc.get("function", {})
                tool_calls.append(ToolCallRequest(
                    id=f"ollama_{idx}",
                    name=fn.get("name", ""),
                    arguments=fn.get("arguments", {})
                ))

        # Fallback text parsing if model returned tool calls inside text
        if not tool_calls and content:
            cleaned_content, fallback_calls = parse_tool_calls_from_text(content)
            if fallback_calls:
                content = cleaned_content
                tool_calls = fallback_calls

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response=data
        )
