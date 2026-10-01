import json
import re
from typing import List, Dict, Any, Tuple
from agent.llm.base import ToolCallRequest

def parse_tool_calls_from_text(text: str) -> Tuple[str, List[ToolCallRequest]]:
    """
    Extract tool calls embedded in plain text / markdown blocks or XML tags.
    Supports formats:
    1. <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    2. ```json\n{"tool": "...", "args": {...}}\n```
    3. {"tool_call": {"name": "...", "arguments": {...}}}
    """
    tool_calls: List[ToolCallRequest] = []
    cleaned_text = text

    # Pattern 1: <tool_call> ... </tool_call>
    xml_pattern = r"<tool_call>\s*({.*?})\s*</tool_call>"
    matches = re.findall(xml_pattern, text, re.DOTALL)
    for idx, match in enumerate(matches):
        try:
            data = json.loads(match)
            name = data.get("name") or data.get("tool")
            args = data.get("arguments") or data.get("args") or {}
            if name:
                tool_calls.append(ToolCallRequest(id=f"fallback_{idx}", name=name, arguments=args))
        except Exception:
            continue

    if tool_calls:
        cleaned_text = re.sub(xml_pattern, "", cleaned_text, flags=re.DOTALL).strip()
        return cleaned_text, tool_calls

    # Pattern 2: ```json block containing tool call JSON
    codeblock_pattern = r"```(?:json)?\s*({[\s\S]*?" + r"(?:tool|name)[\s\S]*?})\s*```"
    matches = re.findall(codeblock_pattern, text)
    for idx, match in enumerate(matches):
        try:
            data = json.loads(match)
            name = data.get("name") or data.get("tool") or data.get("function")
            args = data.get("arguments") or data.get("args") or data.get("parameters") or {}
            if name:
                tool_calls.append(ToolCallRequest(id=f"fallback_{idx}", name=name, arguments=args))
        except Exception:
            continue

    if tool_calls:
        cleaned_text = re.sub(r"```(?:json)?\s*{[\s\S]*?}\s*```", "", cleaned_text).strip()
        return cleaned_text, tool_calls

    return cleaned_text, tool_calls
