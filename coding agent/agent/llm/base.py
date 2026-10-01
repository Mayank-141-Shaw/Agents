from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolCallRequest(BaseModel):
    id: str = Field(default_factory=lambda: "call_0")
    name: str
    arguments: Dict[str, Any]

class Message(BaseModel):
    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCallRequest]] = None

class LLMResponse(BaseModel):
    content: str
    tool_calls: List[ToolCallRequest] = Field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None

class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Send chat messages to the model and return structured response."""
        pass
