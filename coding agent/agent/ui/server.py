import json
import uvicorn
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from agent.config import get_config
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
        input[type="text"] {
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
    </style>
</head>
<body>
    <header>
        <h2>⚡ Local Coding Agent Dashboard</h2>
        <span class="status-tag" id="status">Connecting...</span>
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
        const ws = new WebSocket(`ws://${location.host}/ws`);
        const messagesDiv = document.getElementById('messages');
        const telemetryDiv = document.getElementById('telemetry');
        const statusSpan = document.getElementById('status');

        ws.onopen = () => {
            statusSpan.innerText = "Online";
            statusSpan.style.background = "#065f46";
        };

        ws.onclose = () => {
            statusSpan.innerText = "Disconnected";
            statusSpan.style.background = "#991b1b";
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === "step_start") {
                appendTelemetry(`━━ Step ${data.step}/${data.max_steps} ━━`);
            } else if (data.type === "assistant_thinking") {
                appendMessage("assistant", data.content);
            } else if (data.type === "tool_executing") {
                appendTelemetry(`⚙ Tool Call: ${data.tool_name}`);
            } else if (data.type === "tool_completed") {
                appendMessage("tool", `[${data.tool_name}] ${data.output}`);
            } else if (data.type === "final_response") {
                appendMessage("assistant", data.content);
            }
        };

        function sendMessage() {
            const input = document.getElementById('userInput');
            const msg = input.value.trim();
            if (!msg) return;
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
    config = get_config()
    engine = AgentEngine(config=config)

    def ws_callback(event: dict):
        asyncio.create_task(websocket.send_json(event))

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if data.get("type") == "user_message":
                user_text = data.get("content", "")
                answer = await engine.run_step(user_text, step_callback=ws_callback)
                await websocket.send_json({"type": "final_response", "content": answer})
    except WebSocketDisconnect:
        pass

def start_server(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_server()
