import os
from pathlib import Path
from typing import Optional, Dict, Any
from agent.tools.base import default_registry, ToolResult

@default_registry.register(
    name="read_file",
    description="Read lines from a text file with line numbers. Optionally specify start_line and end_line.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path to read"},
            "start_line": {"type": "integer", "description": "1-indexed starting line number (optional)"},
            "end_line": {"type": "integer", "description": "1-indexed ending line number (optional)"}
        },
        "required": ["path"]
    }
)
async def read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> ToolResult:
    try:
        file_path = Path(path).resolve()
        if not file_path.exists():
            return ToolResult(success=False, output="", error=f"File not found: {path}")
        if file_path.is_dir():
            return ToolResult(success=False, output="", error=f"Path is a directory, not a file: {path}")
        
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        s_line = max(1, start_line) if start_line else 1
        e_line = min(total_lines, end_line) if end_line else total_lines

        snippet = []
        for idx in range(s_line - 1, e_line):
            snippet.append(f"{idx + 1:4d}: {lines[idx]}")

        output = "".join(snippet)
        header = f"--- {file_path.name} (Lines {s_line}-{e_line} of {total_lines}) ---\n"
        return ToolResult(success=True, output=header + output)
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Error reading file {path}: {str(e)}")

@default_registry.register(
    name="write_file",
    description="Write complete contents to a file. Creates file and parent directories if they don't exist.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to create or overwrite"},
            "content": {"type": "string", "description": "The exact text content to write"}
        },
        "required": ["path", "content"]
    }
)
async def write_file(path: str, content: str) -> ToolResult:
    try:
        file_path = Path(path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return ToolResult(success=True, output=f"Successfully wrote {len(content)} bytes to {file_path}")
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Error writing to file {path}: {str(e)}")

@default_registry.register(
    name="edit_file_exact",
    description="Replace an exact target snippet in a file with replacement content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to modify"},
            "target_content": {"type": "string", "description": "Exact text string to be replaced"},
            "replacement_content": {"type": "string", "description": "New replacement string"}
        },
        "required": ["path", "target_content", "replacement_content"]
    }
)
async def edit_file_exact(path: str, target_content: str, replacement_content: str) -> ToolResult:
    try:
        file_path = Path(path).resolve()
        if not file_path.exists():
            return ToolResult(success=False, output="", error=f"File not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if target_content not in content:
            return ToolResult(
                success=False, 
                output="", 
                error=f"Target content not found in {path}. Make sure whitespace and line breaks match exactly."
            )
        
        count = content.count(target_content)
        if count > 1:
            return ToolResult(
                success=False,
                output="",
                error=f"Target content matched {count} times in {path}. Provide a larger surrounding snippet for uniqueness."
            )

        new_content = content.replace(target_content, replacement_content, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return ToolResult(success=True, output=f"Successfully updated {path}")
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Error editing file {path}: {str(e)}")

@default_registry.register(
    name="list_directory",
    description="List files and subdirectories in a directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path to list"},
            "recursive": {"type": "boolean", "description": "Whether to list recursively (default false)"}
        },
        "required": ["path"]
    }
)
async def list_directory(path: str, recursive: bool = False) -> ToolResult:
    try:
        dir_path = Path(path).resolve()
        if not dir_path.exists():
            return ToolResult(success=False, output="", error=f"Directory not found: {path}")
        if not dir_path.is_dir():
            return ToolResult(success=False, output="", error=f"Path is not a directory: {path}")

        results = []
        if recursive:
            for p in dir_path.rglob("*"):
                rel = p.relative_to(dir_path)
                kind = "DIR" if p.is_dir() else "FILE"
                results.append(f"[{kind}] {rel}")
        else:
            for p in dir_path.iterdir():
                kind = "DIR" if p.is_dir() else "FILE"
                results.append(f"[{kind}] {p.name}")

        return ToolResult(success=True, output="\n".join(results) or "Directory is empty.")
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Error listing directory {path}: {str(e)}")
