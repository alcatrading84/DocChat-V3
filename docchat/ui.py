"""DocChat UI v3 — Interfaz mejorada con todas las nuevas funciones.

Novedades:
- 🏆 Indicador de modo (offline/online/híbrido)
- 🌐 Botón para abrir Web UI
- 🔄 Notificación de actualizaciones
- 📄 Vista previa de documentos (doble clic)
- 🎨 Resaltado de fuentes en respuestas
- 📊 Panel de estadísticas
"""

import sys
import os
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QSplitter, QStatusBar,
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox,
    QTabWidget, QGroupBox, QFormLayout, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QIcon, QAction

from docchat.engine import DocChatEngine
from docchat.lang import t

logger = logging.getLogger(__name__)


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
            # Detectar tareas especiales
            if self.question == "__summarize__":
                full = self.engine.summarize(
                    on_token=lambda t: self.token.emit(t)
                )
            elif self.question.startswith("__translate__:"):
                parts = self.question.split(":", 2)
                target = parts[1]
                text = parts[2]
                full = self.engine.translate(
                    text, target=target,
                    on_token=lambda t: self.token.emit(t)
                )
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
# DIÁLOGO DE ESTADÍSTICAS
# =============================================================================

class StatsDialog(QDialog):
    def __init__(self, stats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 DocChat Stats")
        self.setMinimumSize(400, 350)
        layout = QVBoxLayout()

        title = QLabel("📊 Estadísticas de DocChat")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        layout.addWidget(title)

        form = QFormLayout()

        if "metrics" in stats:
            m = stats["metrics"]
            form.addRow("📄 Documentos:", QLabel(str(m.get("docs_processed", 0))))
            form.addRow("💬 Consultas:", QLabel(str(m.get("queries", 0))))
            form.addRow("❌ Errores:", QLabel(str(m.get("errors", 0))))
            form.addRow("📏 Char/doc (prom):", QLabel(str(m.get("avg_doc_chars", 0))))
            form.addRow("⏱️  Duración prom:", QLabel(f"{m.get('avg_duration_ms', 0)}ms"))
        else:
            form.addRow("📄 En memoria:", QLabel(str(stats.get("documents", 0))))

        form.addRow("🔧 Modo:", QLabel(stats.get("mode", "N/A")))
        form.addRow("🧠 Local:", QLabel("✅ Sí" if stats.get("using_local") else "❌ No"))
        form.addRow("📁 Fuentes:", QLabel(", ".join(stats.get("sources", [])) or "Ninguna"))

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.setLayout(layout)


# =============================================================================
# DIÁLOGO DE ACTUALIZACIÓN
# =============================================================================

class UpdateDialog(QDialog):
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔄 Actualización disponible")
        self.setMinimumSize(450, 300)
        layout = QVBoxLayout()

        title = QLabel(f"🔄 DocChat v{update_info['version']} disponible!")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4fc3f7;")
        layout.addWidget(title)

        notes = QLabel(f"Tu versión: v{update_info['current']}")
        notes.setStyleSheet("color: #888;")
        layout.addWidget(notes)

        if update_info.get("notes"):
            notes_box = QTextEdit()
            notes_box.setReadOnly(True)
            notes_box.setPlainText(update_info["notes"])
            notes_box.setMaximumHeight(150)
            layout.addWidget(QLabel("Notas de la versión:"))
            layout.addWidget(notes_box)

        buttons = QDialogButtonBox()
        btn_download = buttons.addButton(
            "📥 Descargar", QDialogButtonBox.ButtonRole.AcceptRole
        )
        btn_later = buttons.addButton(
            "Más tarde", QDialogButtonBox.ButtonRole.RejectRole
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)


# =============================================================================
# VENTANA PRINCIPAL
# =============================================================================

class DocChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "es"
        self._current_response = ""
        self._engine_ready = False

        # Inicializar motor (con modo auto)
        logger.info("Inicializando DocChat Engine v3...")
        self.engine = DocChatEngine()
        mode = self.engine.mode
        logger.info(f"Modo detectado: {mode}")

        self.setWindowTitle(t("app_name", self.lang))
        self.setMinimumSize(1000, 700)
        self.resize(1200, 750)

        self._init_ui()
        self._check_status()

        # Web UI (referencia)
        self._web_server = None

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        ml = QVBoxLayout()
        ml.setContentsMargins(4, 4, 4, 4)

        # ==================== HEADER ====================
        header_layout = QHBoxLayout()
        self.header = QLabel(t("app_subtitle", self.lang))
        self.header.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 8px 12px;
            background: #1a1a2e; color: #e0e0e0; border-radius: 8px;
        """)
        header_layout.addWidget(self.header)

        # Badge de modo
        self.mode_badge = QLabel("")
        self.mode_badge.setStyleSheet("""
            padding: 4px 10px; border-radius: 10px;
            font-size: 11px; font-weight: bold;
        """)
        header_layout.addWidget(self.mode_badge)

        header_layout.addStretch()

        # Botón Web UI
        self.btn_web = QPushButton("🌐 Web UI")
        self.btn_web.setToolTip("Abrir interfaz web en el navegador")
        self.btn_web.setStyleSheet("""
            QPushButton { background: #2a2a4e; color: #e0e0e0;
                border: 1px solid #444; border-radius: 4px;
                padding: 4px 10px; font-size: 11px; }
            QPushButton:hover { background: #3a3a6e; }
        """)
        self.btn_web.clicked.connect(self._toggle_web_ui)
        header_layout.addWidget(self.btn_web)

        # Botón Stats
        self.btn_stats = QPushButton("📊")
        self.btn_stats.setToolTip("Ver estadísticas")
        self.btn_stats.setFixedWidth(30)
        self.btn_stats.setStyleSheet("""
            QPushButton { background: #2a2a4e; color: #e0e0e0;
                border: 1px solid #444; border-radius: 4px; }
            QPushButton:hover { background: #3a3a6e; }
        """)
        self.btn_stats.clicked.connect(self._show_stats)
        header_layout.addWidget(self.btn_stats)

        ml.addLayout(header_layout)

        # ==================== SPLITTER ====================
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- PANEL IZQUIERDO: Documentos ----
        dp = QWidget()
        dl = QVBoxLayout()
        dl.setSpacing(4)

        dl.addWidget(QLabel(t("docs_title", self.lang)))
        self.drop_desc = QLabel(t("drop_desc", self.lang))
        dl.addWidget(self.drop_desc)

        # Zona de drop mejorada
        self.drop_zone = QLabel(t("drop_hint", self.lang))
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setMinimumHeight(80)
        self.drop_zone.setStyleSheet("""
            QLabel {
                background: #0d0d1a; color: #888;
                border: 2px dashed #444; border-radius: 8px;
                font-size: 16px; font-weight: bold;
                padding: 8px;
            }
            QLabel:hover { border-color: #4fc3f7; color: #4fc3f7; }
        """)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.mousePressEvent = lambda e: self._browse()
        self.drop_zone.dragEnterEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasUrls() else None
        self.drop_zone.dragMoveEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasUrls() else None
        self.drop_zone.dropEvent = self._on_drop
        dl.addWidget(self.drop_zone)

        # Barra de progreso (nueva)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #333; border-radius: 2px;
                text-align: center; height: 12px; font-size: 10px; }
            QProgressBar::chunk { background: #4fc3f7; border-radius: 2px; }
        """)
        dl.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888; font-size: 11px;")
        dl.addWidget(self.progress_label)

        # Lista de documentos
        self.doc_list = QListWidget()
        self.doc_list.setStyleSheet("""
            QListWidget { background: #0d0d1a; color: #ccc;
                border: 1px solid #333; border-radius: 4px; }
            QListWidget::item { padding: 4px; }
            QListWidget::item:hover { background: #1a1a3e; }
        """)
        self.doc_list.itemDoubleClicked.connect(self._preview_doc)
        self.doc_label = QLabel(t("loaded", self.lang))
        dl.addWidget(self.doc_label)
        dl.addWidget(self.doc_list)

        # Botón Limpiar + tipo de modelo
        bottom_row = QHBoxLayout()
        self.btn_clear = QPushButton(t("clear_all", self.lang))
        self.btn_clear.setStyleSheet("""
            QPushButton { background: #5c2e2e; color: white;
                border: none; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background: #7a3e3e; }
        """)
        self.btn_clear.clicked.connect(self._clear_all)
        bottom_row.addWidget(self.btn_clear)

        # Selector de modo (nuevo)
        self.mode_sel = QComboBox()
        self.mode_sel.addItem("🏆 Auto", "auto")
        self.mode_sel.addItem("🧠 Local", "offline")
        self.mode_sel.addItem("☁️ LM Studio", "online")
        self.mode_sel.setStyleSheet("""
            QComboBox { background: #1a1a2e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px; padding: 2px; }
        """)
        self.mode_sel.currentIndexChanged.connect(self._change_mode)
        bottom_row.addWidget(self.mode_sel)

        dl.addLayout(bottom_row)

        # Info del modelo (nuevo)
        self.model_info = QLabel("")
        self.model_info.setStyleSheet("color: #666; font-size: 10px; padding: 2px;")
        self.model_info.setWordWrap(True)
        dl.addWidget(self.model_info)

        dp.setLayout(dl)
        splitter.addWidget(dp)

        # ---- PANEL DERECHO: Chat ----
        cp = QWidget()
        cl = QVBoxLayout()
        cl.setSpacing(4)

        # Toolbar
        tr = QHBoxLayout()
        tr.addWidget(QLabel("🧠:"))
        self.model_sel = QComboBox()
        self.model_sel.setMinimumWidth(180)
        self.model_sel.setStyleSheet("""
            QComboBox { background: #1a1a2e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px; padding: 4px; }
        """)
        tr.addWidget(self.model_sel)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(30)
        self.btn_refresh.setToolTip("Refrescar modelos")
        self.btn_refresh.clicked.connect(self._refresh_models)
        tr.addWidget(self.btn_refresh)

        self.rag_btn = QPushButton("📄 RAG ON")
        self.rag_btn.setCheckable(True)
        self.rag_btn.setChecked(True)
        self.rag_btn.setStyleSheet("""
            QPushButton { background: #0d7377; color: white;
                border: none; border-radius: 4px; padding: 4px 8px; }
            QPushButton:checked { background: #2d5c2e; }
        """)
        self.rag_btn.clicked.connect(self._toggle_rag)
        tr.addWidget(self.rag_btn)

        # Idioma
        self.lang_sel = QComboBox()
        self.lang_sel.addItem("🇪🇸 ES", "es")
        self.lang_sel.addItem("🇬🇧 EN", "en")
        self.lang_sel.setFixedWidth(70)
        self.lang_sel.setStyleSheet("""
            QComboBox { background: #1a1a2e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 4px; padding: 2px; }
        """)
        self.lang_sel.currentIndexChanged.connect(self._change_lang)
        tr.addWidget(self.lang_sel)

        # Botones extra
        self.btn_summarize = QPushButton("📊 Resumir")
        self.btn_summarize.setStyleSheet("""
            QPushButton { background: #2d5c2e; color: white; border: none;
                border-radius: 4px; padding: 4px 8px; }
            QPushButton:hover { background: #3d7c3e; }
        """)
        self.btn_summarize.clicked.connect(self._summarize_docs)
        tr.addWidget(self.btn_summarize)

        self.btn_theme = QPushButton("🌙")
        self.btn_theme.setFixedWidth(30)
        self.btn_theme.setToolTip("Cambiar tema")
        self.btn_theme.clicked.connect(self._toggle_theme)
        tr.addWidget(self.btn_theme)

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
        self.input.setPlaceholderText(t("prompt_rag", self.lang))
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

        # Botones extra en input row
        self.btn_export = QPushButton("📋")
        self.btn_export.setFixedWidth(36)
        self.btn_export.setToolTip("Exportar chat")
        self.btn_export.setStyleSheet("""
            QPushButton { background: #2a2a4e; color: white; border: none;
                border-radius: 4px; }
            QPushButton:hover { background: #3a3a6e; }
        """)
        self.btn_export.clicked.connect(self._export_chat)
        ir.addWidget(self.btn_export)

        self.btn_translate = QPushButton("🌐")
        self.btn_translate.setFixedWidth(36)
        self.btn_translate.setToolTip("Traducir última respuesta")
        self.btn_translate.setStyleSheet("""
            QPushButton { background: #2a2a4e; color: white; border: none;
                border-radius: 4px; }
            QPushButton:hover { background: #3a3a6e; }
        """)
        self.btn_translate.clicked.connect(self._translate_last)
        ir.addWidget(self.btn_translate)

        cl.addLayout(ir)
        cp.setLayout(cl)
        splitter.addWidget(cp)

        splitter.setSizes([280, 720])
        ml.addWidget(splitter)

        # ==================== STATUS BAR ====================
        self.sb = QStatusBar()
        self.lm_status = QLabel("🟡 Iniciando...")
        self.doc_count = QLabel("📄 0")
        self.update_btn = QPushButton("🔄 Buscar actualizaciones")
        self.update_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #4fc3f7;
                border: 1px solid #4fc3f7; border-radius: 10px;
                padding: 2px 8px; font-size: 10px; }
            QPushButton:hover { background: #1a3a5c; }
        """)
        self.update_btn.clicked.connect(self._check_updates_manual)
        self.update_btn.setVisible(False)  # Solo visible cuando hay update

        self.sb.addWidget(self.lm_status)
        self.sb.addPermanentWidget(self.update_btn)
        self.sb.addPermanentWidget(self.doc_count)
        self.setStatusBar(self.sb)

        central.setLayout(ml)

        # Bienvenida
        if self.engine.is_available():
            self._show_welcome()
        else:
            self._msg("system",
                "⏳ Iniciando modelo local...\n"
                "Esto puede tomar unos segundos la primera vez."
            )

        # Verificar actualizaciones en segundo plano
        QTimer.singleShot(3000, self._check_updates_background)

    def _show_welcome(self):
        """Mostrar mensaje de bienvenida con info del modo."""
        mode_info = self.engine.get_mode_info()
        mode_text = {
            "offline": "🧠 **Modo Local** — Sin dependencias externas",
            "online": "☁️ **Modo LM Studio** — Servidor externo",
            "hybrid": "🏆 **Modo Híbrido** — LM Studio + fallback local",
        }.get(mode_info.get("mode", "offline"), "Modo desconocido")

        local_info = ""
        if mode_info.get("using_local") and mode_info.get("local_model"):
            lm = mode_info["local_model"]
            local_info = f"\n📦 Modelo: {lm.get('model', 'N/A')} ({lm.get('size_gb', '?')} GB)"

        welcome = (
            f"📄 **DocChat v3** — Asistente Local de Documentos\n\n"
            f"{mode_text}{local_info}\n\n"
            f"1️⃣ Arrastra un documento al panel izquierdo\n"
            f"2️⃣ Escribe preguntas sobre su contenido\n"
            f"3️⃣ Las respuestas aparecen **en tiempo real**\n\n"
            f"✅ 100% local · Sin API keys · Sin internet"
        )
        self._msg("system", welcome)

    def _update_mode_badge(self):
        """Actualizar el badge de modo en el header."""
        mode_info = self.engine.get_mode_info()
        mode = mode_info.get("mode", "offline")

        colors = {
            "offline": ("#2d5c2e", "🧠 LOCAL"),
            "online": ("#0d7377", "☁️ LM STUDIO"),
            "hybrid": ("#4a3a8e", "🏆 HÍBRIDO"),
        }
        bg, text = colors.get(mode, ("#444", "N/A"))

        self.mode_badge.setText(text)
        self.mode_badge.setStyleSheet(f"""
            background: {bg}; color: white; padding: 4px 10px;
            border-radius: 10px; font-size: 11px; font-weight: bold;
        """)

        # Actualizar info del modelo
        if mode_info.get("local_model"):
            lm = mode_info["local_model"]
            self.model_info.setText(
                f"📦 {lm.get('model', '')} ({lm.get('size_gb', '?')} GB)"
            )
        else:
            self.model_info.setText(mode_info.get("mode", ""))

    def _change_mode(self, idx):
        """Cambiar modo de operación."""
        mode_map = {"auto": None, "offline": "offline", "online": "online"}
        new_mode = mode_map.get(self.mode_sel.currentData(), None)

        if new_mode != self.engine.mode:
            reply = QMessageBox.question(
                self, "Cambiar modo",
                "¿Cambiar modo de operación?\nSe reiniciará el motor.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.engine = DocChatEngine(mode=new_mode)
                self._update_mode_badge()
                self._msg("system", f"🔄 Modo cambiado a: {new_mode or 'auto'}")
                self._check_status()

    # ----- Drag & Drop -----
    def _on_drop(self, event):
        for url in event.mimeData().urls():
            fp = url.toLocalFile()
            self._load_doc(fp)

    def _browse(self, event=None):
        title = "Seleccionar documentos" if self.lang == "es" else "Select documents"
        files, _ = QFileDialog.getOpenFileNames(
            self, title, "",
            "Documentos (*.pdf *.docx *.txt *.md *.html *.csv *.xlsx *.pptx *.json *.xml *.yaml *.py *.js *.ts);;All files (*.*)")  # noqa
        for f in files:
            self._load_doc(f)

    # ----- Carga de documentos -----
    def _load_doc(self, filepath):
        if not os.path.exists(filepath):
            return
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in ('.pdf', '.docx', '.txt', '.md', '.html', '.htm',
                       '.csv', '.xlsx', '.xls', '.pptx', '.json', '.xml',
                       '.yaml', '.yml', '.py', '.js', '.ts', '.java',
                       '.cpp', '.c', '.cs', '.go', '.rs', '.rb', '.php',
                       '.swift', '.kt', '.sql', '.sh', '.bat', '.ps1', '.r'):
            return

        self.progress_label.setText(
            t("loading", self.lang).format(os.path.basename(filepath))
        )
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_send.setEnabled(False)

        self._worker = DocLoadWorker(self.engine, filepath)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_doc_done)
        self._worker.error.connect(self._on_doc_error)
        self._worker.finished.connect(lambda: setattr(self, '_worker', None))
        self._worker.error.connect(lambda: setattr(self, '_worker', None))
        self._worker.start()

    def _on_progress(self, actual, total, msg):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(actual)
        self.progress_label.setText(f"⏳ {msg}")

    def _on_doc_done(self, result):
        self.btn_send.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        try:
            if result and result.get("status") == "ok":
                fn = result['filename']
                chunks = result['chunks']
                chars = result['total_chars']
                self.doc_list.addItem(
                    QListWidgetItem(f"✅ {fn} ({chunks} {t('frags', self.lang)})")
                )
                self._msg("system",
                    t("loaded_ok", self.lang).format(fn, chunks, chars)
                )
                self.sb.showMessage(f"✅ {fn}", 3000)
            else:
                msg = result.get("message", t("error_unknown", self.lang)) if result else t("error_unknown", self.lang)
                self._msg("error", msg)
        except Exception as e:
            self._msg("error", t("error_display", self.lang).format(e))
        self._update_stats()

    def _on_doc_error(self, error):
        self.btn_send.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        friendly = str(error)
        if "encrypted" in error.lower() or "decrypt" in error.lower():
            friendly = t("error_pdf_encrypted", self.lang)
        elif "timeout" in error.lower():
            friendly = t("error_timeout", self.lang)
        elif "tesseract" in error.lower():
            friendly = (
                "📄 El PDF parece escaneado (imágenes).\n"
                "Para leerlo con OCR, instala Tesseract:\n"
                "  https://github.com/UB-Mannheim/tesseract/wiki\n"
                "Y luego: pip install pytesseract Pillow pdf2image"
            )
        self._msg("error", friendly)
        self.sb.showMessage(t("status_error", self.lang), 5000)

    # ----- Vista previa de documento -----
    def _preview_doc(self, item):
        """Mostrar vista previa del documento (doble clic)."""
        text = item.text()
        filename = text.replace("✅ ", "").split(" (")[0] if "✅ " in text else text

        # Buscar en el vector store
        for doc in self.engine.vector_store.documents:
            if doc["source"] == filename:
                preview = QMessageBox(self)
                preview.setWindowTitle(f"📄 Vista previa: {filename}")
                preview.setText(doc["text"][:2000])
                preview.setInformativeText(
                    f"\n\n... ({len(doc['text'])} caracteres totales)"
                )
                preview.exec()
                return

        self._msg("system", f"No se encontró contenido de: {filename}")

    # ----- Chat -----
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

    # ----- Nuevas funciones -----
    def _summarize_docs(self):
        """Resumir documentos cargados."""
        if self.engine.vector_store.count == 0:
            self._msg("error", "No hay documentos cargados para resumir.")
            return
        self._msg("system", "📊 Generando resumen...")
        self._current_response = ""
        w = StreamWorker(self.engine, "__summarize__", use_context=False)
        w.task_type = "summarize"
        w.token.connect(self._on_token)
        w.finished.connect(lambda r: self._msg("system", "✅ Resumen completado"))
        w.error.connect(lambda e: self._msg("error", f"Error al resumir: {e}"))
        w.start()

    def _export_chat(self):
        """Exportar chat a archivo TXT."""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar chat", "chat_docchat.txt",
            "Archivos de texto (*.txt);;Todos (*)"
        )
        if path:
            try:
                self.engine.export_chat(self.chat.toHtml(), path)
                self.sb.showMessage(f"✅ Exportado: {path}", 5000)
            except Exception as e:
                self._msg("error", f"Error al exportar: {e}")

    def _translate_last(self):
        """Traducir último mensaje del asistente al inglés/español alternando."""
        # Buscar última respuesta del asistente en el chat
        html = self.chat.toHtml()
        import re
        # Extraer texto entre tags de color #81c784 (verde del asistente)
        parts = re.findall(r'<span[^>]*style="[^"]*color:#81c784[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
        if not parts:
            self._msg("error", "No hay respuesta para traducir.")
            return
        last = parts[-1]
        # Limpiar HTML
        last = re.sub(r'<[^>]+>', '', last)
        last = last.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        if not last.strip():
            self._msg("error", "No hay texto que traducir.")
            return
        target = "es" if self.lang == "en" else "en"
        lang_name = {"es": "español", "en": "inglés"}
        self._msg("system", f"🌐 Traduciendo a {lang_name[target]}...")
        self._current_response = ""
        w = StreamWorker(self.engine, f"__translate__:{target}:{last}", use_context=False)
        w.task_type = "translate"
        w.token.connect(self._on_token)
        w.finished.connect(lambda r: self._msg("system", f"✅ Traducción a {lang_name[target]} completada"))
        w.error.connect(lambda e: self._msg("error", f"Error al traducir: {e}"))
        w.start()

    _dark_theme = True
    def _toggle_theme(self):
        """Alternar entre tema oscuro y claro."""
        self._dark_theme = not self._dark_theme
        if self._dark_theme:
            self.btn_theme.setText("🌙")
            app = self.window().styleSheet()
            self.setStyleSheet("""
                QMainWindow { background: #12121a; }
                QToolTip { background: #1a1a2e; color: #e0e0e0; border: 1px solid #444; padding: 4px; }
            """)
            self.chat.setStyleSheet("QTextEdit { background: #0d0d1a; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; padding: 8px; }")
        else:
            self.btn_theme.setText("☀️")
            self.setStyleSheet("""
                QMainWindow { background: #f5f5f5; }
                QToolTip { background: #fff; color: #333; border: 1px solid #ccc; }
            """)
            self.chat.setStyleSheet("QTextEdit { background: #ffffff; color: #222222; border: 1px solid #ccc; border-radius: 4px; padding: 8px; }")

    # ----- Acciones -----
    def _clear_all(self):
        r = QMessageBox.question(
            self, t("clear_all", self.lang), t("clear_confirm", self.lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
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
        self.btn_clear.setText(t("clear_all", self.lang))
        self.doc_label.setText(t("loaded", self.lang))
        self.drop_desc.setText(t("drop_desc", self.lang))
        self._toggle_rag()
        self.typing_label.setText("")
        self.input.setPlaceholderText(
            t("prompt_rag" if self.rag_btn.isChecked() else "prompt_chat", self.lang)
        )
        self.chat.clear()
        self._show_welcome()

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

    # ----- Web UI -----
    def _toggle_web_ui(self):
        if self._web_server:
            try:
                import webbrowser
                webbrowser.open("http://127.0.0.1:5000")
            except Exception:
                pass
            return

        try:
            from docchat.web_ui import start_web_ui
            self._web_server = start_web_ui(
                self.engine, host="127.0.0.1", port=5000,
                open_browser=True
            )
            self.btn_web.setText("🌐 Abrir Web UI")
            self.sb.showMessage("🌐 Web UI iniciada en http://127.0.0.1:5000", 5000)
        except ImportError as e:
            QMessageBox.information(
                self, "Web UI",
                f"Para la Web UI necesitas:\n  pip install flask\n\nError: {e}"
            )
        except Exception as e:
            self._msg("error", f"Error iniciando Web UI: {e}")

    # ----- Stats -----
    def _show_stats(self):
        try:
            stats = self.engine.get_stats()
            dialog = StatsDialog(stats, self)
            dialog.exec()
        except Exception as e:
            self._msg("error", f"Error mostrando estadísticas: {e}")

    # ----- Updates -----
    def _check_updates_background(self):
        try:
            from docchat.updater import check_for_updates_async

            def on_update(update_info):
                self.update_btn.setText(
                    f"🔄 v{update_info['version']} disponible!"
                )
                self.update_btn.setVisible(True)

            check_for_updates_async(callback=on_update)
        except Exception:
            pass

    def _check_updates_manual(self):
        try:
            from docchat.updater import check_for_updates

            self.sb.showMessage("🔍 Buscando actualizaciones...", 2000)
            update_info = check_for_updates()

            if update_info:
                dialog = UpdateDialog(update_info, self)
                if dialog.exec():
                    # Descargar
                    self.sb.showMessage("📥 Descargando actualización...", 2000)
                    from docchat.updater import download_update
                    exe_path = download_update(update_info)
                    if exe_path:
                        from docchat.updater import install_update
                        install_update(exe_path)
            else:
                QMessageBox.information(
                    self, "Actualizaciones",
                    "✅ Tienes la versión más reciente."
                )
                self.update_btn.setVisible(False)
        except Exception as e:
            self._msg("error", f"Error buscando actualizaciones: {e}")

    # ----- Status -----
    def _check_status(self):
        if self.engine.is_available():
            self.lm_status.setText(t("connected", self.lang))
            self.lm_status.setStyleSheet("color: #69db7c;")
            self._refresh_models()
            self._update_mode_badge()
            if not self._engine_ready:
                self._engine_ready = True
                self._show_welcome()
        else:
            self.lm_status.setText("🟡 Cargando modelo local...")
            self.lm_status.setStyleSheet("color: #ffd43b;")
            # Reintentar cada 5 segundos hasta que esté listo
            QTimer.singleShot(5000, self._check_status)

    def _update_stats(self):
        s = self.engine.get_stats()
        self.doc_count.setText(t("docs_count", self.lang).format(s['documents']))

    # ----- Mensajes -----
    def _msg(self, role, text):
        colors = {"system": "#888", "user": "#4fc3f7",
                  "assistant": "#81c784", "error": "#ef5350"}
        color = colors.get(role, "#fff")
        prefix_map = {
            "user": t("user_prefix", self.lang),
            "assistant": t("ai_prefix", self.lang),
            "system": t("system", self.lang),
            "error": t("error_prefix", self.lang),
        }
        prefix = prefix_map.get(role, t("ai_prefix", self.lang))

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
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("DocChat")
    app.setStyle("Fusion")

    # Icono
    icon_paths = [
        os.path.join(os.path.dirname(__file__), "..", "favicon.ico"),
        os.path.join(os.path.dirname(__file__), "..", "docchat_icon.png"),
    ]
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            app.setWindowIcon(icon)
            break

    app.setStyleSheet("""
        QMainWindow { background: #12121a; }
        QToolTip { background: #1a1a2e; color: #e0e0e0;
            border: 1px solid #444; padding: 4px; }
        QScrollBar:vertical { background: #1a1a2e; width: 8px; }
        QScrollBar::handle:vertical { background: #444; border-radius: 4px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """)

    w = DocChatWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
