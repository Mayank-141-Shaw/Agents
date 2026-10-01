import json
import uvicorn
import asyncio
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from agent.config import get_config, set_session_api_key, AgentConfig
from agent.core.engine import AgentEngine

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
                <select id="providerSelect" onchange="updateModelOptions()">
                    <option value="gemini" selected>Google Gemini</option>
                    <option value="openai">OpenAI / Compatible API</option>
                    <option value="ollama">Local Ollama</option>
                </select>

                <label style="font-size: 12px; color: #94a3b8;">Model</label>
                <select id="modelSelect"></select>

                <label style="font-size: 12px; color: #94a3b8;">API Key</label>
                <input type="password" id="apiKeyInput" placeholder="Enter API Key (e.g. AIzaSy...)" />
                <button onclick="submitApiKey()">Start Session</button>
            </div>
        </div>
    </div>

    <header>
        <h2>⚡ Local Coding Agent Dashboard</h2>
        <div>
            <button style="padding: 6px 12px; font-size: 12px; margin-right: 10px;" onclick="clearSessionKey()">Change Key & Model</button>
            <span class="status-tag" id="status">Disconnected</span>
        </div>
    </header>

    <div class="container">
        <div class="main-chat">
            <div id="messages"></div>
            <div class="input-box">
                <input type="text" id="userInput" placeholder="Enter coding task or instruction..." onkeydown="if(event.key==='Enter') sendMessage()" />
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>

        <div class="side-panel">
            <h3>⚙ Tool Execution Telemetry</h3>
            <div id="telemetry"></div>
        </div>
    </div>

    <script>
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
        let sessionApiKey = sessionStorage.getItem("GOOGLE_API_KEY") || "";
        let sessionProvider = sessionStorage.getItem("session_provider") || "gemini";
        let sessionModel = sessionStorage.getItem("session_model") || "gemini-2.0-flash";

        const messagesDiv = document.getElementById('messages');
        const telemetryDiv = document.getElementById('telemetry');
        const statusSpan = document.getElementById('status');
        const keyModal = document.getElementById('keyModal');

        window.addEventListener("DOMContentLoaded", () => {
            updateModelOptions();
            if (sessionApiKey) {
                document.getElementById('apiKeyInput').value = sessionApiKey;
                document.getElementById('providerSelect').value = sessionProvider;
                updateModelOptions();
                document.getElementById('modelSelect').value = sessionModel;
                keyModal.style.display = "none";
                initWebSocket();
            } else {
                keyModal.style.display = "flex";
            }
        });

        function updateModelOptions() {
            const provSelect = document.getElementById('providerSelect');
            const modelSelect = document.getElementById('modelSelect');
            const prov = provSelect.value;
            const models = MODEL_MAP[prov] || [];

            modelSelect.innerHTML = "";
            models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.innerText = m.name;
                modelSelect.appendChild(opt);
            });
        }

        function submitApiKey() {
            const input = document.getElementById('apiKeyInput');
            const provSelect = document.getElementById('providerSelect');
            const modelSelect = document.getElementById('modelSelect');
            
            const key = input.value.trim();
            const prov = provSelect.value;
            const model = modelSelect.value;
            
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

            keyModal.style.display = "none";
            if (ws) {
                ws.close();
            }
            initWebSocket();
        }

        function clearSessionKey() {
            sessionStorage.removeItem("GOOGLE_API_KEY");
            sessionStorage.removeItem("session_provider");
            sessionStorage.removeItem("session_model");
            sessionApiKey = "";
            document.getElementById('apiKeyInput').value = "";
            keyModal.style.display = "flex";
            if (ws) {
                ws.close();
            }
            statusSpan.innerText = "Disconnected";
            statusSpan.style.background = "#334155";
        }

        function initWebSocket() {
            if (ws) {
                ws.onopen = null;
                ws.onmessage = null;
                ws.onclose = null;
                ws.close();
                ws = null;
            }

            telemetryDiv.innerHTML = "";
            const currentWs = new WebSocket(`ws://${location.host}/ws`);
            ws = currentWs;

            currentWs.onopen = () => {
                statusSpan.innerText = "Connecting Engine...";
                statusSpan.style.background = "#f59e0b";
                
                currentWs.send(JSON.stringify({
                    type: "init",
                    api_key: sessionApiKey,
                    provider: sessionProvider,
                    model: sessionModel
                }));
            };

            currentWs.onclose = () => {
                statusSpan.innerText = "Disconnected";
                statusSpan.style.background = "#991b1b";
            };

            currentWs.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === "init_success") {
                    statusSpan.innerText = `Online (${data.provider}: ${data.model})`;
                    statusSpan.style.background = "#065f46";
                    telemetryDiv.innerHTML = `<div style="font-size: 12px; color: #94a3b8; margin-bottom: 5px;">Agent initialized with provider: ${data.provider}, model: ${data.model}</div>`;
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
                    statusSpan.innerText = "Init Failed";
                    statusSpan.style.background = "#991b1b";
                    appendMessage("assistant", `❌ Error: ${data.error}`);
                    alert(`Agent Initialization Error: ${data.error}`);
                }
            };
        }

        function sendMessage() {
            const input = document.getElementById('userInput');
            const msg = input.value.trim();
            if (!msg) return;
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                alert("WebSocket is not connected. Please enter your API key and start session.");
                return;
            }
            appendMessage("user", msg);
            ws.send(JSON.stringify({ type: "user_message", content: msg }));
            input.value = "";
        }

        function appendMessage(role, text) {
            if (!text) return;
            const div = document.createElement('div');
            div.className = `msg ${role}`;
            div.innerText = text;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function appendTelemetry(text) {
            const div = document.createElement('div');
            div.style.fontSize = "12px";
            div.style.color = "#94a3b8";
            div.style.marginBottom = "5px";
            div.innerText = text;
            telemetryDiv.appendChild(div);
            telemetryDiv.scrollTop = telemetryDiv.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get_dashboard():
    return HTMLResponse(content=HTML_TEMPLATE)

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
