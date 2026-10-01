import asyncio
import os
from agent.tools.base import default_registry, ToolResult
from agent.config import get_config

async def _exec_git(args: list[str]) -> ToolResult:
    config = get_config()
    try:
        cmd = ["git"] + args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(config.workspace_dir)
        )
        stdout, stderr = await process.communicate()
        out_str = stdout.decode("utf-8", errors="replace").strip()
        err_str = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            return ToolResult(success=False, output="", error=f"Git command failed: {err_str or out_str}")

        return ToolResult(success=True, output=out_str or "Command completed with no output.")
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Error executing git command: {str(e)}")

@default_registry.register(
    name="git_status",
    description="Get current Git status of the repository.",
    parameters={"type": "object", "properties": {}}
)
async def git_status() -> ToolResult:
    return await _exec_git(["status", "--short"])

@default_registry.register(
    name="git_diff",
    description="Show git diff for unstaged or staged changes.",
    parameters={
        "type": "object",
        "properties": {
            "staged": {"type": "boolean", "description": "If true, show staged changes diff"}
        }
    }
)
async def git_diff(staged: bool = False) -> ToolResult:
    args = ["diff", "--cached"] if staged else ["diff"]
    return await _exec_git(args)

@default_registry.register(
    name="git_commit",
    description="Commit staged changes with a message.",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message"}
        },
        "required": ["message"]
    }
)
async def git_commit(message: str) -> ToolResult:
    return await _exec_git(["commit", "-m", message])
