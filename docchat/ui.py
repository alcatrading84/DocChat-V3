"""DocChat UI v3 — Interfaz profesional estilo dashboard con tema CSS global."""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QStatusBar,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from docchat.engine import DocChatEngine
from docchat.lang import t


# =============================================================================
# PALETA DE COLORES — Diseño profesional referencia
# =============================================================================
C = {
    "dark": {
        "bg": "#000020",
        "sidebar": "#161F32",
        "main": "#1A2337",
        "header": "#182033",
        "input_bg": "#0F172A",
        "accent": "#3A83F1",
        "accent_hover": "#5A9BF5",
        "text": "#BCBECE",
        "text_dim": "#6B7280",
        "text_bright": "#E2E8F0",
        "border": "#1E293B",
        "danger": "#EF4444",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "card": "#1E293B",
        "hover_bg": "#1E3A5F",
    },
    "light": {
        "bg": "#F8FAFC",
        "sidebar": "#FFFFFF",
        "main": "#F1F5F9",
        "header": "#FFFFFF",
        "input_bg": "#FFFFFF",
        "accent": "#2563EB",
        "accent_hover": "#3B82F6",
        "text": "#334155",
        "text_dim": "#94A3B8",
        "text_bright": "#0F172A",
        "border": "#E2E8F0",
        "danger": "#DC2626",
        "success": "#16A34A",
        "warning": "#D97706",
        "card": "#FFFFFF",
        "hover_bg": "#E8F0FE",
    },
}


# =============================================================================
# GENERADOR DE TEMA CSS
# =============================================================================

