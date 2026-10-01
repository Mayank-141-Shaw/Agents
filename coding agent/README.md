# Local AI Coding Agent

An autonomous, local AI coding agent powered by Python, supporting local models (via Ollama / LM Studio) and cloud models (OpenAI, Anthropic, Gemini). Features a full tool suite (filesystem operations, code search, AST symbol parsing, terminal execution, Git tools, task planner), rich interactive CLI, and Web UI dashboard.

---

## 🚀 Quick Start & Installation

### 1. Requirements & Setup
Ensure you have Python 3.10+ installed.

```bash
# Navigate to the project directory
cd "agents/coding agent"

# Create a virtual environment (optional but recommended)
python -m venv venv

# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies and local package in editable mode
pip install -e .
```

Alternatively, install dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration & Environment Variables

Create a `.env` file in the root directory (or pass environment variables):

```env
# Default Provider & Model Configuration
CODING_AGENT_PROVIDER=ollama
CODING_AGENT_MODEL_NAME=qwen2.5-coder:latest
CODING_AGENT_OLLAMA_BASE_URL=http://localhost:11434

# For OpenAI / OpenAI-compatible Endpoints:
# CODING_AGENT_PROVIDER=openai
# CODING_AGENT_OPENAI_API_KEY=sk-your-api-key
# CODING_AGENT_OPENAI_BASE_URL=https://api.openai.com/v1
# CODING_AGENT_MODEL_NAME=gpt-4o

# Loop Guardrails & Security Settings
CODING_AGENT_MAX_STEPS=30
CODING_AGENT_ALLOW_TERMINAL_EXECUTION=true
```

---

## 💻 Commands for Running the Agent

### 1. Interactive Terminal CLI
Start the Rich interactive terminal interface:

```bash
# Using installed package entrypoint:
coding-agent cli

# Or using Python module execution:
python -m agent.main cli
```

---

### 2. Web UI Dashboard Server
Launch the FastAPI Web UI dashboard with real-time WebSockets telemetry:

```bash
# Default (runs on http://127.0.0.1:8000)
coding-agent web

# Specify custom host and port:
coding-agent web --host 0.0.0.0 --port 8080

# Or via python module:
python -m agent.main web --port 8000
```
Open your browser and navigate to `http://localhost:8000` to interact with the agent dashboard.

---

### 3. Single Task Execution
Run a single coding task or prompt directly from the command line without opening interactive mode:

```bash
# Run with default Ollama provider:
coding-agent run "Create a python script that fetches current weather using httpx"

# Run specifying provider and model flags:
coding-agent run "Refactor tests in tests/test_tools.py" --provider openai --model gpt-4o

# Or via python module:
python -m agent.main run "Fix bugs in search.py"
```

---

### 4. Running Unit Tests
Run the pytest test suite to verify tools and parsers:

```bash
pytest tests/
```

---

## 🛠 Available Agent Tools

| Tool Name | Description |
|---|---|
| `read_file` | Read file lines with line numbers and line range filters |
| `write_file` | Create or overwrite files and auto-create parent directories |
| `edit_file_exact` | Perform exact string snippet replacement in files |
| `list_directory` | List contents of a directory (single level or recursive) |
| `grep_search` | Search text or regex patterns across codebase files |
| `find_files` | Find files matching glob patterns (e.g. `**/*.py`) |
| `parse_ast_symbols` | Extract classes, function signatures, line numbers, & docstrings using AST |
| `run_shell_command` | Execute terminal commands asynchronously with security guardrails |
| `git_status` | View short repository Git status |
| `git_diff` | View working tree or cached Git diffs |
| `git_commit` | Commit staged changes with commit message |
| `update_task_list` | Maintain active subtask status (pending, in_progress, completed) |
| `get_task_status` | Retrieve current subtask list |

---

## 📂 Project Structure

```
coding agent/
├── SPEC.md                      # Specification & Rules
├── ARCHITECTURE_PLAN.md         # System Architecture Document
├── README.md                    # Usage & Command Guide
├── pyproject.toml               # Package build configuration
├── requirements.txt             # Python dependencies
├── agent/
│   ├── main.py                  # Typer CLI Entrypoint
│   ├── config.py                # Pydantic Settings Configuration
│   ├── core/
│   │   ├── engine.py            # ReAct Decision Loop Engine
│   │   ├── context.py           # Sliding context & prompt manager
│   │   └── logger.py            # JSONL session transcript logger
│   ├── llm/
│   │   ├── base.py              # LLM Provider abstract interface
│   │   ├── ollama.py            # Local Ollama REST client
│   │   ├── openai_compatible.py # OpenAI / Cloud API client
│   │   └── parser.py            # Fallback tool call parser
│   ├── tools/
│   │   ├── base.py              # Tool registry & decorator
│   │   ├── filesystem.py        # File read/write/edit tools
│   │   ├── search.py            # Grep, glob, AST search tools
│   │   ├── terminal.py          # Terminal runner with safety guards
│   │   ├── git.py               # Git operations
│   │   └── task_planner.py      # Subtask tracking tool
│   └── ui/
│       ├── cli.py               # Rich terminal interactive UI
│       └── server.py            # FastAPI Web UI server & WebSockets
└── tests/
    └── test_tools.py            # Pytest suite
```
