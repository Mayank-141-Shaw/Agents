import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.status import Status
from agent.config import get_config
from agent.core.engine import AgentEngine

console = Console()

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
    console.print("[dim]Type your coding task below (type 'exit' or 'quit' to end session):[/dim]\n")

    while True:
        try:
            user_prompt = console.input("[bold green]User > [/bold green]").strip()
            if not user_prompt:
                continue
            if user_prompt.lower() in ["exit", "quit"]:
                console.print("[bold yellow]Exiting Local Coding Agent. Goodbye![/bold yellow]")
                break

            console.print("[dim]Processing request...[/dim]")
            answer = await engine.run_step(user_prompt, step_callback=render_step_callback)
            console.print(Panel(Markdown(answer), title="[bold green]Final Response[/bold green]", border_style="green"))
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Session terminated by user.[/bold yellow]")
            break

def run_cli():
    config = get_config()
    engine = AgentEngine(config=config)
    asyncio.run(async_cli_loop(engine))

if __name__ == "__main__":
    run_cli()
