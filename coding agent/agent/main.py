import asyncio
import typer
from agent.config import get_config, set_session_api_key
from agent.core.engine import AgentEngine
from agent.ui.cli import run_cli, render_step_callback
from agent.ui.server import start_server

app = typer.Typer(help="Local AI Coding Agent CLI & Server")

@app.command()
def cli():
    """Launch the interactive terminal CLI agent session."""
    run_cli()

@app.command()
def web(
    host: str = typer.Option("127.0.0.1", help="Host address"),
    port: int = typer.Option(8000, help="Port number")
):
    """Launch the FastAPI Web UI dashboard server."""
    typer.echo(f"Starting Local Coding Agent Web Dashboard on http://{host}:{port}")
    start_server(host=host, port=port)

@app.command()
def run(
    instruction: str = typer.Argument(..., help="Coding task or instruction to execute"),
    provider: str = typer.Option("gemini", help="LLM provider: gemini, ollama, or openai"),
    model: str = typer.Option("gemini-2.0-flash", help="LLM model name")
):
    """Run a single coding task instruction directly from the command line."""
    config = get_config()
    config.provider = provider
    config.model_name = model
    
    if provider == "gemini" and not config.google_api_key:
        api_key = typer.prompt("🔑 Enter Google API Key (input hidden)", hide_input=True)
        if not api_key:
            typer.echo("Error: Google API key is required.")
            raise typer.Exit(1)
        config = set_session_api_key(api_key, provider=provider, model=model)
    elif provider == "openai" and not config.openai_api_key:
        api_key = typer.prompt("🔑 Enter OpenAI API Key (input hidden)", hide_input=True)
        if not api_key:
            typer.echo("Error: OpenAI API key is required.")
            raise typer.Exit(1)
        config = set_session_api_key(api_key, provider=provider, model=model)
    else:
        config = set_session_api_key(api_key=config.google_api_key or config.openai_api_key, provider=provider, model=model)

    engine = AgentEngine(config=config)
    typer.echo(f"Running task with provider={provider}, model={model}...")
    
    result = asyncio.run(engine.run_step(instruction, step_callback=render_step_callback))
    typer.echo("\n--- Result ---")
    typer.echo(result)

if __name__ == "__main__":
    app()
