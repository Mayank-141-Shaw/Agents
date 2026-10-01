import sys
import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from agent.config import get_config, set_session_api_key
from agent.core.engine import AgentEngine

console = Console()

MODEL_CHOICES = {
    "gemini": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-8b"],
    "openai": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
    "ollama": ["qwen2.5-coder:latest", "llama3.1:latest", "deepseek-coder:latest"]
}

async def get_cli_input_async(prompt_label: str = "User > ", password: bool = False) -> str:
    """Async prompt input for active asyncio loop supporting clipboard & multi-line paste."""
    try:
        from prompt_toolkit import PromptSession
        session = PromptSession()
        res = await session.prompt_async(prompt_label, is_password=password)
        return res.strip()
    except Exception:
        if password:
            return Prompt.ask(prompt_label, password=True).strip()
        else:
            return console.input(f"[bold green]{prompt_label}[/bold green]").strip()

def render_step_callback(event: dict):
    ev_type = event.get("type")
    if ev_type == "step_start":
        step = event.get("step")
        max_s = event.get("max_steps")
        console.print(f"\n[bold blue]━━ Step {step}/{max_s} ━━[/bold blue]")
    elif ev_type == "assistant_thinking":
        content = event.get("content", "")
        if content:
            console.print(Panel(Markdown(content), title="[bold cyan]Agent Thought[/bold cyan]", border_style="cyan"))
    elif ev_type == "tool_executing":
        tool_name = event.get("tool_name")
        args = event.get("arguments", {})
        console.print(f"[bold yellow]⚙ Executing tool:[/bold yellow] [bold white]{tool_name}[/bold white] with args {args}")
    elif ev_type == "tool_completed":
        tool_name = event.get("tool_name")
        success = event.get("success")
        output = event.get("output", "")
        style = "green" if success else "bold red"
        status_text = "SUCCESS" if success else "FAILED"
        console.print(Panel(output, title=f"[{style}]Tool Output ({tool_name}: {status_text})[/{style}]", border_style=style))
    elif ev_type == "error":
        err = event.get("error")
        console.print(f"[bold red]❌ Error:[/bold red] {err}")

async def async_cli_loop(engine: AgentEngine):
    console.print(Panel.fit(
        "[bold green]Local AI Coding Agent[/bold green]\n"
        f"Provider: [cyan]{engine.config.provider}[/cyan] | Model: [yellow]{engine.config.model_name}[/yellow]\n"
        f"Workspace: [magenta]{engine.config.workspace_dir}[/magenta]",
        title="Agent Initialized",
        border_style="green"
    ))
    console.print("[dim]Type or paste your coding task below (type 'exit' or 'quit' to end session):[/dim]\n")

    while True:
        try:
            user_prompt = await get_cli_input_async("User > ")
            if not user_prompt:
                continue
            if user_prompt.lower() in ["exit", "quit"]:
                console.print("[bold yellow]Exiting Local Coding Agent. Goodbye![/bold yellow]")
                break

            console.print("[dim]Processing request...[/dim]")
            answer = await engine.run_step(user_prompt, step_callback=render_step_callback)
            console.print("[bold green]✔ Task completed.[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Session terminated by user.[/bold yellow]")
            break

def run_cli():
    config = get_config()
    
    console.print(Panel("[bold cyan]⚡ Local AI Coding Agent CLI Setup[/bold cyan]", border_style="cyan"))
    
    # 1. Select Provider
    provider = Prompt.ask(
        "Select Provider",
        choices=["gemini", "openai", "ollama"],
        default=config.provider or "gemini"
    )

    # 2. Select Model
    available_models = MODEL_CHOICES.get(provider, ["gemini-2.0-flash"])
    default_model = available_models[0]
    model = Prompt.ask(
        "Select Model",
        choices=available_models,
        default=default_model
    )

    # 3. Prompt for API key if required and not present
    key = None
    if provider == "gemini":
        key = config.google_api_key
        if not key:
            console.print(Panel("[bold yellow]🔐 Session Authentication Required[/bold yellow]\nPlease enter or paste your Google API Key for this session. It will NOT be saved to disk.", border_style="yellow"))
            key = Prompt.ask("[bold cyan]Google API Key[/bold cyan]", password=True).strip()
            if not key:
                console.print("[bold red]API Key is required to proceed. Exiting.[/bold red]")
                return
    elif provider == "openai":
        key = config.openai_api_key
        if not key:
            console.print(Panel("[bold yellow]🔐 Session Authentication Required[/bold yellow]\nPlease enter or paste your OpenAI API Key for this session. It will NOT be saved to disk.", border_style="yellow"))
            key = Prompt.ask("[bold cyan]OpenAI API Key[/bold cyan]", password=True).strip()
            if not key:
                console.print("[bold red]API Key is required to proceed. Exiting.[/bold red]")
                return

    # Set active session config
    config = set_session_api_key(api_key=key, provider=provider, model=model)

    engine = AgentEngine(config=config)
    asyncio.run(async_cli_loop(engine))

if __name__ == "__main__":
    run_cli()
