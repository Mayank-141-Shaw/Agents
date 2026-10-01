import json
import inspect
from typing import Callable, Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    """Result returned from a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True

class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    fn: Callable = Field(exclude=True)

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool definition to OpenAI function call schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class ToolRegistry:
    """Central registry for managing and invoking agent tools."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        """Decorator to register a function as an agent tool."""
        def decorator(func: Callable):
            tool = Tool(
                name=name,
                description=description,
                parameters=parameters,
                fn=func
            )
            self._tools[name] = tool
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' not found in registry."
            )
        try:
            if inspect.iscoroutinefunction(tool.fn):
                res = await tool.fn(**arguments)
            else:
                res = tool.fn(**arguments)
            
            if isinstance(res, ToolResult):
                return res
            elif isinstance(res, str):
                return ToolResult(success=True, output=res)
            elif isinstance(res, dict):
                return ToolResult(success=True, output=json.dumps(res, indent=2), data=res)
            else:
                return ToolResult(success=True, output=str(res))
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Exception executing tool '{name}': {str(e)}"
            )

# Global registry instance
default_registry = ToolRegistry()
