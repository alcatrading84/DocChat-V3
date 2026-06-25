"""DocChat Web UI v3 — Interfaz web alternativa (Flask).

Permite usar DocChat desde el navegador:
- http://localhost:5000
- Accesible desde otros dispositivos en la red local
- Ideal para servidores o usuarios técnicos
"""

import os
import json
import logging
import threading
import queue
import webbrowser
from typing import Optional

logger = logging.getLogger(__name__)


class DocChatWebServer:
    """Servidor web Flask para DocChat."""

    def __init__(self, engine, host: str = "127.0.0.1", port: int = 5000,
                 debug: bool = False):
        """
        Args:
            engine: Instancia de DocChatEngine
            host: Dirección del servidor (0.0.0.0 para red local)
            port: Puerto del servidor
            debug: Modo debug de Flask
        """
        self.engine = engine
        self.host = host
        self.port = port
        self.debug = debug
        self._server = None
        self._thread = None

    def start(self, open_browser: bool = True):
        """Iniciar el servidor web en un hilo separado."""
        self._start(open_browser)

    def run(self, open_browser: bool = True):
        """Alias para start(). Inicia el servidor web."""
        self._start(open_browser)

    def _start(self, open_browser: bool = True):
        try:
            from flask import Flask, request, jsonify, render_template_string
        except ImportError:
            raise ImportError(
                "Para la Web UI necesitas: pip install flask"
            )

        app = Flask(__name__)

        # ---------------------------------------------------------------------
        # HTML Template (todo en uno, sin archivos externos)
        # ---------------------------------------------------------------------
        HTML_TEMPLATE = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>📄 DocChat Web</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                    background: #12121a; color: #e0e0e0;
                    display: flex; height: 100vh;
                }
                /* Sidebar */
                .sidebar {
                    width: 280px; background: #0d0d1a;
                    border-right: 1px solid #333; padding: 16px;
                    display: flex; flex-direction: column;
                }
                .sidebar h2 { color: #4fc3f7; font-size: 16px; margin-bottom: 12px; }
                .upload-zone {
                    border: 2px dashed #444; border-radius: 8px;
                    padding: 20px; text-align: center;
                    cursor: pointer; transition: all 0.3s;
                    margin-bottom: 12px;
                }
                .upload-zone:hover { border-color: #4fc3f7; color: #4fc3f7; }
                .upload-zone.dragover { border-color: #69db7c; background: #1a3a1a; }
                .file-list { flex: 1; overflow-y: auto; }
                .file-item {
                    padding: 6px 8px; margin: 2px 0;
                    background: #1a1a2e; border-radius: 4px;
                    font-size: 13px; color: #aaa;
                }
                .file-item.loaded { color: #69db7c; }
                .btn-clear {
                    background: #5c2e2e; color: white; border: none;
                    border-radius: 4px; padding: 6px; cursor: pointer;
                    margin-top: 8px; width: 100%;
                }
                .btn-clear:hover { background: #7a3e3e; }
                /* Main */
                .main { flex: 1; display: flex; flex-direction: column; }
                .header {
                    padding: 12px 20px; background: #1a1a2e;
                    border-bottom: 1px solid #333;
                    display: flex; align-items: center; gap: 12px;
                }
                .header h1 { font-size: 18px; flex: 1; }
                .rag-toggle {
                    background: #0d7377; color: white; border: none;
                    border-radius: 4px; padding: 4px 10px; cursor: pointer;
                    font-size: 12px;
                }
                .rag-toggle.off { background: #2d5c2e; }
                .status-dot {
                    width: 10px; height: 10px; border-radius: 50%;
                    display: inline-block; margin-right: 6px;
                }
                .status-dot.online { background: #69db7c; }
                .status-dot.offline { background: #ff6b6b; }
                .chat-area {
                    flex: 1; overflow-y: auto; padding: 20px;
                    display: flex; flex-direction: column; gap: 12px;
                }
                .message {
                    padding: 10px 14px; border-radius: 8px;
                    max-width: 80%; line-height: 1.5;
                }
                .message.user {
                    background: #1a3a5c; align-self: flex-end;
                    border-bottom-right-radius: 2px;
                }
                .message.assistant {
                    background: #1a2e1a; align-self: flex-start;
                    border-bottom-left-radius: 2px;
                }
                .message.system {
                    background: #2a2a2a; align-self: center;
                    text-align: center; font-size: 13px; color: #888;
                }
                .message.error {
                    background: #3a1a1a; align-self: center; color: #ef5350;
                }
                .input-area {
                    padding: 12px 20px; border-top: 1px solid #333;
                    display: flex; gap: 8px;
                }
                .input-area input {
                    flex: 1; background: #1a1a2e; color: #e0e0e0;
                    border: 1px solid #333; border-radius: 4px;
                    padding: 10px; font-size: 14px; outline: none;
                }
                .input-area input:focus { border-color: #4fc3f7; }
                .input-area button {
                    background: #0d7377; color: white; border: none;
                    border-radius: 4px; padding: 0 16px; cursor: pointer;
                    font-size: 16px;
                }
                .input-area button:disabled { background: #444; cursor: not-allowed; }
                .typing {
                    color: #888; font-style: italic; padding: 4px 20px;
                    font-size: 13px;
                }
                .progress-bar {
                    height: 3px; background: #333; border-radius: 2px;
                    overflow: hidden; margin: 4px 0;
                }
                .progress-bar .fill {
                    height: 100%; background: #4fc3f7;
                    transition: width 0.3s; width: 0%;
                }
                @media (max-width: 768px) {
                    .sidebar { display: none; }
                }
            </style>
        </head>
        <body>
            <div class="sidebar">
                <h2>📁 Documentos</h2>
                <div class="upload-zone" id="uploadZone"
                     onclick="document.getElementById('fileInput').click()">
                    📄 Arrastra o haz clic<br><small>PDF, DOCX, TXT, MD, etc.</small>
                </div>
                <input type="file" id="fileInput" style="display:none"
                       multiple onchange="uploadFiles(this.files)">
                <div class="file-list" id="fileList"></div>
                <button class="btn-clear" onclick="clearAll()">🗑 Limpiar todo</button>
            </div>
            <div class="main">
                <div class="header">
                    <h1>📄 DocChat Web</h1>
                    <button class="rag-toggle" id="ragToggle"
                            onclick="toggleRag()">📄 RAG ON</button>
                    <span id="status"><span class="status-dot offline"></span>Conectando...</span>
                </div>
                <div class="chat-area" id="chatArea">
                    <div class="message system">
                        📄 DocChat Web — Asistente Local de Documentos<br><br>
                        1️⃣ Arrastra documentos al panel izquierdo<br>
                        2️⃣ Escribe preguntas sobre su contenido<br>
                        3️⃣ Respuestas en tiempo real 🚀
                    </div>
                </div>
                <div class="typing" id="typing"></div>
                <div class="input-area">
                    <input type="text" id="input"
                           placeholder="Pregunta sobre los documentos..."
                           onkeypress="if(event.key==='Enter') send()">
                    <button id="sendBtn" onclick="send()">▶</button>
                </div>
            </div>
            <script>
                let ragEnabled = true;
                let loading = false;

                // Drag & drop
                const uz = document.getElementById('uploadZone');
                uz.addEventListener('dragover', e => {
                    e.preventDefault();
                    uz.classList.add('dragover');
                });
                uz.addEventListener('dragleave', () => uz.classList.remove('dragover'));
                uz.addEventListener('drop', e => {
                    e.preventDefault();
                    uz.classList.remove('dragover');
                    uploadFiles(e.dataTransfer.files);
                });

                function uploadFiles(files) {
                    const formData = new FormData();
                    for (const f of files) {
                        formData.append('files', f);
                    }
                    fetch('/upload', { method: 'POST', body: formData })
                        .then(r => r.json())
                        .then(d => {
                            if (d.status === 'ok') {
                                updateFileList();
                                addMessage('system', d.message || '✅ Documentos cargados');
                            } else {
                                addMessage('error', d.message || 'Error al cargar');
                            }
                        })
                        .catch(e => addMessage('error', 'Error de conexión'));
                }

                function updateFileList() {
                    fetch('/files')
                        .then(r => r.json())
                        .then(d => {
                            const fl = document.getElementById('fileList');
                            fl.innerHTML = d.files.map(f =>
                                `<div class="file-item loaded">✅ ${f}</div>`
                            ).join('');
                            document.querySelector('.header h1').textContent =
                                `📄 DocChat Web (${d.count} docs)`;
                        });
                }

                function clearAll() {
                    fetch('/clear', { method: 'POST' })
                        .then(r => r.json())
                        .then(d => {
                            document.getElementById('fileList').innerHTML = '';
                            addMessage('system', '🗑 Documentos eliminados');
                            document.querySelector('.header h1').textContent = '📄 DocChat Web';
                        });
                }

                function toggleRag() {
                    ragEnabled = !ragEnabled;
                    const btn = document.getElementById('ragToggle');
                    btn.textContent = ragEnabled ? '📄 RAG ON' : '💬 CHAT';
                    btn.className = 'rag-toggle' + (ragEnabled ? '' : ' off');
                    document.getElementById('input').placeholder =
                        ragEnabled ? 'Pregunta sobre los documentos...' : 'Chatea con la IA local...';
                }

                function send() {
                    const input = document.getElementById('input');
                    const q = input.value.trim();
                    if (!q || loading) return;
                    input.value = '';
                    addMessage('user', q);
                    loading = true;
                    document.getElementById('sendBtn').disabled = true;
                    document.getElementById('typing').textContent = '🤖 Escribiendo...';

                    const msgDiv = document.createElement('div');
                    msgDiv.className = 'message assistant';
                    msgDiv.id = 'streamResponse';
                    document.getElementById('chatArea').appendChild(msgDiv);

                    fetch('/stream', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question: q, use_context: ragEnabled })
                    }).then(async r => {
                        const reader = r.body.getReader();
                        const decoder = new TextDecoder();
                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) break;
                            const text = decoder.decode(value);
                            const lines = text.split('\\n');
                            for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                    const data = line.slice(6);
                                    if (data === '[DONE]') continue;
                                    try {
                                        const parsed = JSON.parse(data);
                                        if (parsed.token) {
                                            msgDiv.textContent += parsed.token;
                                        }
                                    } catch(e) {}
                                }
                            }
                        }
                        loading = false;
                        document.getElementById('sendBtn').disabled = false;
                        document.getElementById('typing').textContent = '';
                        msgDiv.scrollIntoView({ behavior: 'smooth' });
                    }).catch(e => {
                        addMessage('error', 'Error en la respuesta');
                        loading = false;
                        document.getElementById('sendBtn').disabled = false;
                        document.getElementById('typing').textContent = '';
                        const el = document.getElementById('streamResponse');
                        if (el) el.remove();
                    });
                }

                function addMessage(role, text) {
                    const div = document.createElement('div');
                    div.className = 'message ' + role;
                    div.textContent = text;
                    document.getElementById('chatArea').appendChild(div);
                    div.scrollIntoView({ behavior: 'smooth' });
                }

                updateFileList();
                // Status check
                fetch('/status').then(r => r.json()).then(d => {
                    const s = document.getElementById('status');
                    s.innerHTML = d.available
                        ? '<span class="status-dot online"></span>✅ Conectado'
                        : '<span class="status-dot offline"></span>🔴 Desconectado';
                });
            </script>
        </body>
        </html>
        """

        # ---------------------------------------------------------------------
        # RUTAS FLASK
        # ---------------------------------------------------------------------

        @app.route("/")
        def index():
            return render_template_string(HTML_TEMPLATE)

        @app.route("/status")
        def status():
            return jsonify({
                "available": self.engine.is_available(),
                "stats": self.engine.get_stats(),
            })

        @app.route("/files")
        def list_files():
            stats = self.engine.get_stats()
            return jsonify({
                "files": stats.get("sources", []),
                "count": stats.get("documents", 0),
            })

        @app.route("/upload", methods=["POST"])
        def upload():
            from flask import request as flask_req
            files = flask_req.files.getlist("files")
            if not files:
                return jsonify({"status": "error", "message": "No files received"})

            results = []
            for f in files:
                temp_path = os.path.join(
                    os.path.expanduser("~"), ".docchat", "uploads", f.filename
                )
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                f.save(temp_path)

                try:
                    result = self.engine.add_document(temp_path)
                    results.append({
                        "file": f.filename,
                        "status": result.get("status", "error"),
                        "chunks": result.get("chunks", 0),
                    })
                except Exception as e:
                    results.append({
                        "file": f.filename,
                        "status": "error",
                        "message": str(e),
                    })

            return jsonify({
                "status": "ok",
                "results": results,
                "message": f"✅ {len(results)} documentos procesados",
            })

        @app.route("/stream", methods=["POST"])
        def stream():
            """Streaming de respuesta (SSE real con tokens en vivo)."""
            data = request.get_json()
            question = data.get("question", "")
            use_context = data.get("use_context", True)

            def generate():
                q = queue.Queue()
                _done = object()

                def on_token(tok: str):
                    q.put(tok)

                def run_query():
                    try:
                        self.engine.query_stream(
                            question,
                            on_token=on_token,
                            use_context=use_context,
                        )
                    except Exception as e:
                        q.put(f"\n\n❌ Error: {e}")
                    finally:
                        q.put(_done)

                thread = threading.Thread(target=run_query, daemon=True)
                thread.start()

                while True:
                    item = q.get()
                    if item is _done:
                        break
                    yield f"data: {json.dumps({'token': item})}\n\n"
                yield "data: [DONE]\n\n"

            from flask import Response
            return Response(
                generate(),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

        @app.route("/chat", methods=["POST"])
        def chat():
            """Chat sin streaming (para clientes simples)."""
            data = request.get_json()
            question = data.get("question", "")
            use_context = data.get("use_context", True)

            try:
                response = self.engine.query(question, use_context=use_context)
                return jsonify({"response": response})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/clear", methods=["POST"])
        def clear():
            self.engine.clear()
            return jsonify({"status": "ok"})

        import time as _time

        # ---------------------------------------------------------------------
        # INICIAR SERVIDOR
        # ---------------------------------------------------------------------

        self._thread = threading.Thread(
            target=lambda: app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                use_reloader=False,
            ),
            daemon=True,
        )
        self._thread.start()
        logger.info(f"🌐 Web UI en http://{self.host}:{self.port}")

        if open_browser:
            _time.sleep(0.5)
            webbrowser.open(f"http://{self.host}:{self.port}")

        return f"http://{self.host}:{self.port}"

    def stop(self):
        """Detener el servidor web."""
        if self._thread and self._thread.is_alive():
            import requests
            try:
                requests.get(f"http://{self.host}:{self.port}/shutdown",
                             timeout=2)
            except Exception:
                pass
            logger.info("🌐 Web UI detenida")


def start_web_ui(engine, host="127.0.0.1", port=5000,
                 open_browser=True, debug=False) -> DocChatWebServer:
    """Función de conveniencia para iniciar la Web UI."""
    server = DocChatWebServer(engine, host, port, debug)
    url = server.start(open_browser)
    print(f"\n🌐 Web UI disponible en: {url}")
    if host == "0.0.0.0":
        import socket
        hostname = socket.gethostname()
        print(f"   Desde otro dispositivo: http://{hostname}:{port}")
    return server
