import asyncio
import shlex
import os
from agent.tools.base import default_registry, ToolResult
from agent.config import get_config

@default_registry.register(
    name="run_shell_command",
    description="Execute a shell command asynchronously and return stdout/stderr output. Has safety guardrails.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout_seconds": {"type": "integer", "description": "Timeout in seconds (default 30)"}
        },
        "required": ["command"]
    }
)
async def run_shell_command(command: str, timeout_seconds: int = 30) -> ToolResult:
    config = get_config()
    
    if not config.allow_terminal_execution:
        return ToolResult(success=False, output="", error="Terminal command execution is disabled in agent configuration.")

    # Guardrail check
    for forbidden in config.forbidden_commands:
        if forbidden.lower() in command.lower():
            return ToolResult(
                success=False, 
                output="", 
                error=f"Command execution blocked by safety filter: contains forbidden phrase '{forbidden}'"
            )

    try:
        # Use appropriate shell based on OS
        is_win = os.name == "nt"
        shell_cmd = f"powershell.exe -Command \"{command}\"" if is_win else command

        process = await asyncio.create_subprocess_shell(
            shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(config.workspace_dir)
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            return ToolResult(success=False, output="", error=f"Command timed out after {timeout_seconds} seconds.")

        out_str = stdout.decode("utf-8", errors="replace").strip()
        err_str = stderr.decode("utf-8", errors="replace").strip()
        exit_code = process.returncode

        output_combined = f"Exit Code: {exit_code}\n"
        if out_str:
            output_combined += f"--- STDOUT ---\n{out_str}\n"
        if err_str:
            output_combined += f"--- STDERR ---\n{err_str}\n"

        return ToolResult(
            success=(exit_code == 0),
            output=output_combined,
            data={"exit_code": exit_code, "stdout": out_str, "stderr": err_str}
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to execute command '{command}': {str(e)}")
