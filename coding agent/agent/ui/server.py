import json
import uvicorn
import asyncio
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from agent.config import get_config, set_session_api_key, AgentConfig
from agent.core.engine import AgentEngine

class StreamRequest(BaseModel):
    user_input: str
    api_key: Optional[str] = None
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"

app = FastAPI(title="Local Coding Agent Dashboard", version="0.1.0")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Coding Agent Dashboard</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --panel-bg: #1e293b;
            --accent: #3b82f6;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
        }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            height: 95vh;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            background: var(--panel-bg);
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .container {
            display: flex;
            gap: 20px;
            flex: 1;
            overflow: hidden;
        }
        .main-chat {
            flex: 2;
            display: flex;
            flex-direction: column;
            background: var(--panel-bg);
            border-radius: 8px;
            padding: 15px;
        }
        .side-panel {
            flex: 1;
            background: var(--panel-bg);
            border-radius: 8px;
            padding: 15px;
            overflow-y: auto;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding-right: 10px;
        }
        .msg {
            padding: 10px 15px;
            border-radius: 6px;
            max-width: 85%;
            white-space: pre-wrap;
            font-size: 14px;
        }
        .msg.user {
            background: #2563eb;
            align-self: flex-end;
        }
        .msg.assistant {
            background: #334155;
            align-self: flex-start;
        }
        .msg.tool {
            background: #064e3b;
            border-left: 4px solid var(--success);
            align-self: flex-start;
            font-family: monospace;
            font-size: 12px;
        }
        .input-box {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        input[type="text"], input[type="password"], select {
            flex: 1;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #fff;
            font-size: 14px;
        }
        button {
            padding: 12px 20px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            opacity: 0.9;
        }
        .status-tag {
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            background: #334155;
        }
        /* Modal Overlay */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal {
            background: var(--panel-bg);
            padding: 30px;
            border-radius: 12px;
            width: 440px;
            border: 1px solid #475569;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }
        .modal h3 {
            margin-top: 0;
            color: #f8fafc;
        }
        .modal p {
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <!-- Key & Model Selector Modal -->
    <div id="keyModal" class="modal-overlay">
        <div class="modal">
            <h3>🔐 Session API Key & Model Configuration</h3>
            <p>Select your provider, model, and enter your API key. The key is stored purely in browser RAM (`sessionStorage`) and is <strong>never saved to disk</strong>.</p>
            <div style="display: flex; flex-direction: column; gap: 12px;">
                <label style="font-size: 12px; color: #94a3b8;">Provider</label>
                <select id="providerSelect">
                    <option value="gemini" selected>Google Gemini</option>
                    <option value="openai">OpenAI / Compatible API</option>
                    <option value="ollama">Local Ollama</option>
                </select>

                <label style="font-size: 12px; color: #94a3b8;">Model</label>
                <select id="modelSelect">
                    <option value="gemini-3.5-flash-lite" selected>Gemini 3.5 Flash Lite (Recommended)</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-2.0-flash-lite">Gemini 2.0 Flash Lite</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                    <option value="gemini-1.5-flash-8b">Gemini 1.5 Flash 8B</option>
                </select>

                <label style="font-size: 12px; color: #94a3b8;">API Key</label>
                <input type="password" id="apiKeyInput" placeholder="Enter API Key (e.g. AIzaSy...)" />
                <button type="button" id="startSessionBtn">Start Session</button>
            </div>
        </div>
    </div>

    <header>
        <h2>⚡ Local Coding Agent Dashboard</h2>
        <div>
            <button type="button" id="changeKeyBtn" style="padding: 6px 12px; font-size: 12px; margin-right: 10px;">Change Key & Model</button>
            <span class="status-tag" id="status">Disconnected</span>
        </div>
    </header>

    <div class="container">
        <div class="main-chat">
            <div id="messages"></div>
            <div class="input-box">
                <input type="text" id="userInput" placeholder="Enter coding task or instruction..." />
                <button type="button" id="sendMsgBtn">Send</button>
            </div>
        </div>

        <div class="side-panel">
            <h3>⚙ Tool Execution Telemetry</h3>
            <div id="telemetry"></div>
        </div>
    </div>

    <script type="text/javascript">
        const MODEL_MAP = {
            "gemini": [
                { id: "gemini-3.5-flash-lite", name: "Gemini 3.5 Flash Lite (Recommended)" },
                { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash " },
                { id: "gemini-2.0-flash-lite", name: "Gemini 2.0 Flash Lite" },
                { id: "gemini-1.5-flash", name: "Gemini 1.5 Flash" },
                { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro" },
                { id: "gemini-1.5-flash-8b", name: "Gemini 1.5 Flash 8B" }
            ],
            "openai": [
                { id: "gpt-4o", name: "GPT-4o" },
                { id: "gpt-4o-mini", name: "GPT-4o Mini" },
                { id: "o3-mini", name: "o3 Mini" }
            ],
            "ollama": [
                { id: "qwen2.5-coder:latest", name: "Qwen 2.5 Coder" },
                { id: "llama3.1:latest", name: "Llama 3.1" },
                { id: "deepseek-coder:latest", name: "DeepSeek Coder" }
            ]
        };

        let ws = null;
        let useSse = false;
        let sessionApiKey = sessionStorage.getItem("GOOGLE_API_KEY") || "";
        let sessionProvider = sessionStorage.getItem("session_provider") || "gemini";
        let sessionModel = sessionStorage.getItem("session_model") || "gemini-2.0-flash";

        const getMessagesDiv = () => document.getElementById('messages');
        const getTelemetryDiv = () => document.getElementById('telemetry');
        const getStatusSpan = () => document.getElementById('status');

        function updateModelOptions() {
            const provSelect = document.getElementById('providerSelect');
            const modelSelect = document.getElementById('modelSelect');
            if (!provSelect || !modelSelect) return;

            const prov = provSelect.value || sessionProvider || "gemini";
            const models = MODEL_MAP[prov] || MODEL_MAP["gemini"] || [];

            modelSelect.innerHTML = "";
            models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.innerText = m.name;
                if (m.id === sessionModel) {
                    opt.selected = true;
                }
                modelSelect.appendChild(opt);
            });
            if (modelSelect.options.length > 0 && !modelSelect.value) {
                modelSelect.selectedIndex = 0;
            }
        }

        function submitApiKey() {
            try {
                const input = document.getElementById('apiKeyInput');
                const provSelect = document.getElementById('providerSelect');
                const modelSelect = document.getElementById('modelSelect');
                
                const key = input ? input.value.trim() : "";
                const prov = provSelect ? provSelect.value : "gemini";
                const model = modelSelect ? modelSelect.value : "gemini-2.0-flash";
                
                if (!key && prov !== "ollama") {
                    alert("Please enter a valid API Key to proceed.");
                    return;
                }

                sessionApiKey = key;
                sessionProvider = prov;
                sessionModel = model;

                sessionStorage.setItem("GOOGLE_API_KEY", key);
                sessionStorage.setItem("session_provider", prov);
                sessionStorage.setItem("session_model", model);

                const keyModal = document.getElementById('keyModal');
                if (keyModal) keyModal.style.display = "none";
                
                if (ws) {
                    try { ws.close(); } catch(e) {}
                    ws = null;
                }
                initConnection();
            } catch (err) {
                console.error("submitApiKey error:", err);
                alert("Error starting session: " + err.message);
            }
        }

        function clearSessionKey() {
            sessionStorage.removeItem("GOOGLE_API_KEY");
            sessionStorage.removeItem("session_provider");
            sessionStorage.removeItem("session_model");
            sessionApiKey = "";
            const keyInput = document.getElementById('apiKeyInput');
            if (keyInput) keyInput.value = "";
            const provSelect = document.getElementById('providerSelect');
            if (provSelect) provSelect.value = "gemini";
            sessionProvider = "gemini";
            sessionModel = "gemini-2.0-flash";
            updateModelOptions();
            const keyModal = document.getElementById('keyModal');
            if (keyModal) keyModal.style.display = "flex";
            if (ws) {
                try { ws.close(); } catch(e) {}
                ws = null;
            }
            const statusSpan = getStatusSpan();
            if (statusSpan) {
                statusSpan.innerText = "Disconnected";
                statusSpan.style.background = "#334155";
            }
        }

        function initConnection() {
            const telemetryDiv = getTelemetryDiv();
            if (telemetryDiv) telemetryDiv.innerHTML = "";

            const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            try {
                const currentWs = new WebSocket(`${wsProtocol}//${location.host}/ws`);
                ws = currentWs;

                currentWs.onopen = () => {
                    const statusSpan = getStatusSpan();
                    if (statusSpan) {
                        statusSpan.innerText = "Connecting Engine (WS)...";
                        statusSpan.style.background = "#f59e0b";
                    }
                    
                    currentWs.send(JSON.stringify({
                        type: "init",
                        api_key: sessionApiKey,
                        provider: sessionProvider,
                        model: sessionModel
                    }));
                };

                currentWs.onerror = () => {
                    enableSseMode("WebSocket connection unavailable. Enabled HTTP SSE streaming.");
                };

                currentWs.onclose = () => {
                    if (!useSse) {
                        enableSseMode("Disconnected from WebSocket. Switched to HTTP SSE mode.");
                    }
                };

                currentWs.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    handleAgentEvent(data);
                };
            } catch (err) {
                enableSseMode("WebSocket not supported. Enabled HTTP SSE streaming.");
            }
        }

        function enableSseMode(reason) {
            useSse = true;
            const statusSpan = getStatusSpan();
            if (statusSpan) {
                statusSpan.innerText = `Online (${sessionProvider}: ${sessionModel}) [SSE Mode]`;
                statusSpan.style.background = "#0284c7";
            }
            appendTelemetry(`ℹ ${reason}`);
        }

        function handleAgentEvent(data) {
            const statusSpan = getStatusSpan();
            if (data.type === "init_success") {
                if (statusSpan) {
                    statusSpan.innerText = `Online (${data.provider}: ${data.model}) [WS]`;
                    statusSpan.style.background = "#065f46";
                }
                useSse = false;
                appendTelemetry(`Agent initialized with provider: ${data.provider}, model: ${data.model}`);
            } else if (data.type === "step_start") {
                appendTelemetry(`━━ Step ${data.step}/${data.max_steps} ━━`);
            } else if (data.type === "assistant_thinking") {
                appendMessage("assistant", data.content);
            } else if (data.type === "tool_executing") {
                appendTelemetry(`⚙ Tool Call: ${data.tool_name}`);
            } else if (data.type === "tool_completed") {
                appendMessage("tool", `[${data.tool_name}] ${data.output}`);
            } else if (data.type === "final_response") {
                appendTelemetry("✔ Response complete.");
            } else if (data.type === "error") {
                if (statusSpan) {
                    statusSpan.innerText = "Error";
                    statusSpan.style.background = "#991b1b";
                }
                appendMessage("assistant", `❌ Error: ${data.error}`);
            }
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const msg = input ? input.value.trim() : "";
            if (!msg) return;

            if (input) input.value = "";

            if (ws && ws.readyState === WebSocket.OPEN && !useSse) {
                appendMessage("user", msg);
                ws.send(JSON.stringify({ type: "user_message", content: msg }));
            } else {
                await sendViaSse(msg);
            }
        }

        function sendViaSse(userMsg) {
            appendMessage("user", userMsg);
            const statusSpan = getStatusSpan();
            if (statusSpan) {
                statusSpan.innerText = "Processing (SSE)...";
                statusSpan.style.background = "#3b82f6";
            }

            const query = new URLSearchParams({
                user_input: userMsg,
                api_key: sessionApiKey,
                provider: sessionProvider,
                model: sessionModel
            });

            const es = new EventSource(`/api/stream?${query}`);
            es.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleAgentEvent(data);
                    if (data.type === "final_response" || data.type === "error") {
                        es.close();
                        if (statusSpan) {
                            statusSpan.innerText = `Online (${sessionProvider}: ${sessionModel}) [SSE Mode]`;
                            statusSpan.style.background = "#0284c7";
                        }
                    }
                } catch (e) {
                    console.error("SSE parse error:", e);
                }
            };

            es.onerror = () => {
                es.close();
                if (statusSpan) {
                    statusSpan.innerText = "Error (SSE)";
                    statusSpan.style.background = "#991b1b";
                }
            };
        }

        function appendMessage(role, text) {
            if (!text) return;
            const messagesDiv = getMessagesDiv();
            if (!messagesDiv) return;
            const div = document.createElement('div');
            div.className = `msg ${role}`;
            div.innerText = text;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function appendTelemetry(text) {
            const telemetryDiv = getTelemetryDiv();
            if (!telemetryDiv) return;
            const div = document.createElement('div');
            div.style.fontSize = "12px";
            div.style.color = "#94a3b8";
            div.style.marginBottom = "5px";
            div.innerText = text;
            telemetryDiv.appendChild(div);
            telemetryDiv.scrollTop = telemetryDiv.scrollHeight;
        }

        function attachEventListeners() {
            const startBtn = document.getElementById('startSessionBtn');
            if (startBtn) {
                startBtn.onclick = submitApiKey;
                startBtn.addEventListener('click', submitApiKey);
            }
            const changeBtn = document.getElementById('changeKeyBtn');
            if (changeBtn) {
                changeBtn.onclick = clearSessionKey;
                changeBtn.addEventListener('click', clearSessionKey);
            }
            const sendBtn = document.getElementById('sendMsgBtn');
            if (sendBtn) {
                sendBtn.onclick = sendMessage;
                sendBtn.addEventListener('click', sendMessage);
            }
            const provSelect = document.getElementById('providerSelect');
            if (provSelect) {
                provSelect.onchange = updateModelOptions;
                provSelect.addEventListener('change', updateModelOptions);
            }
            const userInput = document.getElementById('userInput');
            if (userInput) {
                userInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') sendMessage();
                });
            }
        }

        function initPage() {
            attachEventListeners();
            const provSelect = document.getElementById('providerSelect');
            if (provSelect) {
                provSelect.value = sessionProvider;
            }
            updateModelOptions();

            const keyModal = document.getElementById('keyModal');
            if (sessionApiKey || sessionProvider === "ollama") {
                const keyInput = document.getElementById('apiKeyInput');
                if (keyInput) keyInput.value = sessionApiKey;
                if (keyModal) keyModal.style.display = "none";
                initConnection();
            } else {
                if (keyModal) keyModal.style.display = "flex";
            }
        }

        // Expose handlers globally on window scope
        window.updateModelOptions = updateModelOptions;
        window.submitApiKey = submitApiKey;
        window.clearSessionKey = clearSessionKey;
        window.sendMessage = sendMessage;

        // Initialize page state safely
        try {
            if (document.readyState === "loading") {
                document.addEventListener("DOMContentLoaded", initPage);
            } else {
                initPage();
            }
        } catch (err) {
            console.error("Initialization error:", err);
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get_dashboard():
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_wellknown():
    return {}

@app.api_route("/api/stream", methods=["GET", "POST"])
async def stream_agent_execution(
    user_input: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    payload: Optional[StreamRequest] = None
):
    inp = (payload.user_input if payload else user_input) or ""
    key = (payload.api_key if payload else api_key) or ""
    prov = (payload.provider if payload else provider) or "gemini"
    mdl = (payload.model if payload else model) or "gemini-2.0-flash"

    event_queue = asyncio.Queue()

    def sse_callback(event: dict):
        event_queue.put_nowait(event)

    async def event_generator():
        try:
            config = set_session_api_key(
                api_key=key,
                provider=prov,
                model=mdl
            )
            engine = AgentEngine(config=config)
            
            yield f"data: {json.dumps({'type': 'init_success', 'provider': prov, 'model': mdl})}\n\n"
            
            task = asyncio.create_task(engine.run_step(inp, step_callback=sse_callback))
            
            while not task.done() or not event_queue.empty():
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.01)
            
            final_answer = await task
            yield f"data: {json.dumps({'type': 'final_response', 'content': final_answer})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    engine: Optional[AgentEngine] = None

    def ws_callback(event: dict):
        asyncio.create_task(websocket.send_json(event))

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            
            msg_type = data.get("type")
            if msg_type == "init":
                session_key = data.get("api_key")
                provider = data.get("provider", "gemini")
                model_name = data.get("model", "gemini-2.0-flash")

                config = set_session_api_key(api_key=session_key, provider=provider, model=model_name)

                try:
                    engine = AgentEngine(config=config)
                    await websocket.send_json({
                        "type": "init_success",
                        "provider": provider,
                        "model": model_name
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "error": str(e)})

            elif msg_type == "user_message":
                user_text = data.get("content", "")
                if not engine:
                    await websocket.send_json({"type": "error", "error": "Agent engine not initialized. Please provide a valid API key."})
                    continue
                try:
                    answer = await engine.run_step(user_text, step_callback=ws_callback)
                    await websocket.send_json({"type": "final_response", "content": answer})
                except Exception as e:
                    await websocket.send_json({"type": "error", "error": f"Execution error: {str(e)}"})
    except WebSocketDisconnect:
        pass

def start_server(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_server()