def build_theme(mode: str = "dark") -> str:
    """Generar el stylesheet global completo para el modo indicado."""
    c = C.get(mode, C["dark"])
    return f"""
        /* === VENTANA PRINCIPAL === */
        QMainWindow {{ background: {c['bg']}; }}
        QWidget {{ color: {c['text']}; font-family: 'Segoe UI', sans-serif; }}

        /* === TOOLTIP === */
        QToolTip {{
            background: {c['sidebar']};
            color: {c['text']};
            border: 1px solid {c['border']};
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
        }}

        /* === SCROLLBAR === */
        QScrollBar:vertical {{
            background: {c['bg']};
            width: 8px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {c['border']};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c['accent']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        /* === SPLITTER === */
        QSplitter::handle {{
            background: {c['border']};
            width: 1px;
        }}

        /* === STATUS BAR === */
        QStatusBar {{
            background: {c['header']};
            color: {c['text_dim']};
            border-top: 1px solid {c['border']};
            font-size: 11px;
            padding: 2px 12px;
        }}

        /* === SIDEBAR === */
        #sidebar {{
            background: {c['sidebar']};
        }}
        #sidebarTitle {{
            color: {c['text_bright']};
            font-size: 14px;
            font-weight: bold;
            padding: 4px 0;
            white-space: nowrap;
        }}
        #sidebarDesc {{
            color: {c['text_dim']};
            font-size: 11px;
            padding: 0 4px;
            white-space: nowrap;
        }}
        #sidebarFooter {{
            color: {c['text_dim']};
            font-size: 10px;
            padding: 8px 0 0 0;
            white-space: nowrap;
        }}

        /* === DROP ZONE === */
        #dropZone {{
            background: {c['card']};
            color: {c['text_dim']};
            border: 2px dashed {c['border']};
            border-radius: 10px;
            font-size: 13px;
            font-weight: bold;
            padding: 16px;
        }}
        #dropZone:hover {{
            border-color: {c['accent']};
            color: {c['accent']};
            background: {c['hover_bg']};
        }}

        /* === PROGRESS LABEL === */
        #progressLabel {{
            color: {c['accent']};
            font-size: 11px;
            padding: 2px 4px;
        }}

        /* === DOC LIST === */
        #docLabel {{
            color: {c['text_dim']};
            font-size: 11px;
            padding: 4px 0;
        }}
        #docList {{
            background: {c['card']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 4px;
            font-size: 12px;
        }}
        #docList::item {{
            padding: 6px 8px;
            border-radius: 4px;
        }}
        #docList::item:hover {{
            background: {c['hover_bg']};
        }}

        /* === BOTÓN LIMPIAR === */
        #btnClear {{
            background: transparent;
            color: {c['text_dim']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
            white-space: nowrap;
        }}
        #btnClear:hover {{
            background: #3A1A1A;
            color: {c['danger']};
            border-color: {c['danger']};
        }}

        /* === HEADER === */
        #headerBar {{
            background: {c['header']};
            border-bottom: 1px solid {c['border']};
        }}
        #headerTitle {{
            color: {c['text_bright']};
            font-size: 15px;
            font-weight: bold;
            background: transparent;
        }}

        /* === COMBOBOX === */
        QComboBox {{
            background: {c['card']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            min-height: 28px;
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 6px;
        }}
        QComboBox:hover {{
            border-color: {c['accent']};
        }}
        QComboBox QAbstractItemView {{
            background: {c['sidebar']};
            color: {c['text']};
            border: 1px solid {c['border']};
            selection-background-color: {c['accent']};
        }}

        /* === BOTONES HEADER === */
        .headerBtn {{
            background: transparent;
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 13px;
        }}
        .headerBtn:hover {{
            background: {c['accent']};
            color: white;
            border-color: {c['accent']};
        }}

        /* === BOTÓN PEQUEÑO === */
        .smallBtn {{
            background: {c['card']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
        }}
        .smallBtn:hover {{
            background: {c['accent']};
            color: white;
            border-color: {c['accent']};
        }}

        /* === RAG TOGGLE === */
        #ragBtn {{
            background: {c['card']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
        }}
        #ragBtn:hover {{
            border-color: {c['accent']};
        }}
        #ragBtn:checked {{
            background: {c['accent']};
            color: white;
            border-color: {c['accent']};
        }}

        /* === CHAT AREA === */
        #rightPanel {{
            background: {c['main']};
        }}
        #chatArea {{
            background: {c['main']};
            color: {c['text']};
            border: none;
            padding: 20px;
            font-size: 13px;
            line-height: 1.6;
        }}

        /* === INPUT BAR === */
        #inputBar {{
            background: {c['input_bg']};
            border-top: 1px solid {c['border']};
        }}
        #chatInput {{
            background: {c['card']};
            color: {c['text_bright']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 10px 16px;
            font-size: 13px;
        }}
        #chatInput:focus {{
            border-color: {c['accent']};
        }}
        #chatInput::placeholder {{
            color: {c['text_dim']};
        }}

        /* === BOTÓN ENVIAR === */
        #btnSend {{
            background: {c['accent']};
            color: white;
            border: none;
            border-radius: 21px;
            font-size: 16px;
        }}
        #btnSend:hover {{
            background: {c['accent_hover']};
        }}
        #btnSend:disabled {{
            background: {c['card']};
            color: {c['text_dim']};
        }}

        /* === BOTONES INPUT === */
        .inputBtn {{
            background: transparent;
            color: {c['text_dim']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 6px;
            font-size: 14px;
        }}
        .inputBtn:hover {{
            background: {c['accent']};
            color: white;
            border-color: {c['accent']};
        }}

        /* === TYPING LABEL === */
        #typingLabel {{
            color: {c['text_dim']};
            font-style: italic;
            font-size: 11px;
            padding: 0 0 2px 4px;
        }}

        /* === STATUS LABELS === */
        #statusConnected {{
            color: {c['success']};
            padding: 0 8px;
        }}
        #statusDisconnected {{
            color: {c['danger']};
            padding: 0 8px;
        }}
        #docCountLabel {{
            color: {c['text_dim']};
            padding: 0 8px;
        }}
    """


# =============================================================================
# WORKERS
# =============================================================================

