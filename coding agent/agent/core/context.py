from pathlib import Path
from typing import List, Optional, Dict, Any
from agent.llm.base import Message, ToolCallRequest

DEFAULT_SYSTEM_PROMPT = """You are an expert autonomous AI Coding Agent running locally on the user's workspace.
Your mission is to analyze codebase structure, read/edit files, execute shell commands safely, search for code, and complete software engineering tasks reliably.

Workspace Root Directory: {workspace_dir}

Operating Guidelines:
1. Always explore and inspect relevant files or search the codebase before proposing or modifying code.
2. When editing code, ensure you match existing indentation and surrounding code context accurately.
3. Keep track of complex multi-step tasks using the task planner tools.
4. Execute terminal commands when necessary to verify environment context, but avoid destructive system actions.
5. Provide clear, concise explanations of your actions and observations.
"""

class ContextManager:
    """Manages system prompt, message history, tool responses, and context pruning."""

    def __init__(self, workspace_dir: Path, custom_system_prompt: Optional[str] = None):
        self.workspace_dir = Path(workspace_dir)
        self.system_prompt = (custom_system_prompt or DEFAULT_SYSTEM_PROMPT).format(workspace_dir=str(self.workspace_dir))
        self.messages: List[Message] = [
            Message(role="system", content=self.system_prompt)
        ]

    def add_user_message(self, content: str):
        self.messages.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str, tool_calls: Optional[List[ToolCallRequest]] = None):
        self.messages.append(Message(role="assistant", content=content, tool_calls=tool_calls))

    def add_tool_result(self, tool_name: str, tool_call_id: str, output: str):
        # Truncate very long tool outputs to avoid exhausting context window
        max_len = 12000
        if len(output) > max_len:
            output = output[:max_len] + f"\n... [Tool output truncated from {len(output)} chars]"

        self.messages.append(Message(
            role="tool",
            name=tool_name,
            tool_call_id=tool_call_id,
            content=output
        ))

    def get_messages(self, max_history_messages: int = 50) -> List[Message]:
        """Return sliding window of messages, preserving system prompt at index 0."""
        if len(self.messages) <= max_history_messages:
            return self.messages
        
        system_msg = self.messages[0]
        recent_history = self.messages[-(max_history_messages - 1):]
        return [system_msg] + recent_history
