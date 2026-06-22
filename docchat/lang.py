"""Traducciones para DocChat — Español / English."""

LANG = {
    "es": {
        "app_name": "📄 DocChat — Chat con tus documentos",
        "app_subtitle": "📄 DocChat — Asistente Local de Documentos",
        "docs_title": "📁 Documentos",
        "drop_hint": "🎯 SOLTAR AQUÍ",
        "drop_desc": "Arrastra PDF, DOCX o TXT:",
        "drag_hint_1": "Arrastra PDF, Word o TXT",
        "drag_hint_2": "al panel izquierdo",
        "loaded": "Cargados:",
        "clear_all": "🗑 Limpiar todo",
        "clear_confirm": "¿Eliminar todos los documentos?",
        "clear_done": "🗑 Documentos eliminados",
        "model": "🧠 Modelo:",
        "rag_on": "📄 RAG ON",
        "chat_mode": "💬 CHAT",
        "prompt_rag": "Pregunta sobre los documentos...",
        "prompt_chat": "Chatea con la IA local...",
        "typing": "🤖 Escribiendo...",
        "send": "▶",
        "connected": "🟢 LM Studio",
        "disconnected": "🔴 LM Studio NO disponible",
        "connecting": "🟡 Conectando...",
        "docs_count": "📄 {}",
        "frags": "frags",
        "chars": "caracteres",
        "loading": "⏳ Procesando {}",
        "progress": "Chunk {}/{}",
        "loaded_ok": "✅ **{}** cargado.\n{} fragmentos · {} caracteres",
        "no_context": "No encontré información relevante en los documentos.",
        "error_pdf_encrypted": "PDF protegido. Guárdalo sin contraseña e intenta de nuevo.",
        "error_pdf_scan": "No se pudo extraer texto. Puede ser un PDF escaneado.",
        "error_timeout": "LM Studio tardó. Verifica que el modelo esté cargado y prueba de nuevo.",
        "error_unknown": "Error desconocido",
        "error_display": "Error al mostrar resultado: {}",
        "welcome": (
            "📄 **DocChat** — Asistente Local de Documentos\n\n"
            "1️⃣ Arrastra un PDF, Word o TXT al panel izquierdo\n"
            "2️⃣ Escribe preguntas sobre su contenido\n"
            "3️⃣ Las respuestas aparecen **en tiempo real**\n\n"
            "✅ 100% local · Sin API keys · Sin internet"
        ),
        "user_prefix": "🧑 Tú",
        "ai_prefix": "🤖 DocChat",
        "system": "",
        "error_prefix": "❌",
        "status_ok": "✅ Listo",
        "status_error": "❌ Error",
        "models_updated": "🔄 {} modelos",
        "lang_es": "Español",
        "lang_en": "English",
    },
    "en": {
        "app_name": "📄 DocChat — Chat with your documents",
        "app_subtitle": "📄 DocChat — Local Document Assistant",
        "docs_title": "📁 Documents",
        "drop_hint": "🎯 DROP HERE",
        "drop_desc": "Drop PDF, DOCX or TXT:",
        "drag_hint_1": "Drop PDF, Word or TXT",
        "drag_hint_2": "on the left panel",
        "loaded": "Loaded:",
        "clear_all": "🗑 Clear all",
        "clear_confirm": "Delete all documents?",
        "clear_done": "🗑 Documents deleted",
        "model": "🧠 Model:",
        "rag_on": "📄 RAG ON",
        "chat_mode": "💬 CHAT",
        "prompt_rag": "Ask about your documents...",
        "prompt_chat": "Chat with local AI...",
        "typing": "🤖 Thinking...",
        "send": "▶",
        "connected": "🟢 LM Studio",
        "disconnected": "🔴 LM Studio unavailable",
        "connecting": "🟡 Connecting...",
        "docs_count": "📄 {}",
        "frags": "frags",
        "chars": "characters",
        "loading": "⏳ Processing {}",
        "progress": "Chunk {}/{}",
        "loaded_ok": "✅ **{}** loaded.\n{} fragments · {} characters",
        "no_context": "No relevant information found in the documents.",
        "error_pdf_encrypted": "PDF is password protected. Save a copy without password and try again.",
        "error_pdf_scan": "Could not extract text. It might be a scanned PDF (images).",
        "error_timeout": "LM Studio timed out. Make sure the model is loaded and try again.",
        "error_unknown": "Unknown error",
        "error_display": "Error showing result: {}",
        "welcome": (
            "📄 **DocChat** — Local Document Assistant\n\n"
            "1️⃣ Drop a PDF, Word or TXT on the left panel\n"
            "2️⃣ Ask questions about the content\n"
            "3️⃣ Responses appear **in real time**\n\n"
            "✅ 100% local · No API keys · No internet required"
        ),
        "user_prefix": "🧑 You",
        "ai_prefix": "🤖 DocChat",
        "system": "",
        "error_prefix": "❌",
        "status_ok": "✅ Done",
        "status_error": "❌ Error",
        "models_updated": "🔄 {} models",
        "lang_es": "Spanish",
        "lang_en": "English",
    },
}


def t(key: str, lang: str = "es") -> str:
    """Traducir una clave al idioma seleccionado."""
    return LANG.get(lang, LANG["es"]).get(key, key)
