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
    provider: str = Field(default="gemini", description="Default provider: gemini, ollama, openai, anthropic")
    model_name: str = Field(default="gemini-3.5-flash-lite", description="LLM model identifier")
    google_api_key: Optional[str] = Field(default=None, description="In-memory Google Gemini API Key for current session (never persisted)")
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

_SESSION_CONFIG: Optional[AgentConfig] = None

def get_config() -> AgentConfig:
    """Retrieve the active session configuration, resolving keys from session memory or env vars."""
    global _SESSION_CONFIG
    if _SESSION_CONFIG is None:
        _SESSION_CONFIG = AgentConfig()
    
    # Fallback to env vars if not explicitly set in session RAM
    if not _SESSION_CONFIG.google_api_key:
        _SESSION_CONFIG.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not _SESSION_CONFIG.openai_api_key:
        _SESSION_CONFIG.openai_api_key = os.getenv("OPENAI_API_KEY")

    return _SESSION_CONFIG

def set_session_config(config: AgentConfig) -> AgentConfig:
    """Set or update the global session configuration object."""
    global _SESSION_CONFIG
    _SESSION_CONFIG = config
    return _SESSION_CONFIG

def set_session_api_key(api_key: str, provider: Optional[str] = None, model: Optional[str] = None) -> AgentConfig:
    """Update active session API key, provider, and model in session storage."""
    cfg = get_config()
    if provider:
        cfg.provider = provider
    if model:
        cfg.model_name = model
    
    if api_key:
        cfg.google_api_key = api_key
        cfg.openai_api_key = api_key

    return set_session_config(cfg)
