# Session-Based Google API Key Architecture Plan

## 1. Requirement Summary
- Before initiating any interaction with the agent, the user **must** provide their Google Gemini API Key.
- The API key **must NOT be saved to disk** (not written to `.env`, config files, or logs).
- The service agent operates statelessly, storing the API key purely in-memory for the active session (CLI turn / WebSocket connection).

---

## 2. Technical Design

### A. Dynamic In-Memory Configuration (`agent/config.py`)
- Add an in-memory `google_api_key: Optional[str] = None` attribute to `AgentConfig`.
- Ensure `.env` loading ignores `google_api_key` or does not write/persist it to disk.

### B. Gemini LLM Provider (`agent/llm/gemini.py` & `agent/llm/__init__.py`)
- Implement `GeminiProvider` using Google's OpenAI-compatible REST endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`) or direct Gemini v1beta REST API (`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent`).
- Pass the session Google API key dynamically via HTTP Authorization headers (`Bearer <GOOGLE_API_KEY>`) for every request in that session.

### C. CLI Session Flow (`agent/ui/cli.py` & `agent/main.py`)
- On starting `coding-agent cli` or `coding-agent run`:
  1. Check if `google_api_key` is set in memory for the current process.
  2. If missing, securely prompt the user: `Enter Google API Key (input hidden):`.
  3. Validate key presence before initializing `AgentEngine`.
  4. Ensure loggers mask or omit the API key from `.agent_logs/` JSONL transcripts.

### D. Web UI Session Flow (`agent/ui/server.py`)
- On loading the Web Dashboard (`http://localhost:8000`):
  1. Show a glassmorphism modal overlay requiring the user to enter their **Google API Key**.
  2. When the user submits the key, store it strictly in browser session memory (`sessionStorage`) and send it in the initial WebSocket handshake `init` message.
  3. The server holds the key in the active WebSocket connection state only; when the connection closes, the key is evicted from memory.

---

## 3. Implementation Files to Create/Update

1. `agent/config.py`: Add `google_api_key` memory property.
2. `agent/llm/gemini.py`: Create native `GeminiProvider`.
3. `agent/llm/__init__.py`: Export `GeminiProvider`.
4. `agent/ui/cli.py`: Add secure interactive prompt for API key before session start.
5. `agent/ui/server.py`: Add API key modal overlay in Web UI & session state in WebSocket endpoint.
6. `agent/main.py`: Add key prompt to single-run CLI command.

---

> [!IMPORTANT]
> As per Rule 2 in `SPEC.md` (*"Plan first, proceed to code only after plan is accepted"*), please review and accept this implementation plan before code modifications begin.
