import pytest
from pathlib import Path
from agent.tools.base import ToolRegistry, ToolResult
from agent.tools.filesystem import read_file, write_file, edit_file_exact, list_directory
from agent.tools.search import grep_search, find_files, parse_ast_symbols
from agent.tools.task_planner import update_task_list, get_task_status
from agent.llm.parser import parse_tool_calls_from_text

@pytest.mark.asyncio
async def test_filesystem_tools(tmp_path: Path):
    test_file = tmp_path / "sample.py"
    
    # Test write_file
    w_res = await write_file(str(test_file), "def hello():\n    print('world')\n")
    assert w_res.success
    assert test_file.exists()

    # Test read_file
    r_res = await read_file(str(test_file))
    assert r_res.success
    assert "def hello():" in r_res.output

    # Test edit_file_exact
    e_res = await edit_file_exact(
        str(test_file),
        target_content="print('world')",
        replacement_content="print('hello world')"
    )
    assert e_res.success
    
    r_res2 = await read_file(str(test_file))
    assert "print('hello world')" in r_res2.output

@pytest.mark.asyncio
async def test_search_and_ast_tools(tmp_path: Path):
    code = '''
class Calculator:
    """A sample calculator class."""
    def add(self, a, b):
        return a + b
'''
    file_path = tmp_path / "calc.py"
    await write_file(str(file_path), code)

    # Test AST parsing
    ast_res = await parse_ast_symbols(str(file_path))
    assert ast_res.success
    assert "CLASS Calculator" in ast_res.output
    assert "add" in ast_res.output

    # Test Grep
    grep_res = await grep_search("Calculator", directory=str(tmp_path))
    assert grep_res.success
    assert "calc.py" in grep_res.output

@pytest.mark.asyncio
async def test_task_planner():
    tasks = [
        {"id": "1", "description": "Write architecture plan", "status": "completed"},
        {"id": "2", "description": "Implement tools", "status": "in_progress"}
    ]
    u_res = await update_task_list(tasks)
    assert u_res.success

    s_res = await get_task_status()
    assert s_res.success
    assert "Write architecture plan" in s_res.output

def test_fallback_parser():
    sample_text = """
    I will read the file now.
    <tool_call>{"name": "read_file", "arguments": {"path": "main.py"}}</tool_call>
    """
    cleaned, calls = parse_tool_calls_from_text(sample_text)
    assert len(calls) == 1
    assert calls[0].name == "read_file"
    assert calls[0].arguments["path"] == "main.py"