class StreamWorker(QThread):
    token = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, engine, question, use_context=True):
        super().__init__()
        self.engine = engine
        self.question = question
        self.use_context = use_context

    def run(self):
        try:
            if self.question.startswith("__summarize__"):
                lang = self.question.split(":")[1] if ":" in self.question else "es"
                full = self.engine.summarize(on_token=lambda t: self.token.emit(t), lang=lang)
            elif self.question.startswith("__translate__:"):
                parts = self.question.split(":", 2)
                full = self.engine.translate(parts[2], target=parts[1],
                                             on_token=lambda t: self.token.emit(t))
            else:
                full = self.engine.query_stream(
                    self.question,
                    on_token=lambda t: self.token.emit(t),
                    use_context=self.use_context,
                )
            self.finished.emit(full)
        except Exception as e:
            self.error.emit(str(e))


class DocLoadWorker(QThread):
    progress = pyqtSignal(int, int, str)
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
        self.lang = "es"
        self._theme = "dark"  # "dark" o "light"
        self.setWindowTitle(t("app_name", self.lang))
        # Icono
        for p in ["favicon.ico", os.path.join(os.path.dirname(__file__), "..", "favicon.ico"),
                   getattr(__import__('sys'), '_MEIPASS', '') + "/favicon.ico"]:
            if p and os.path.exists(p):
                from PyQt6.QtGui import QIcon
                self.setWindowIcon(QIcon(p))
                break
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)
        self._current_response = ""
        self._init_ui()
        QTimer.singleShot(500, self._check_status)
        QTimer.singleShot(3000, self._check_update_async)

    @property
    def _colors(self):
        """Colores del tema activo."""
        return C.get(self._theme, C["dark"])

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        ml = QVBoxLayout()
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # ================================================================
        # CONTENEDOR: SIDEBAR + MAIN
        # ================================================================
        h_container = QWidget()
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # ================================================================
        # SIDEBAR (280px fijo)
        # ================================================================
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        sb_layout = QVBoxLayout()
        sb_layout.setContentsMargins(16, 16, 16, 16)
        sb_layout.setSpacing(10)

        sb_title = QLabel(t("docs_title", self.lang))
        sb_title.setObjectName("sidebarTitle")
        sb_layout.addWidget(sb_title)

        self.drop_zone = QLabel(t("drop_hint", self.lang))
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setMinimumHeight(90)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.mousePressEvent = lambda e: self._browse()
        self.drop_zone.dragEnterEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasUrls() else None
        self.drop_zone.dragMoveEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasUrls() else None
        self.drop_zone.dropEvent = self._on_drop
        sb_layout.addWidget(self.drop_zone)

        self.drop_desc = QLabel(t("drop_desc", self.lang))
        self.drop_desc.setObjectName("sidebarDesc")
        sb_layout.addWidget(self.drop_desc)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progressLabel")
        sb_layout.addWidget(self.progress_label)

        self.doc_label = QLabel(t("loaded", self.lang))
        self.doc_label.setObjectName("docLabel")
        sb_layout.addWidget(self.doc_label)

        self.doc_list = QListWidget()
        self.doc_list.setObjectName("docList")
        sb_layout.addWidget(self.doc_list)

        self.btn_clear = QPushButton(t("clear_all", self.lang))
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.clicked.connect(self._clear_all)
        sb_layout.addWidget(self.btn_clear)

        sb_layout.addStretch()

        sb_footer = QLabel("DocChat v3 · 100% Local")
        sb_footer.setObjectName("sidebarFooter")
        sb_layout.addWidget(sb_footer)

        sidebar.setLayout(sb_layout)
        h_layout.addWidget(sidebar)

        # ================================================================
        # PANEL PRINCIPAL
        # ================================================================
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        rp_layout = QVBoxLayout()
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(0)

        # ---- HEADER ----
        header_bar = QWidget()
        header_bar.setObjectName("headerBar")
        header_bar.setFixedHeight(52)
        hb_layout = QHBoxLayout()
        hb_layout.setContentsMargins(16, 0, 16, 0)
        hb_layout.setSpacing(8)

        self.header = QLabel(t("app_subtitle", self.lang))
        self.header.setObjectName("headerTitle")
        hb_layout.addWidget(self.header)
        hb_layout.addStretch()

        # Modelo
        self.model_sel = QComboBox()
        self.model_sel.setMinimumWidth(160)
        hb_layout.addWidget(self.model_sel)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedSize(30, 30)
        self.btn_refresh.setProperty("class", "smallBtn")
        self.btn_refresh.setStyleSheet("")  # placeholder, usa class
        self.btn_refresh.clicked.connect(self._refresh_models)
        hb_layout.addWidget(self.btn_refresh)

        # RAG
        self.rag_btn = QPushButton("📄 RAG")
        self.rag_btn.setObjectName("ragBtn")
        self.rag_btn.setCheckable(True)
        self.rag_btn.setChecked(True)
        self.rag_btn.clicked.connect(self._toggle_rag)
        hb_layout.addWidget(self.rag_btn)

        # Idioma
        self.lang_sel = QComboBox()
        self.lang_sel.addItem("🇪🇸 ES", "es")
        self.lang_sel.addItem("🇬🇧 EN", "en")
        self.lang_sel.setFixedWidth(65)
        self.lang_sel.currentIndexChanged.connect(self._change_lang)
        hb_layout.addWidget(self.lang_sel)

        # Modo
        self.mode_sel = QComboBox()
        self.mode_sel.addItem("🖥️ LM", "lmstudio")
        self.mode_sel.addItem("☁️ Cloud", "cloud")
        self.mode_sel.addItem("🏠 GGUF", "local_gguf")
        self.mode_sel.setFixedWidth(100)
        self.mode_sel.currentIndexChanged.connect(self._change_mode)
        hb_layout.addWidget(self.mode_sel)

        # Acciones
        for btn_data in [
            ("📊", "Resumir" if self.lang == "es" else "Summarize", self._summarize_docs),
            ("🌙", "Tema", self._toggle_theme),
            ("🔄", "Buscar actualizaciones", self._check_update),
        ]:
            btn = QPushButton(btn_data[0])
            btn.setFixedSize(34, 30)
            btn.setToolTip(btn_data[1])
            btn.setProperty("class", "headerBtn")
            btn.clicked.connect(btn_data[2])
            hb_layout.addWidget(btn)

        header_bar.setLayout(hb_layout)
        rp_layout.addWidget(header_bar)

        # ---- CHAT ----
        self.chat = QTextEdit()
        self.chat.setObjectName("chatArea")
        self.chat.setReadOnly(True)
        self.chat.setFont(QFont("Segoe UI", 10))
        rp_layout.addWidget(self.chat)

        # ---- INPUT BAR ----
        input_bar = QWidget()
        input_bar.setObjectName("inputBar")
        input_bar.setFixedHeight(72)
        ib_layout = QHBoxLayout()
        ib_layout.setContentsMargins(20, 12, 20, 12)
        ib_layout.setSpacing(10)

        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.setPlaceholderText(t("prompt_rag", self.lang))
        self.input.setFont(QFont("Segoe UI", 12))
        self.input.returnPressed.connect(self._send)
        ib_layout.addWidget(self.input)

        self.btn_send = QPushButton("▶")
        self.btn_send.setObjectName("btnSend")
        self.btn_send.setFixedSize(42, 42)
        self.btn_send.clicked.connect(self._send)
        ib_layout.addWidget(self.btn_send)

        for btn_data in [
            ("📋", "Exportar chat", self._export_chat),
            ("🌐", "Traducir", self._translate_last),
        ]:
            btn = QPushButton(btn_data[0])
            btn.setFixedSize(36, 36)
            btn.setToolTip(btn_data[1])
            btn.setProperty("class", "inputBtn")
            btn.clicked.connect(btn_data[2])
            ib_layout.addWidget(btn)

        self.typing_label = QLabel("")
        self.typing_label.setObjectName("typingLabel")

        input_bar.setLayout(ib_layout)
        rp_layout.addWidget(self.typing_label)
        rp_layout.addWidget(input_bar)

        right_panel.setLayout(rp_layout)
        h_layout.addWidget(right_panel)

        h_container.setLayout(h_layout)
        ml.addWidget(h_container)

        # ---- STATUS BAR ----
        self.sb = QStatusBar()
        self.lm_status = QLabel("🟡 Conectando...")
        self.lm_status.setObjectName("statusDisconnected")
        self.doc_count = QLabel("📄 0")
        self.doc_count.setObjectName("docCountLabel")
        self.sb.addWidget(self.lm_status)
        self.sb.addPermanentWidget(self.doc_count)
        self.setStatusBar(self.sb)

        central.setLayout(ml)
        self._msg("system", t("welcome", self.lang))

    # ---- EVENTOS DRAG & DROP ----
    def _on_drop(self, event):
        for url in event.mimeData().urls():
            fp = url.toLocalFile()
            if fp.lower().endswith(('.pdf', '.docx', '.txt')):
                self._load_doc(fp)

    def _browse(self, event=None):
        title = "Select documents" if self.lang == "en" else "Seleccionar documentos"
        files, _ = QFileDialog.getOpenFileNames(
            self, title, "",
            "Documents (*.pdf *.docx *.txt);;All files (*.*)")
        for f in files:
            self._load_doc(f)

    def _load_doc(self, filepath):
        if not os.path.exists(filepath):
            return
        self.progress_label.setText(t("loading", self.lang).format(os.path.basename(filepath)))
        self.btn_send.setEnabled(False)
        self._worker = DocLoadWorker(self.engine, filepath)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_doc_done)
        self._worker.error.connect(self._on_doc_error)
        self._worker.finished.connect(lambda: setattr(self, '_worker', None))
        self._worker.error.connect(lambda: setattr(self, '_worker', None))
        self._worker.start()

    def _on_progress(self, actual, total, msg):
        self.progress_label.setText(f"⏳ {t('progress', self.lang).format(actual, total)}")

    def _on_doc_done(self, result):
        self.btn_send.setEnabled(True)
        self.progress_label.setText("")
        try:
            if result and result.get("status") == "ok":
                self.doc_list.addItem(
                    QListWidgetItem(f"✅ {result['filename']} ({result['chunks']} {t('frags', self.lang)})")
                )
                self._msg("system",
                    t("loaded_ok", self.lang).format(
                        result['filename'], result['chunks'], result['total_chars']
                    )
                )
                self.sb.showMessage(f"✅ {result['filename']}", 3000)
            else:
                msg = result.get("message", t("error_unknown", self.lang)) if result else t("error_unknown", self.lang)
                self._msg("error", msg)
        except Exception as e:
            self._msg("error", t("error_display", self.lang).format(e))
        self._update_stats()

    def _on_doc_error(self, error):
        self.btn_send.setEnabled(True)
        self.progress_label.setText("")
        friendly = str(error)
        if "encrypted" in error.lower() or "decrypt" in error.lower():
            friendly = t("error_pdf_encrypted", self.lang)
        elif "timeout" in error.lower():
            friendly = t("error_timeout", self.lang)
        self._msg("error", friendly)
        self.sb.showMessage(t("status_error", self.lang), 5000)

    # ---- CHAT ----
    def _send(self):
        q = self.input.text().strip()
        if not q:
            return
        self.input.clear()
        self._msg("user", q)
        self.btn_send.setEnabled(False)
        self.input.setEnabled(False)
        self._current_response = ""
        self.typing_label.setText(t("typing", self.lang))
        uc = self.rag_btn.isChecked()
        self._stream_worker = StreamWorker(self.engine, q, uc)
        self._stream_worker.token.connect(self._on_token)
        self._stream_worker.finished.connect(self._on_response_done)
        self._stream_worker.error.connect(self._on_response_error)
        self._stream_worker.finished.connect(lambda: setattr(self, '_stream_worker', None))
        self._stream_worker.error.connect(lambda: setattr(self, '_stream_worker', None))
        self._stream_worker.start()

    def _on_token(self, token):
        try:
            self._current_response += token
            self.chat.insertPlainText(token)
            c = self.chat.textCursor()
            c.movePosition(QTextCursor.MoveOperation.End)
            self.chat.setTextCursor(c)
        except Exception:
            pass

    def _on_response_done(self, full):
        self.btn_send.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        self.typing_label.setText("")
        self.sb.showMessage(t("status_ok", self.lang), 2000)

    def _on_response_error(self, error):
        friendly = str(error)
        if "timeout" in error.lower():
            friendly = t("error_timeout", self.lang)
        self._msg("error", friendly)
        self.btn_send.setEnabled(True)
        self.input.setEnabled(True)
        self.sb.showMessage(t("status_error", self.lang), 5000)

    # ---- ACCIONES ----
    def _summarize_docs(self):
        if self.engine.vector_store.count == 0:
            self._msg("error", "No hay documentos cargados." if self.lang == "es" else "No documents loaded.")
            return
        self._msg("system", "📊 " + ("Generating summary..." if self.lang == "en" else "Generando resumen..."))
        self._current_response = ""
        self._summarize_worker = StreamWorker(self.engine, f"__summarize__:{self.lang}", use_context=False)
        self._summarize_worker.token.connect(self._on_token)
        self._summarize_worker.finished.connect(
            lambda r: self._msg("system", "✅ " + ("Summary ready" if self.lang == "en" else "Resumen listo")))
        self._summarize_worker.finished.connect(
            lambda: setattr(self, '_summarize_worker', None))
        self._summarize_worker.error.connect(
            lambda e: self._msg("error", f"Error: {e}"))
        self._summarize_worker.start()

    def _export_chat(self):
        path, _ = QFileDialog.getSaveFileName(self,
            "Export chat" if self.lang == "en" else "Exportar chat",
            "chat_docchat.txt", "TXT (*.txt);;All (*)")
        if path:
            try:
                self.engine.export_chat(self.chat.toHtml(), path)
                self.sb.showMessage("✅ " + ("Exported" if self.lang == "en" else "Exportado"), 5000)
            except Exception as e:
                self._msg("error", str(e))

    def _translate_last(self):
        import re
        html = self.chat.toHtml()
        parts = re.findall(r'<p[^>]*><b[^>]*>🤖 DocChat:</b> (.*?)</p>', html, re.DOTALL)
        if not parts:
            self._msg("error", "No hay respuesta para traducir." if self.lang == "es" else "No response to translate.")
            return
        last = parts[-1]
        last = re.sub(r'<[^>]+>', '', last)
        for e, r in [('&amp;','&'),('&lt;','<'),('&gt;','>')]: last = last.replace(e, r)
        if not last.strip():
            self._msg("error", "Texto vacío." if self.lang == "es" else "Empty text.")
            return
        target = "es" if self.lang == "en" else "en"
        lang_n = {"es": "español", "en": "inglés"}
        self._msg("system", f"🌐 " + (f"Translating to {lang_n[target]}..." if self.lang == "en" else f"Traduciendo a {lang_n[target]}..."))
        self._translate_worker = StreamWorker(self.engine, f"__translate__:{target}:{last}", use_context=False)
        self._translate_worker.token.connect(self._on_token)
        self._translate_worker.finished.connect(
            lambda r: self._msg("system", "✅ " + (f"Translation to {lang_n[target]} ready" if self.lang == "en" else f"Traducción a {lang_n[target]} lista")))
        self._translate_worker.finished.connect(
            lambda: setattr(self, '_translate_worker', None))
        self._translate_worker.error.connect(
            lambda e: self._msg("error", f"Error: {e}"))
        self._translate_worker.start()

    def _toggle_theme(self):
        """Alternar entre tema oscuro y claro."""
        self._theme = "light" if self._theme == "dark" else "dark"
        # Actualizar el tema global de la aplicación
        QApplication.instance().setStyleSheet(build_theme(self._theme))
        # Actualizar colores inline (sidebar, right_panel tienen stylesheet fijo)
        self._apply_theme_colors()
        self.sb.showMessage(
            ("☀️ Light theme" if self._theme == "light" else "🌙 Dark theme"),
            2000)

    def _apply_theme_colors(self):
        """Actualizar colores de widgets que tienen stylesheet inline."""
        pass  # El tema global se encarga de casi todo

    def _clear_all(self):
        title = t("clear_all", self.lang)
        confirm = t("clear_confirm", self.lang)
        r = QMessageBox.question(self, title, confirm,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.engine.clear()
            self.doc_list.clear()
            self._msg("system", t("clear_done", self.lang))
            self._update_stats()

    def _change_lang(self, idx):
        self.lang = self.lang_sel.currentData()
        self.setWindowTitle(t("app_name", self.lang))
        self.header.setText(t("app_subtitle", self.lang))
        self.drop_zone.setText(t("drop_hint", self.lang))
        self.drop_desc.setText(t("drop_desc", self.lang))
        self.btn_clear.setText(t("clear_all", self.lang))
        self.doc_label.setText(t("loaded", self.lang))
        self._toggle_rag()
        self._check_status()
        self.chat.clear()
        self._msg("system", t("welcome", self.lang))

    def _change_mode(self, idx):
        mode = self.mode_sel.currentData()
        if mode == "cloud":
            from PyQt6.QtWidgets import QInputDialog
            key, ok = QInputDialog.getText(self,
                "☁️ OpenAI API Key",
                "Paste your OpenAI API key (sk-...):\nGet it at: https://platform.openai.com/api-keys"
                if self.lang == "en" else
                "Pega tu API key de OpenAI (sk-...):\nConsíguela en: https://platform.openai.com/api-keys",
                text=os.getenv("OPENAI_API_KEY", ""))
            if ok and key.strip():
                self.engine.set_mode("cloud", key.strip())
                os.environ["OPENAI_API_KEY"] = key.strip()
                self.sb.showMessage("☁️ Cloud mode activated" if self.lang == "en" else "☁️ Modo Cloud activado", 3000)
            else:
                self.mode_sel.setCurrentIndex(0)
                self.sb.showMessage("🖥️ LM Studio mode" if self.lang == "en" else "🖥️ Modo LM Studio", 3000)
        elif mode == "local_gguf":
            self.engine.set_mode("local_gguf")
            self.sb.showMessage("🏠 GGUF Local mode" if self.lang == "en" else "🏠 Modo GGUF Local", 3000)
        else:
            self.engine.set_mode("lmstudio")
            self.sb.showMessage("🖥️ LM Studio mode" if self.lang == "en" else "🖥️ Modo LM Studio", 3000)
        self._check_status()

    def _toggle_rag(self):
        if self.rag_btn.isChecked():
            self.rag_btn.setText(t("rag_on", self.lang))
            self.input.setPlaceholderText(t("prompt_rag", self.lang))
        else:
            self.rag_btn.setText(t("chat_mode", self.lang))
            self.input.setPlaceholderText(t("prompt_chat", self.lang))

    def _refresh_models(self):
        models = self.engine.available_models()
        self.model_sel.clear()
        for m in models:
            self.model_sel.addItem(m)
        self.sb.showMessage(t("models_updated", self.lang).format(len(models)), 3000)

    def _check_update(self):
        self.sb.showMessage("🔄 " + ("Checking for updates..." if self.lang == "en" else "Buscando actualizaciones..."), 5000)
        try:
            from docchat.updater import check_for_updates
            info = check_for_updates()
            if info:
                msg = (
                    f"🔄 New version: v{info['version']}\n"
                    f"   Current: v{info['current']}\n"
                    f"   {info.get('download_url', '')}" if self.lang == "en" else
                    f"🔄 Nueva versión: v{info['version']}\n"
                    f"   Actual: v{info['current']}\n"
                    f"   {info.get('download_url', '')}"
                )
                self._msg("system", msg)
                self.sb.showMessage(f"🔄 v{info['version']} " + ("available" if self.lang == "en" else "disponible"), 5000)
            else:
                self._msg("system", "✅ " + ("You have the latest version." if self.lang == "en" else "Tienes la versión más reciente."))
                self.sb.showMessage("✅ " + ("Up to date" if self.lang == "en" else "Actualizado"), 3000)
        except Exception as e:
            self._msg("system", f"❌ " + ("Error checking: " if self.lang == "en" else "Error al buscar: ") + f"{e}")

    def _check_update_async(self):
        try:
            from docchat.updater import check_for_updates
            info = check_for_updates()
            if info:
                msg = (
                    f"🔄 New version available: v{info['version']}\n"
                    f"   Current: v{info['current']}\n"
                    f"   Click the 🔄 button for details." if self.lang == "en" else
                    f"🔄 Nueva versión disponible: v{info['version']}\n"
                    f"   Actual: v{info['current']}\n"
                    f"   Haz clic en el botón 🔄 para más info."
                )
                self._msg("system", msg)
                self.sb.showMessage(f"🔄 v{info['version']} " + ("available" if self.lang == "en" else "disponible"), 8000)
        except Exception:
            pass

    def _check_status(self):
        if self.engine.is_available():
            self.lm_status.setText("🟢 " + ("Connected" if self.lang == "en" else "Conectado"))
            self.lm_status.setObjectName("statusConnected")
            self.lm_status.style().unpolish(self.lm_status)
            self.lm_status.style().polish(self.lm_status)
            self._refresh_models()
        else:
            self.lm_status.setText("🔴 " + ("Disconnected" if self.lang == "en" else "Desconectado"))
            self.lm_status.setObjectName("statusDisconnected")
            self.lm_status.style().unpolish(self.lm_status)
            self.lm_status.style().polish(self.lm_status)
            QTimer.singleShot(10000, self._check_status)

    def _update_stats(self):
        s = self.engine.get_stats()
        self.doc_count.setText(t("docs_count", self.lang).format(s['documents']))

    def _msg(self, role, text):
        colors = {"system": self._colors["text_dim"], "user": self._colors["accent"],
                  "assistant": self._colors["success"], "error": self._colors["danger"]}
        color = colors.get(role, self._colors["text_bright"])
        prefix_map = {
            "user": t("user_prefix", self.lang),
            "assistant": t("ai_prefix", self.lang),
            "system": t("system", self.lang),
            "error": t("error_prefix", self.lang),
        }
        prefix = prefix_map.get(role, t("ai_prefix", self.lang))
        if role == "system":
            html = f'<p style="color:{color}; text-align:center; font-size:12px; padding:8px 0;">{text}</p>'
        else:
            html = f'<p style="margin:6px 0;"><b style="color:{color};">{prefix}:</b> '
            html += f'<span style="color:{self._colors["text"]};">{text}</span></p>'
        self.chat.append(html)
        c = self.chat.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.chat.setTextCursor(c)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DocChat")
    app.setStyle("Fusion")

    # Icono
    for icon_path in [
        os.path.join(os.path.dirname(__file__), "..", "favicon.ico"),
        os.path.join(os.path.dirname(__file__), "..", "docchat_icon.png"),
        os.path.join(os.path.dirname(sys.argv[0]), "favicon.ico"),
        getattr(__import__('sys'), '_MEIPASS', '') + "/favicon.ico",
        "favicon.ico",
        "docchat_icon.png",
    ]:
        if icon_path and os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            app.setWindowIcon(QIcon(icon_path))
            break

    # Tema CSS global único
    app.setStyleSheet(build_theme("dark"))

    w = DocChatWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
