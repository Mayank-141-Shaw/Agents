import os
import re
import ast
import asyncio
from pathlib import Path
from typing import Optional, List
from agent.tools.base import default_registry, ToolResult

@default_registry.register(
    name="grep_search",
    description="Search for a text pattern or regex across files in a directory.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text query or regex pattern to search for"},
            "directory": {"type": "string", "description": "Directory path to search in (defaults to current directory)"},
            "file_pattern": {"type": "string", "description": "Glob pattern to filter files e.g. '*.py'"}
        },
        "required": ["query"]
    }
)
async def grep_search(query: str, directory: str = ".", file_pattern: Optional[str] = None) -> ToolResult:
    try:
        dir_path = Path(directory).resolve()
        if not dir_path.exists():
            return ToolResult(success=False, output="", error=f"Directory not found: {directory}")

        pattern = re.compile(query, re.IGNORECASE)
        matches = []

        files_to_check = dir_path.rglob(file_pattern) if file_pattern else dir_path.rglob("*")

        for file_path in files_to_check:
            if file_path.is_file() and not any(part.startswith(".") for part in file_path.parts):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                rel_path = file_path.relative_to(dir_path)
                                matches.append(f"{rel_path}:{line_num}: {line.strip()}")
                                if len(matches) >= 100:
                                    break
                except Exception:
                    continue
            if len(matches) >= 100:
                break

        if not matches:
            return ToolResult(success=True, output=f"No matches found for query: '{query}'")
        
        output = "\n".join(matches)
        if len(matches) >= 100:
            output += "\n... (results capped at 100 matches)"
        return ToolResult(success=True, output=output)
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Grep search failed: {str(e)}")


@default_registry.register(
    name="web_search",
    description="Search for a prompt or query on the web using DuckDuckGo.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Search prompt or query string"},
            "max_results": {"type": "integer", "description": "Maximum number of search results to return (default 5)"}
        },
        "required": ["prompt"]
    }
)
async def web_search(prompt: str, max_results: int = 5) -> ToolResult:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return ToolResult(
            success=False,
            output="",
            error="duckduckgo_search package is not installed. Run 'pip install duckduckgo-search' to enable web search."
        )

    try:
        def _fetch():
            with DDGS() as ddgs:
                return list(ddgs.text(prompt, max_results=max_results))

        results = await asyncio.to_thread(_fetch)

        if not results:
            return ToolResult(success=True, output=f"No web search results found for prompt: '{prompt}'")

        formatted = []
        for idx, res in enumerate(results, 1):
            title = res.get("title", "No Title")
            href = res.get("href") or res.get("link", "")
            body = res.get("body") or res.get("snippet", "")
            formatted.append(f"{idx}. {title}\n   URL: {href}\n   Snippet: {body}")

        output = f"Web Search Results for '{prompt}':\n\n" + "\n\n".join(formatted)
        return ToolResult(success=True, output=output, data={"results": results})
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Web search failed: {str(e)}")


@default_registry.register(
    name="find_files",
    description="Find files matching a glob pattern (e.g. '**/*.py', 'src/*.ts').",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern"},
            "directory": {"type": "string", "description": "Search directory (defaults to .)"}
        },
        "required": ["pattern"]
    }
)
async def find_files(pattern: str, directory: str = ".") -> ToolResult:
    try:
        dir_path = Path(directory).resolve()
        matches = [str(p.relative_to(dir_path)) for p in dir_path.glob(pattern) if p.is_file()]
        if not matches:
            return ToolResult(success=True, output=f"No files matched pattern: '{pattern}'")
        return ToolResult(success=True, output="\n".join(sorted(matches)))
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Find files failed: {str(e)}")

@default_registry.register(
    name="parse_ast_symbols",
    description="Extract classes, functions, docstrings, and line numbers from a Python source file using AST.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to Python file"}
        },
        "required": ["path"]
    }
)
async def parse_ast_symbols(path: str) -> ToolResult:
    try:
        file_path = Path(path).resolve()
        if not file_path.exists():
            return ToolResult(success=False, output="", error=f"File not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)
        symbols = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or "No docstring"
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                symbols.append(f"CLASS {node.name} (Line {node.lineno})\n  Doc: {doc[:80]}\n  Methods: {', '.join(methods)}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or "No docstring"
                args = [a.arg for a in node.args.args]
                is_async = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                symbols.append(f"FUNCTION {is_async}{node.name}({', '.join(args)}) (Line {node.lineno})\n  Doc: {doc[:80]}")

        if not symbols:
            return ToolResult(success=True, output="No top-level class or function symbols found.")

        return ToolResult(success=True, output="\n\n".join(symbols))
    except Exception as e:
        return ToolResult(success=False, output="", error=f"AST parsing failed for {path}: {str(e)}")
