from typing import List, Dict, Any
from agent.tools.base import default_registry, ToolResult

# In-memory active task state
_TASK_LIST: List[Dict[str, Any]] = []

@default_registry.register(
    name="update_task_list",
    description="Update the task list tracker with subtasks and their current status (pending, in_progress, completed, failed).",
    parameters={
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "failed"]}
                    },
                    "required": ["id", "description", "status"]
                }
            }
        },
        "required": ["tasks"]
    }
)
async def update_task_list(tasks: List[Dict[str, Any]]) -> ToolResult:
    global _TASK_LIST
    _TASK_LIST = tasks
    formatted = []
    for t in tasks:
        icon = "☑" if t["status"] == "completed" else ("⏳" if t["status"] == "in_progress" else "☐")
        formatted.append(f"{icon} [{t['status'].upper()}] Task {t['id']}: {t['description']}")

    output = "Task List Updated:\n" + "\n".join(formatted)
    return ToolResult(success=True, output=output, data={"tasks": _TASK_LIST})

@default_registry.register(
    name="get_task_status",
    description="Get current task list status.",
    parameters={"type": "object", "properties": {}}
)
async def get_task_status() -> ToolResult:
    if not _TASK_LIST:
        return ToolResult(success=True, output="No active tasks in tracker.")
    
    formatted = []
    for t in _TASK_LIST:
        icon = "☑" if t["status"] == "completed" else ("⏳" if t["status"] == "in_progress" else "☐")
        formatted.append(f"{icon} [{t['status'].upper()}] Task {t['id']}: {t['description']}")

    return ToolResult(success=True, output="\n".join(formatted), data={"tasks": _TASK_LIST})
