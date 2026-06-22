"""DocChat UI — Interfaz de escritorio para chat con documentos."""

import sys
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QSplitter, QStatusBar,
    QFileDialog, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction, QTextCursor, QDragEnterEvent, QDropEvent

from docchat.engine import DocChatEngine


# =============================================================================
# WORKER PARA LLM (hilo separado, no congela la UI)
# =============================================================================

class QueryWorker(QThread):
    """Worker para consultas al LLM (no congela la UI)."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, engine: DocChatEngine, question: str, use_context: bool = True):
        super().__init__()
        self.engine = engine
        self.question = question
        self.use_context = use_context

    def run(self):
        try:
            result = self.engine.query(self.question, self.use_context)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DocumentWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, engine: DocChatEngine, filepath: str):
        super().__init__()
        self.engine = engine
        self.filepath = filepath

    def run(self):
        try:
            result = self.engine.add_document(self.filepath)
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
        self._init_ui()
        self._check_status()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()

        # === HEADER ===
        header = QLabel("📄 DocChat — Asistente Local de Documentos")
        header.setStyleSheet("""
            font-size: 20px; font-weight: bold; padding: 12px;
            background: #1a1a2e; color: #e0e0e0; border-radius: 8px;
        """)
        main_layout.addWidget(header)

        # === CUERPO (splitter: docs | chat) ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Panel izquierdo: Documentos ---
        docs_panel = QWidget()
        docs_layout = QVBoxLayout()

        docs_title = QLabel("📁 Documentos")
        docs_title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px;")
        docs_layout.addWidget(docs_title)

        # Drop zone
        self.drop_zone = QLabel(
            "┌─────────────────────────┐\n"
            "│  Arrastra PDF, DOCX o   │\n"
            "│  TXT aquí para cargarlos │\n"
            "│                         │\n"
            "│    O haz click para     │\n"
            "│    seleccionar archivos  │\n"
            "└─────────────────────────┘"
        )
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setStyleSheet("""
            QLabel {
                background: #0d0d1a; color: #888; border: 2px dashed #444;
                border-radius: 8px; padding: 20px; font-family: monospace;
            }
            QLabel:hover { border-color: #4fc3f7; color: #4fc3f7; }
        """)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.mousePressEvent = self._browse_files

        # Override drop events properly
        self.drop_zone.dragEnterEvent = self._drag_enter
        self.drop_zone.dragMoveEvent = self._drag_move
        self.drop_zone.dropEvent = self._drop_file

        docs_layout.addWidget(self.drop_zone)

        # Lista de documentos
        self.doc_list = QListWidget()
        self.doc_list.setStyleSheet("""
            QListWidget {
                background: #0d0d1a; color: #ccc; border: 1px solid #333;
                border-radius: 4px; padding: 4px;
            }
        """)
        docs_layout.addWidget(QLabel("Documentos cargados:"))
        docs_layout.addWidget(self.doc_list)

        # Botón limpiar
        btn_clear = QPushButton("🗑 Limpiar todo")
        btn_clear.setStyleSheet("""
            QPushButton { background: #5c2e2e; color: white; border: none;
                border-radius: 4px; padding: 6px; }
            QPushButton:hover { background: #7a3e3e; }
        """)
        btn_clear.clicked.connect(self._clear_all)
        docs_layout.addWidget(btn_clear)

        docs_panel.setLayout(docs_layout)
        splitter.addWidget(docs_panel)

        # --- Panel derecho: Chat ---
        chat_panel = QWidget()
        chat_layout = QVBoxLayout()

        # Selector de modelo
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("🧠 Modelo:"))
        self.model_selector = QComboBox()
        self.model_selector.setMinimumWidth(250)
        self.model_selector.setStyleSheet("""
            QComboBox { background: #1a1a2e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px; padding: 4px; }
        """)
        model_row.addWidget(self.model_selector)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(36)
        self.btn_refresh.clicked.connect(self._refresh_models)
        model_row.addWidget(self.btn_refresh)

        self.context_check = QPushButton("📄 RAG ON")
        self.context_check.setCheckable(True)
        self.context_check.setChecked(True)
        self.context_check.setStyleSheet("""
            QPushButton { background: #0d7377; color: white; border: none;
                border-radius: 4px; padding: 4px 8px; }
            QPushButton:checked { background: #2d5c2e; }
        """)
        self.context_check.clicked.connect(self._toggle_context)
        model_row.addWidget(self.context_check)
        model_row.addStretch()

        chat_layout.addLayout(model_row)

        # Área de chat
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont("Segoe UI", 10))
        self.chat_area.setStyleSheet("""
            QTextEdit {
                background: #0d0d1a; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px; padding: 8px;
            }
        """)
        chat_layout.addWidget(self.chat_area)

        # Input
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe tu pregunta sobre los documentos...")
        self.input_field.setFont(QFont("Segoe UI", 11))
        self.input_field.returnPressed.connect(self._send_query)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: #1a1a2e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px;
                padding: 10px; font-size: 13px;
            }
        """)
        input_row.addWidget(self.input_field)

        self.btn_send = QPushButton("▶ Enviar")
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: #0d7377; color: white; border: none;
                border-radius: 4px; padding: 10px 24px; font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background: #0f8a8f; }
            QPushButton:disabled { background: #444; }
        """)
        self.btn_send.clicked.connect(self._send_query)
        input_row.addWidget(self.btn_send)

        chat_layout.addLayout(input_row)

        chat_panel.setLayout(chat_layout)
        splitter.addWidget(chat_panel)

        splitter.setSizes([300, 600])
        main_layout.addWidget(splitter)

        # === STATUS BAR ===
        self.status_bar = QStatusBar()
        self.lm_status = QLabel("🟡 Conectando a LM Studio...")
        self.doc_count = QLabel("📄 0 documentos")
        self.status_bar.addWidget(self.lm_status)
        self.status_bar.addPermanentWidget(self.doc_count)
        self.setStatusBar(self.status_bar)

        central.setLayout(main_layout)

        # Bienvenida
        self._append_chat("system", (
            "📄 **Bienvenido a DocChat**\n\n"
            "1. Carga documentos (PDF, DOCX, TXT) arrastrándolos al panel izquierdo\n"
            "2. Escribe preguntas sobre su contenido\n"
            "3. El modelo local de LM Studio responderá basado en los documentos\n\n"
            "✅ **Funciona 100% local** — Sin internet, sin API keys, sin costo"
        ))

    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drag_move(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_file(self, event):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            if filepath.lower().endswith(('.pdf', '.docx', '.txt')):
                self._load_document(filepath)

    def _browse_files(self, event=None):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar documentos",
            "", "Documentos (*.pdf *.docx *.txt);;Todos (*)"
        )
        for f in files:
            self._load_document(f)

    def _load_document(self, filepath: str):
        """Cargar un documento en la interfaz."""
        if not os.path.exists(filepath):
            return

        self.status_bar.showMessage(f"📖 Procesando: {os.path.basename(filepath)}...")
        self.btn_send.setEnabled(False)

        self.worker = DocumentWorker(self.engine, filepath)
        self.worker.finished.connect(self._on_doc_loaded)
        self.worker.error.connect(self._on_doc_error)
        self.worker.start()

    def _on_doc_loaded(self, result: dict):
        self.btn_send.setEnabled(True)
        if result["status"] == "ok":
            item = QListWidgetItem(f"✅ {result['filename']} ({result['chunks']} fragmentos)")
            item.setToolTip(f"{result['total_chars']:,} caracteres")
            self.doc_list.addItem(item)
            self._append_chat("system", (
                f"✅ **Documento cargado:** {result['filename']}\n"
                f"   • {result['chunks']} fragmentos indexados\n"
                f"   • {result['total_chars']:,} caracteres procesados"
            ))
            self.status_bar.showMessage(f"✅ Cargado: {result['filename']}", 3000)
        else:
            self._append_chat("error", f"Error: {result['message']}")
        self._update_stats()

    def _on_doc_error(self, error: str):
        self.btn_send.setEnabled(True)
        # Mensajes de error más amigables
        friendly = error
        if "encrypted" in error.lower() or "decrypt" in error.lower():
            friendly = (
                "El PDF está protegido con contraseña. "
                "Abre el PDF con un programa normal, "
                "guarda una copia sin protección, e intenta de nuevo."
            )
        elif "timeout" in error.lower():
            friendly = (
                "LM Studio tardó demasiado en responder. "
                "Prueba con un documento más pequeño o "
                "verifica que el modelo esté bien cargado en LM Studio."
            )
        self._append_chat("error", f"❌ {friendly}")
        self.status_bar.showMessage("❌ Error al cargar", 5000)

    def _send_query(self):
        question = self.input_field.text().strip()
        if not question:
            return

        self.input_field.clear()
        self._append_chat("user", question)
        self.status_bar.showMessage("💭 Pensando...")
        self.btn_send.setEnabled(False)
        self.input_field.setEnabled(False)

        use_context = self.context_check.isChecked()
        self.worker = QueryWorker(self.engine, question, use_context)
        self.worker.finished.connect(self._on_query_result)
        self.worker.error.connect(self._on_query_error)
        self.worker.start()

    def _on_query_result(self, result: str):
        self._append_chat("assistant", result)
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.status_bar.showMessage("✅ Respondido", 3000)

    def _on_query_error(self, error: str):
        friendly = error
        if "timeout" in error.lower():
            friendly = (
                "LM Studio tardó en responder. "
                "Puede ser porque:\n"
                "  • El modelo está cargándose\n"
                "  • El documento tiene muchos fragmentos\n"
                "  • La pregunta es muy compleja\n\n"
                "Espera unos segundos y vuelve a intentar."
            )
        self._append_chat("error", f"❌ {friendly}")
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self.status_bar.showMessage("❌ Error de conexión con LM Studio", 5000)

    def _clear_all(self):
        """Limpiar todos los documentos."""
        reply = QMessageBox.question(
            self, "Limpiar todo",
            "¿Eliminar todos los documentos cargados?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.engine.clear()
            self.doc_list.clear()
            self._append_chat("system", "🗑 **Documentos eliminados**")
            self._update_stats()

    def _toggle_context(self):
        """Alternar modo RAG / chat directo."""
        if self.context_check.isChecked():
            self.context_check.setText("📄 RAG ON")
            self.input_field.setPlaceholderText("Pregunta sobre los documentos...")
        else:
            self.context_check.setText("💬 CHAT")
            self.input_field.setPlaceholderText("Chatea con la IA local...")

    def _refresh_models(self):
        """Actualizar lista de modelos disponibles."""
        models = self.engine.available_models()
        self.model_selector.clear()
        for m in models:
            self.model_selector.addItem(m)
        if self.engine.chat_model in models:
            self.model_selector.setCurrentText(self.engine.chat_model)
        self.status_bar.showMessage(f"🔄 {len(models)} modelos disponibles", 3000)

    def _check_status(self):
        """Verificar estado de LM Studio."""
        if self.engine.is_available():
            self.lm_status.setText("🟢 LM Studio conectado")
            self.lm_status.setStyleSheet("color: #69db7c;")
            self._refresh_models()
        else:
            self.lm_status.setText("🔴 LM Studio no disponible")
            self.lm_status.setStyleSheet("color: #ff6b6b;")
            # Reintentar cada 10 segundos
            QTimer.singleShot(10000, self._check_status)

    def _update_stats(self):
        """Actualizar contadores."""
        stats = self.engine.get_stats()
        self.doc_count.setText(f"📄 {stats['documents']} fragmentos")

    def _append_chat(self, role: str, text: str):
        """Añadir mensaje al chat."""
        colors = {
            "system": "#888",
            "user": "#4fc3f7",
            "assistant": "#81c784",
            "error": "#ef5350",
        }
        color = colors.get(role, "#fff")
        prefix = {"user": "🧑 Tú", "assistant": "🤖 DocChat",
                  "system": "", "error": "❌ Error"}.get(role, "🤖 DocChat")

        if role == "system":
            html = f'<p style="color:{color}; font-style:italic;">{text}</p>'
        else:
            html = f'<p><b style="color:{color};">{prefix}:</b> '
            html += f'<span style="color:#e0e0e0;">{text}</span></p>'

        self.chat_area.append(html)
        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_area.setTextCursor(cursor)


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DocChat")
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background: #12121a; }
        QToolTip { background: #1a1a2e; color: #e0e0e0;
            border: 1px solid #444; padding: 4px; }
    """)

    window = DocChatWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
