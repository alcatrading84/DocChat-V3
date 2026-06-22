"""DocChat UI v2 — Interfaz fluida con streaming y progreso."""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QSplitter, QStatusBar,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from docchat.engine import DocChatEngine


# =============================================================================
# WORKERS (hilos separados para no congelar la UI)
# =============================================================================

class StreamWorker(QThread):
    """Worker con streaming: emite tokens 1 a 1 en tiempo real."""
    token = pyqtSignal(str)         # Cada token nuevo
    finished = pyqtSignal(str)       # Respuesta completa
    error = pyqtSignal(str)

    def __init__(self, engine, question, use_context=True):
        super().__init__()
        self.engine = engine
        self.question = question
        self.use_context = use_context

    def run(self):
        try:
            full = self.engine.query_stream(
                self.question,
                on_token=lambda t: self.token.emit(t),
                use_context=self.use_context,
            )
            self.finished.emit(full)
        except Exception as e:
            self.error.emit(str(e))


class DocLoadWorker(QThread):
    """Worker que carga documentos con progreso."""
    progress = pyqtSignal(int, int, str)  # actual, total, mensaje
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, engine, filepath):
        super().__init__()
        self.engine = engine
        self.filepath = filepath

    def run(self):
        try:
            result = self.engine.add_document(
                self.filepath,
                on_progress=lambda a, t, m: self.progress.emit(a, t, m),
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# =============================================================================
# VENTANA PRINCIPAL
# =============================================================================

class DocChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = DocChatEngine()
        self.setWindowTitle("📄 DocChat — Chat con tus documentos")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)
        self._current_response = ""  # Para streaming
        self._init_ui()
        QTimer.singleShot(500, self._check_status)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        ml = QVBoxLayout()

        # HEADER
        header = QLabel("📄 DocChat — Asistente Local de Documentos")
        header.setStyleSheet("""
            font-size: 20px; font-weight: bold; padding: 12px;
            background: #1a1a2e; color: #e0e0e0; border-radius: 8px;
        """)
        ml.addWidget(header)

        # SPLITTER
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === PANEL IZQUIERDO: Documentos ===
        dp = QWidget()
        dl = QVBoxLayout()

        dl.addWidget(QLabel("📁 Documentos"))
        dl.addWidget(QLabel("Arrastra PDF, DOCX o TXT:"))

        self.drop_zone = QLabel("🎯 SOLTAR AQUÍ")
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setMinimumHeight(80)
        self.drop_zone.setStyleSheet("""
            QLabel {
                background: #0d0d1a; color: #888;
                border: 2px dashed #444; border-radius: 8px;
                font-size: 16px; font-weight: bold;
            }
            QLabel:hover { border-color: #4fc3f7; color: #4fc3f7; }
        """)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.mousePressEvent = lambda e: self._browse()
        self.drop_zone.dragEnterEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasUrls() else None
        self.drop_zone.dragMoveEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasUrls() else None
        self.drop_zone.dropEvent = self._on_drop
        dl.addWidget(self.drop_zone)

        # Progreso de carga
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888; font-size: 11px;")
        dl.addWidget(self.progress_label)

        # Lista de documentos
        self.doc_list = QListWidget()
        self.doc_list.setStyleSheet("""
            QListWidget { background: #0d0d1a; color: #ccc;
                border: 1px solid #333; border-radius: 4px; }
        """)
        dl.addWidget(QLabel("Cargados:"))
        dl.addWidget(self.doc_list)

        btn_clear = QPushButton("🗑 Limpiar todo")
        btn_clear.setStyleSheet("""
            QPushButton { background: #5c2e2e; color: white;
                border: none; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background: #7a3e3e; }
        """)
        btn_clear.clicked.connect(self._clear_all)
        dl.addWidget(btn_clear)

        dp.setLayout(dl)
        splitter.addWidget(dp)

        # === PANEL DERECHO: Chat ===
        cp = QWidget()
        cl = QVBoxLayout()

        # Selector de modelo + RAG toggle
        tr = QHBoxLayout()
        tr.addWidget(QLabel("🧠 Modelo:"))
        self.model_sel = QComboBox()
        self.model_sel.setMinimumWidth(220)
        self.model_sel.setStyleSheet("""
            QComboBox { background: #1a1a2e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px; padding: 4px; }
        """)
        tr.addWidget(self.model_sel)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(36)
        self.btn_refresh.clicked.connect(self._refresh_models)
        tr.addWidget(self.btn_refresh)

        self.rag_btn = QPushButton("📄 RAG ON")
        self.rag_btn.setCheckable(True)
        self.rag_btn.setChecked(True)
        self.rag_btn.setStyleSheet("""
            QPushButton { background: #0d7377; color: white;
                border: none; border-radius: 4px; padding: 4px 10px; }
            QPushButton:checked { background: #2d5c2e; }
        """)
        self.rag_btn.clicked.connect(self._toggle_rag)
        tr.addWidget(self.rag_btn)
        tr.addStretch()
        cl.addLayout(tr)

        # Área de chat
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setFont(QFont("Segoe UI", 10))
        self.chat.setStyleSheet("""
            QTextEdit { background: #0d0d1a; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px; padding: 8px; }
        """)
        cl.addWidget(self.chat)

        # Indicador de escritura
        self.typing_label = QLabel("")
        self.typing_label.setStyleSheet("color: #888; font-style: italic; padding: 2px;")

        # Input
        ir = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escribe tu pregunta...")
        self.input.setFont(QFont("Segoe UI", 11))
        self.input.returnPressed.connect(self._send)
        self.input.setStyleSheet("""
            QLineEdit { background: #1a1a2e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px;
                padding: 10px; font-size: 13px; }
        """)
        ir.addWidget(self.input)

        self.btn_send = QPushButton("▶")
        self.btn_send.setFixedSize(50, 40)
        self.btn_send.setStyleSheet("""
            QPushButton { background: #0d7377; color: white;
                border: none; border-radius: 4px; font-size: 16px; }
            QPushButton:hover { background: #0f8a8f; }
            QPushButton:disabled { background: #444; }
        """)
        self.btn_send.clicked.connect(self._send)
        ir.addWidget(self.btn_send)

        cl.addLayout(ir)
        cp.setLayout(cl)
        splitter.addWidget(cp)

        splitter.setSizes([280, 620])
        ml.addWidget(splitter)

        # STATUS BAR
        self.sb = QStatusBar()
        self.lm_status = QLabel("🟡 Conectando...")
        self.doc_count = QLabel("📄 0")
        self.sb.addWidget(self.lm_status)
        self.sb.addPermanentWidget(self.doc_count)
        self.setStatusBar(self.sb)

        central.setLayout(ml)

        # Bienvenida
        self._msg("system",
            "📄 **DocChat** — Asistente Local de Documentos\n\n"
            "1️⃣ Arrastra un PDF, Word o TXT al panel izquierdo\n"
            "2️⃣ Escribe preguntas sobre su contenido\n"
            "3️⃣ Las respuestas aparecen **en tiempo real**\n\n"
            "✅ 100% local · Sin API keys · Sin internet"
        )

    def _on_drop(self, event):
        for url in event.mimeData().urls():
            fp = url.toLocalFile()
            if fp.lower().endswith(('.pdf', '.docx', '.txt')):
                self._load_doc(fp)

    def _browse(self, event=None):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar documentos", "",
            "Documentos (*.pdf *.docx *.txt);;Todos (*)")
        for f in files:
            self._load_doc(f)

    def _load_doc(self, filepath):
        if not os.path.exists(filepath):
            return
        self.progress_label.setText(f"⏳ Procesando {os.path.basename(filepath)}...")
        self.btn_send.setEnabled(False)
        self._worker = DocLoadWorker(self.engine, filepath)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_doc_done)
        self._worker.error.connect(self._on_doc_error)
        self._worker.finished.connect(lambda: setattr(self, '_worker', None))
        self._worker.error.connect(lambda: setattr(self, '_worker', None))
        self._worker.start()

    def _on_progress(self, actual, total, msg):
        self.progress_label.setText(f"⏳ {msg}")

    def _on_doc_done(self, result):
        self.btn_send.setEnabled(True)
        self.progress_label.setText("")
        try:
            if result and result.get("status") == "ok":
                self.doc_list.addItem(
                    QListWidgetItem(f"✅ {result['filename']} ({result['chunks']} frags)")
                )
                self._msg("system",
                    f"✅ **{result['filename']}** cargado.\n"
                    f"{result['chunks']} fragmentos · {result['total_chars']:,} caracteres"
                )
                self.sb.showMessage(f"✅ {result['filename']}", 3000)
            else:
                msg = result.get("message", "Error desconocido") if result else "Error al procesar"
                self._msg("error", msg)
        except Exception as e:
            self._msg("error", f"Error al mostrar resultado: {e}")
        self._update_stats()

    def _on_doc_error(self, error):
        self.btn_send.setEnabled(True)
        self.progress_label.setText("")
        friendly = str(error)
        if "encrypted" in error.lower() or "decrypt" in error.lower():
            friendly = "PDF protegido. Guárdalo sin contraseña e intenta de nuevo."
        elif "timeout" in error.lower():
            friendly = "LM Studio tardó. Verifica que el modelo de embeddings esté cargado."
        self._msg("error", friendly)
        self.sb.showMessage("❌ Error", 5000)

    def _send(self):
        q = self.input.text().strip()
        if not q:
            return
        self.input.clear()
        self._msg("user", q)
        self.btn_send.setEnabled(False)
        self.input.setEnabled(False)

        # Preparar para streaming
        self._current_response = ""
        self.typing_label.setText("🤖 Escribiendo...")

        uc = self.rag_btn.isChecked()
        self._stream_worker = StreamWorker(self.engine, q, uc)
        self._stream_worker.token.connect(self._on_token)
        self._stream_worker.finished.connect(self._on_response_done)
        self._stream_worker.error.connect(self._on_response_error)
        self._stream_worker.finished.connect(lambda: setattr(self, '_stream_worker', None))
        self._stream_worker.error.connect(lambda: setattr(self, '_stream_worker', None))
        self._stream_worker.start()

    def _on_token(self, token):
        """Cada token nuevo se muestra al instante."""
        try:
            self._current_response += token
            self.chat.insertPlainText(token)
            c = self.chat.textCursor()
            c.movePosition(QTextCursor.MoveOperation.End)
            self.chat.setTextCursor(c)
        except Exception:
            pass  # No romper la app si hay error de UI

    def _on_response_done(self, full):
        self.btn_send.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        self.typing_label.setText("")
        self.sb.showMessage("✅ Listo", 2000)

    def _on_response_error(self, error):
        friendly = str(error)
        if "timeout" in error.lower():
            friendly = "LM Studio tardó. Verifica que el modelo esté cargado y prueba de nuevo."
        self._msg("error", friendly)
        self.btn_send.setEnabled(True)
        self.input.setEnabled(True)
        self.sb.showMessage("❌ Error", 5000)

    def _clear_all(self):
        r = QMessageBox.question(self, "Limpiar todo",
            "¿Eliminar todos los documentos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.engine.clear()
            self.doc_list.clear()
            self._msg("system", "🗑 Documentos eliminados")
            self._update_stats()

    def _toggle_rag(self):
        if self.rag_btn.isChecked():
            self.rag_btn.setText("📄 RAG ON")
            self.input.setPlaceholderText("Pregunta sobre los documentos...")
        else:
            self.rag_btn.setText("💬 CHAT")
            self.input.setPlaceholderText("Chatea con la IA local...")

    def _refresh_models(self):
        models = self.engine.available_models()
        self.model_sel.clear()
        for m in models:
            self.model_sel.addItem(m)
        self.sb.showMessage(f"🔄 {len(models)} modelos", 3000)

    def _check_status(self):
        if self.engine.is_available():
            self.lm_status.setText("🟢 LM Studio")
            self.lm_status.setStyleSheet("color: #69db7c;")
            self._refresh_models()
        else:
            self.lm_status.setText("🔴 LM Studio NO disponible")
            self.lm_status.setStyleSheet("color: #ff6b6b;")
            # Reintentar
            QTimer.singleShot(10000, self._check_status)

    def _update_stats(self):
        s = self.engine.get_stats()
        self.doc_count.setText(f"📄 {s['documents']}")

    def _msg(self, role, text):
        colors = {"system": "#888", "user": "#4fc3f7",
                  "assistant": "#81c784", "error": "#ef5350"}
        color = colors.get(role, "#fff")
        prefix = {"user": "🧑 Tú", "assistant": "🤖 DocChat",
                  "system": "", "error": "❌"}.get(role, "🤖")

        if role == "system":
            html = f'<p style="color:{color};">{text}</p>'
        else:
            html = f'<p><b style="color:{color};">{prefix}:</b> '
            html += f'<span style="color:#e0e0e0;">{text}</span></p>'

        self.chat.append(html)
        c = self.chat.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.chat.setTextCursor(c)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DocChat")
    app.setStyle("Fusion")
    
    # Icono de la aplicación
    import os
    icon_paths = [
        os.path.join(os.path.dirname(__file__), "..", "favicon.ico"),
        os.path.join(os.path.dirname(__file__), "..", "docchat_icon.png"),
    ]
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            icon = QIcon(icon_path)
            app.setWindowIcon(icon)
            break
    
    app.setStyleSheet("""
        QMainWindow { background: #12121a; }
        QToolTip { background: #1a1a2e; color: #e0e0e0;
            border: 1px solid #444; padding: 4px; }
    """)
    w = DocChatWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
