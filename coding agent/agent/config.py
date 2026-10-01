import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class AgentConfig(BaseSettings):
    """Configuration settings for the Local Coding Agent."""
    
    # Workspace & Directory Settings
    workspace_dir: Path = Field(default_factory=lambda: Path.cwd(), description="Root directory for workspace operations")
    logs_dir: Path = Field(default_factory=lambda: Path.cwd() / ".agent_logs", description="Directory for session transcripts and logs")
    
    # Provider & Model Settings
    provider: str = Field(default="ollama", description="Default provider: ollama, openai, anthropic, gemini")
    model_name: str = Field(default="qwen2.5-coder:latest", description="LLM model identifier")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Base URL for Ollama service")
    openai_api_key: Optional[str] = Field(default=None, description="API Key for OpenAI compatible endpoints")
    openai_base_url: Optional[str] = Field(default="https://api.openai.com/v1", description="OpenAI API Base URL")
    
    # Execution & Loop Guards
    max_steps: int = Field(default=30, description="Maximum ReAct loop iterations per user request")
    temperature: float = Field(default=0.2, description="Sampling temperature for code generation")
    max_tokens: int = Field(default=4096, description="Max generation tokens")
    
    # Security Guardrails
    allow_terminal_execution: bool = Field(default=True, description="Enable running shell commands")
    forbidden_commands: list[str] = Field(
        default_factory=lambda: ["rm -rf /", "mkfs", "dd ", "shutdown", "reboot", ":(){ :|:& };:"],
        description="Forbidden command patterns for safety"
    )

    class Config:
        env_prefix = "CODING_AGENT_"
        env_file = ".env"
        extra = "ignore"

def get_config() -> AgentConfig:
    return AgentConfig()
