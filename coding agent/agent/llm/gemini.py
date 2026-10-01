import json
import httpx
from typing import List, Dict, Any, Optional
from agent.config import get_config
from agent.llm.base import BaseLLMProvider, Message, LLMResponse, ToolCallRequest
from agent.llm.parser import parse_tool_calls_from_text

class GeminiProvider(BaseLLMProvider):
    """Client for Google Gemini REST API using in-memory session API key."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        cfg = get_config()
        resolved_key = api_key or cfg.google_api_key
        if not resolved_key:
            raise ValueError("Google API key is required for GeminiProvider. Please enter your API key.")
        self.api_key = resolved_key
        model_req = model or cfg.model_name
        if "2.5" in model_req:
            model_req = "gemini-2.0-flash"
        self.model = model_req
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        params = {"key": self.api_key}

        # Try Endpoint Strategy 1: OpenAI compatibility at /openai/chat/completions
        # Try Endpoint Strategy 2: OpenAI compatibility at /chat/completions
        endpoints = [
            f"{self.base_url}/openai/chat/completions",
            f"{self.base_url}/chat/completions"
        ]

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
                            "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments)
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

        async with httpx.AsyncClient(timeout=120.0) as client:
            res = None
            last_err = None
            for url in endpoints:
                try:
                    response = await client.post(url, json=payload, headers=headers, params=params)
                    if response.status_code == 404:
                        continue
                    if response.status_code in (401, 403):
                        raise ValueError("Invalid or unauthorized Google API Key provided.")
                    response.raise_for_status()
                    res = response.json()
                    break
                except httpx.HTTPStatusError as err:
                    last_err = err
                    if err.response.status_code == 404:
                        continue
                    raise

            # If OpenAI endpoints returned 404, fallback to native Gemini REST endpoint
            if res is None:
                res = await self._native_gemini_fallback(client, messages, tools, temperature, max_tokens)

        choice = res.get("choices", [{}])[0]
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
            raw_response=res
        )

    async def _native_gemini_fallback(
        self,
        client: httpx.AsyncClient,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Native Gemini generateContent REST fallback handler."""
        contents = []
        system_instruction = None

        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content}]}
            elif m.role == "user":
                contents.append({"role": "user", "parts": [{"text": m.content}]})
            elif m.role == "assistant":
                parts = []
                if m.content:
                    parts.append({"text": m.content})
                contents.append({"role": "model", "parts": parts})
            elif m.role == "tool":
                contents.append({"role": "function", "parts": [{"text": f"[{m.name}] {m.content}"}]})

        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if system_instruction:
            body["systemInstruction"] = system_instruction

        models_to_try = [self.model, "gemini-2.0-flash", "gemini-1.5-flash"]
        res = None
        for m_name in models_to_try:
            model_clean = m_name if m_name.startswith("models/") else f"models/{m_name}"
            url = f"{self.base_url}/{model_clean}:generateContent"
            params = {"key": self.api_key}
            headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
            
            resp = await client.post(url, json=body, headers=headers, params=params)
            if resp.status_code == 404:
                continue
            if resp.status_code in (401, 403):
                raise ValueError("Invalid or unauthorized Google API Key provided.")
            resp.raise_for_status()
            res = resp.json()
            break

        if res is None:
            raise ValueError(f"Google Gemini model '{self.model}' not found or unavailable for your API key.")
        data = res

        # Convert native response into OpenAI-style payload for unified parsing
        text_out = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                if "text" in p:
                    text_out += p["text"]

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": text_out
                    }
                }
            ]
        }
