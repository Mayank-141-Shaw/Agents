import json
import httpx
from typing import List, Dict, Any, Optional
from agent.config import get_config
from agent.llm.base import BaseLLMProvider, Message, LLMResponse, ToolCallRequest
from agent.llm.parser import parse_tool_calls_from_text

class OpenAICompatibleProvider(BaseLLMProvider):
    """Client for OpenAI and OpenAI-compatible endpoints (LM Studio, vLLM, DeepSeek, Groq)."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        cfg = get_config()
        self.api_key = api_key or cfg.openai_api_key or "sk-no-key-required"
        self.base_url = (base_url or cfg.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model or cfg.model_name

    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> LLMResponse:
        payload_messages = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role, "content": m.content}
            if m.name:
                msg_dict["name"] = m.name
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": str(tc.arguments) if isinstance(tc.arguments, str) else json.dumps(tc.arguments)
                        }
                    } for tc in m.tool_calls
                ]
            payload_messages.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            res.raise_for_status()
            data = res.json()

        choice = data.get("choices", [{}])[0]
        message_obj = choice.get("message", {})
        content = message_obj.get("content") or ""
        tool_calls: List[ToolCallRequest] = []

        if "tool_calls" in message_obj and message_obj["tool_calls"]:
            for tc in message_obj["tool_calls"]:
                fn = tc.get("function", {})
                args_raw = fn.get("arguments", "{}")
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except Exception:
                    args = {}
                tool_calls.append(ToolCallRequest(
                    id=tc.get("id", "call_0"),
                    name=fn.get("name", ""),
                    arguments=args
                ))

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
