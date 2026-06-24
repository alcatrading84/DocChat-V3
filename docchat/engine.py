"""DocChat Engine v3 — Motor RAG con modo offline y todas las mejoras.

Novedades v3:
- 🏆 Modo offline: sin LM Studio, modelo local con llama-cpp-python
- 🖼️ OCR para PDFs escaneados
- 📊 Soporte multi-formato (CSV, Excel, PPTX, MD, HTML, código, etc.)
- 🌐 Web UI opcional (Flask)
- 📈 Métricas de uso
- 🔄 Auto-updates desde GitHub
- 🎨 UI mejorada con vista previa y resaltado
"""

import os
import json
import math
import hashlib
import pickle
import time
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

CHUNK_SIZE = 300
CHUNK_OVERLAP = 30
TOP_K = 3
DATA_DIR = os.path.join(os.path.expanduser("~"), ".docchat")
if os.name == "nt":
    DATA_DIR = DATA_DIR.replace("/", "\\")
os.makedirs(DATA_DIR, exist_ok=True)


# =============================================================================
# MODO DE OPERACIÓN
# =============================================================================

class OperationMode:
    """Modo de operación del motor."""
    OFFLINE = "offline"      # Solo modelo local (llama-cpp-python)
    ONLINE = "online"        # Solo LM Studio
    HYBRID = "hybrid"        # LM Studio si disponible, si no local

    @classmethod
    def detect(cls) -> str:
        """Detectar automáticamente el mejor modo."""
        try:
            import httpx
            r = httpx.get("http://127.0.0.1:1234/v1/models", timeout=2)
            if r.status_code == 200:
                return cls.HYBRID
        except Exception:
            pass
        return cls.OFFLINE


# =============================================================================
# CLIENTE DE INFERENCIA (unificado)
# =============================================================================

class InferenceClient:
    """Cliente unificado: LM Studio + modelo local + híbrido."""

    def __init__(self, mode: str = None):
        self.mode = mode or OperationMode.detect()
        self._local = None
        self._lm_client = None
        self._init_providers()

    def _init_providers(self):
        """Inicializar proveedores según el modo."""
        if self.mode in (OperationMode.HYBRID, OperationMode.OFFLINE):
            try:
                from docchat.local_model import LocalModel
                self._local = LocalModel()
                logger.info("✅ Modelo local listo")
            except Exception as e:
                logger.warning(f"⚠️ Modelo local no disponible: {e}")
                self._local = None

        if self.mode in (OperationMode.HYBRID, OperationMode.ONLINE):
            try:
                import httpx
                self._lm_client = httpx.Client(timeout=180)
                logger.info("✅ Cliente LM Studio listo")
            except Exception:
                self._lm_client = None

    @property
    def using_local(self) -> bool:
        if self.mode == OperationMode.OFFLINE:
            return True
        if self.mode == OperationMode.ONLINE:
            return False
        # Híbrido: prefiere LM Studio, fallback a local
        if self._lm_available():
            return False
        return self._local is not None

    def _lm_available(self) -> bool:
        if not self._lm_client:
            return False
        try:
            r = self._lm_client.get(
                "http://127.0.0.1:1234/v1/models", timeout=2
            )
            return r.status_code == 200
        except Exception:
            return False

    def health_check(self) -> bool:
        """Verificar disponibilidad de cualquier proveedor."""
        if self.mode == OperationMode.OFFLINE and self._local:
            return self._local.health_check()
        if self._lm_available():
            return True
        if self.mode == OperationMode.HYBRID and self._local:
            return self._local.health_check()
        return False

    def chat_stream(self, messages: List[Dict],
                    on_token: Callable = None,
                    **kwargs) -> str:
        """Chat con streaming."""
        if not self.using_local and self._lm_available():
            return self._lm_chat_stream(messages, on_token, **kwargs)

        if self._local:
            # Formatear mensajes para modo local
            return self._local.chat_stream(messages, on_token=on_token, **kwargs)

        raise RuntimeError(
            "No hay proveedor de inferencia disponible.\n"
            "1️⃣ Instala: pip install llama-cpp-python\n"
            "2️⃣ O abre LM Studio con un modelo cargado"
        )

    def _lm_chat_stream(self, messages, on_token, **kwargs):
        """Chat via LM Studio con streaming."""
        import httpx
        payload = {
            "model": kwargs.get("model", "qwen2.5-coder-3b-instruct"),
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True,
        }
        full = ""
        with httpx.Client().stream("POST",
              "http://127.0.0.1:1234/v1/chat/completions",
              json=payload, timeout=180) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or line.startswith(": "):
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        token = data["choices"][0].get("delta", {}).get("content", "")
                        if token:
                            full += token
                            if on_token:
                                on_token(token)
                    except Exception:
                        continue
        return full

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """Chat sin streaming."""
        return self.chat_stream(messages, **kwargs)

    def embed(self, text: str) -> List[float]:
        """Embedding."""
        if not self.using_local and self._lm_available():
            return self._lm_embed(text)

        if self._local:
            return self._local.embed(text)

        # Fallback: embedding simulado
        return self._fallback_embedding(text)

    def _lm_embed(self, text: str) -> List[float]:
        try:
            import httpx
            resp = httpx.post(
                "http://127.0.0.1:1234/v1/embeddings",
                json={
                    "model": "text-embedding-nomic-embed-text-v1.5",
                    "input": text,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
        except Exception:
            return self._local.embed(text) if self._local else self._fallback_embedding(text)

    def _fallback_embedding(self, text: str, dim: int = 768) -> List[float]:
        h = hashlib.sha256(text.encode()).digest()
        return [(h[i % len(h)] / 255.0) * 2 - 1 for i in range(dim)]

    def list_models(self) -> List[str]:
        """Listar modelos disponibles."""
        models = []
        if self._lm_available():
            try:
                r = httpx.get("http://127.0.0.1:1234/v1/models", timeout=5)
                if r.status_code == 200:
                    models.extend(
                        m["id"] for m in r.json().get("data", [])
                    )
            except Exception:
                pass
        if self._local and self._local.is_loaded:
            models.append("🧠 Local: " + os.path.basename(self._local.model_path))
        return models

    def get_info(self) -> Dict:
        """Info del proveedor activo."""
        info = {
            "mode": self.mode,
            "using_local": self.using_local,
            "available": self.health_check(),
        }
        if self._local and self._local.is_loaded:
            info["local_model"] = self._local.get_info()
        return info


# =============================================================================
# PROCESADOR DE DOCUMENTOS (con OCR y multi-formato)
# =============================================================================

def load_document(filepath: str, use_ocr_fallback: bool = True) -> str:
    """
    Cargar cualquier documento soportado.

    Args:
        filepath: Ruta al archivo
        use_ocr_fallback: Si True, intenta OCR si la extracción normal falla

    Returns:
        Texto extraído
    """
    ext = Path(filepath).suffix.lower()

    # Formatos básicos (engine original)
    if ext in (".txt", ".md", ".py", ".js", ".ts", ".java", ".cpp", ".c",
               ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt",
               ".sql", ".sh", ".bat", ".ps1", ".r"):
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    # JSON, XML, YAML, HTML, CSV, Excel, PPTX
    if ext in (".json", ".xml", ".yaml", ".yml", ".html", ".htm",
               ".csv", ".xlsx", ".xls", ".pptx"):
        from docchat.formats import load_any_document
        return load_any_document(filepath)

    # DOCX
    if ext == ".docx":
        from docx import Document as DocxDoc
        doc = DocxDoc(filepath)
        return "\n".join(p.text for p in doc.paragraphs)

    # PDF (con OCR fallback)
    if ext == ".pdf":
        return _load_pdf(filepath, use_ocr_fallback)

    raise ValueError(f"Formato no soportado: {ext}")


def _load_pdf(filepath: str, use_ocr: bool = True) -> str:
    """Cargar PDF con OCR como fallback."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(filepath)
    except Exception as e:
        raise ValueError(f"No se pudo abrir el PDF: {e}")

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError(
                "PDF protegido con contraseña. "
                "Guarda una copia sin protección e intenta de nuevo."
            )

    # Extraer texto normal
    text = []
    for page in reader.pages:
        try:
            t = page.extract_text()
            if t and t.strip():
                text.append(t)
        except Exception:
            pass

    result = "\n".join(text)

    # Verificar si necesita OCR
    if use_ocr and _needs_ocr(result):
        logger.info("📄 PDF parece escaneado. Intentando OCR...")
        try:
            from docchat.ocr import ocr_full_pdf
            ocr_text = ocr_full_pdf(filepath)
            if ocr_text and len(ocr_text) > len(result):
                logger.info(f"✅ OCR extrajo {len(ocr_text)} caracteres")
                return ocr_text
        except Exception as e:
            logger.warning(f"⚠️ OCR falló: {e}")
            if not result.strip():
                raise ValueError(
                    "No se pudo extraer texto. "
                    "Puede ser un PDF escaneado. "
                    "Instala Tesseract OCR para leerlo."
                )

    if not result.strip():
        raise ValueError(
            "No se pudo extraer texto del PDF. "
            "¿Es un PDF escaneado? "
            "Instala Tesseract OCR y vuelve a intentar."
        )

    return result


def _needs_ocr(text: str) -> bool:
    """Determinar si un texto necesita OCR."""
    if not text or len(text.strip()) < 50:
        return True
    words = text.strip().split()
    real_words = sum(1 for w in words if any(c.isalpha() for c in w))
    if len(words) == 0:
        return True
    return (real_words / len(words)) < 0.3


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Dividir texto en chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
        if i >= len(words):
            break
    return chunks


# =============================================================================
# ALMACÉN VECTORIAL
# =============================================================================

class VectorStore:
    """Almacén vectorial simple (Python puro)."""

    def __init__(self, db_path: str = None):
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = os.path.join(DATA_DIR, "docchat_data")
        os.makedirs(DATA_DIR, exist_ok=True)

        self.documents: List[Dict] = []
        self.embeddings: List[List[float]] = []
        self._load()

    def _path(self):
        return self.db_path + ".pkl"

    def _load(self):
        path = self._path()
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                self.documents = data.get("docs", [])
                self.embeddings = data.get("vecs", [])
            except Exception:
                self.documents = []
                self.embeddings = []

    def save(self):
        if not self.documents or not self.embeddings:
            return
        path = self._path()
        tmp = path + ".tmp"
        try:
            with open(tmp, "wb") as f:
                pickle.dump({"docs": self.documents, "vecs": self.embeddings}, f)
            shutil.move(tmp, path)
        except Exception as e:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
            logger.warning(f"Error al guardar: {e}")

    def add_one(self, text: str, embedding: List[float], source: str = ""):
        doc_id = hashlib.md5(text.encode()).hexdigest()[:12]
        self.documents.append({"id": doc_id, "text": text, "source": source})
        self.embeddings.append(embedding)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query_embedding: List[float],
               top_k: int = TOP_K) -> List[tuple]:
        if not self.embeddings:
            return []
        scored = []
        for i, emb in enumerate(self.embeddings):
            sim = self._cosine_similarity(query_embedding, emb)
            scored.append((sim, i))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, idx in scored[:top_k]:
            doc = self.documents[idx]
            results.append((doc["text"], doc["source"], sim))
        return results

    def clear(self):
        self.documents = []
        self.embeddings = []
        path = self._path()
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        tmp = path + ".tmp"
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

    @property
    def count(self) -> int:
        return len(self.documents)

    @property
    def sources(self) -> List[str]:
        return list(set(d["source"] for d in self.documents if d["source"]))


# =============================================================================
# MOTOR RAG v3
# =============================================================================

class DocChatEngine:
    """Motor principal v3 con todas las mejoras."""

    def __init__(self, mode: str = None):
        # Elegir modo automáticamente
        self.mode = mode or OperationMode.detect()
        logger.info(f"🚀 DocChat Engine v3 iniciado (modo: {self.mode})")

        # Proveedor de inferencia
        self.inference = InferenceClient(self.mode)

        # Almacén vectorial
        self.vector_store = VectorStore()

        # Métricas
        try:
            from docchat.metrics import MetricsCollector
            self.metrics = MetricsCollector()
        except Exception:
            self.metrics = None

        # Estado
        self.chat_model = "auto"

    def is_available(self) -> bool:
        return self.inference.health_check()

    def available_models(self) -> List[str]:
        return self.inference.list_models()

    def get_mode_info(self) -> Dict:
        return self.inference.get_info()

    def add_document(self, filepath: str,
                     on_progress: Callable = None) -> Dict:
        """Cargar documento con soporte multi-formato y OCR."""
        filename = os.path.basename(filepath)
        start_time = time.time()

        # 1. Cargar texto (con OCR si es necesario)
        try:
            text = load_document(filepath, use_ocr_fallback=True)
        except Exception as e:
            if self.metrics:
                from docchat.metrics import ErrorEvent
                self.metrics.log_error(ErrorEvent(
                    error_type="load_error",
                    message=str(e),
                    context=f"file={filename}",
                ))
            return {"status": "error", "message": str(e)}

        # 2. Dividir en chunks
        chunks = chunk_text(text)
        if not chunks:
            return {"status": "error", "message": "No se pudo extraer texto"}

        if on_progress:
            on_progress(0, len(chunks), "Iniciando...")

        # 3. Procesar chunks (1 a 1 para RAM estable)
        for i, chunk in enumerate(chunks):
            emb = self.inference.embed(chunk)
            self.vector_store.add_one(chunk, emb, filename)

            if i % 20 == 0:
                self.vector_store.save()

            if on_progress:
                on_progress(i + 1, len(chunks), f"Chunk {i+1}/{len(chunks)}")

        self.vector_store.save()
        duration = (time.time() - start_time) * 1000

        # Registrar métricas
        if self.metrics:
            from docchat.metrics import DocEvent
            self.metrics.log_doc(DocEvent(
                filename=filename,
                format=Path(filepath).suffix.lower(),
                chars=len(text),
                chunks=len(chunks),
                duration_ms=duration,
            ))

        return {
            "status": "ok",
            "filename": filename,
            "chunks": len(chunks),
            "total_chars": len(text),
            "duration_ms": duration,
        }

    def query_stream(self, question: str,
                     on_token: Callable = None,
                     use_context: bool = True) -> str:
        """Pregunta con respuesta en streaming."""
        start_time = time.time()

        if not use_context or self.vector_store.count == 0:
            messages = [{"role": "user", "content": question}]
            response = self.inference.chat_stream(
                messages, on_token=on_token
            )
        else:
            # 1. Embedding de la pregunta
            q_embedding = self.inference.embed(question)

            # 2. Buscar chunks relevantes
            results = self.vector_store.search(q_embedding, top_k=TOP_K)

            if not results:
                no_result = "No encontré información relevante en los documentos."
                if on_token:
                    for c in no_result:
                        on_token(c)
                response = no_result
            else:
                # 3. Construir contexto
                context_parts = []
                sources = set()
                for text, source, score in results:
                    context_parts.append(f"[{source}]\n{text.strip()[:500]}")
                    sources.add(source)

                context = "\n\n---\n\n".join(context_parts)
                sources_str = ", ".join(sorted(sources))

                # 4. Prompt
                system_prompt = (
                    "Responde la pregunta basándote en el contexto. "
                    "Si no encuentras la respuesta, di que no está en los documentos. "
                    "Sé conciso. Cita las fuentes."
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": (
                        f"Contexto:\n{context}\n\n"
                        f"Pregunta: {question}\n"
                        f"Fuentes: {sources_str}"
                    )},
                ]

                # 5. Streaming
                response = self.inference.chat_stream(
                    messages, on_token=on_token
                )

        duration = (time.time() - start_time) * 1000

        # Registrar métricas
        if self.metrics:
            from docchat.metrics import QueryEvent
            self.metrics.log_query(QueryEvent(
                question_length=len(question),
                had_context=use_context and self.vector_store.count > 0,
                response_length=len(response),
                duration_ms=duration,
            ))

        return response

    def query(self, question: str, use_context: bool = True) -> str:
        """Pregunta sin streaming."""
        return self.query_stream(question, use_context=use_context)

    def clear(self):
        self.vector_store.clear()

    def summarize(self, on_token: Callable = None) -> str:
        """Resumir todos los documentos cargados."""
        if self.vector_store.count == 0:
            msg = "No hay documentos cargados para resumir."
            if on_token:
                for c in msg:
                    on_token(c)
            return msg

        sources = ", ".join(self.vector_store.sources)
        prompt = (
            f"Resume el contenido de estos documentos de forma clara y organizada.\n\n"
            f"Documentos: {sources}\n\n"
            f"Contexto:\n"
        )
        # Tomar primeros 10 chunks como muestra
        texts = [d["text"][:300] for d in self.vector_store.documents[:10]]
        prompt += "\n\n---\n\n".join(texts)

        messages = [
            {"role": "system", "content": "Eres un asistente que resume documentos. Sé conciso y organizado."},
            {"role": "user", "content": prompt},
        ]
        return self.inference.chat_stream(messages, on_token=on_token)

    def translate(self, text: str, target: str = "en",
                  on_token: Callable = None) -> str:
        """Traducir texto al idioma indicado."""
        lang_name = {"en": "English", "es": "Spanish"}.get(target, target)
        messages = [
            {"role": "system", "content": f"Traduce el texto a {lang_name}. Solo responde con la traducción."},
            {"role": "user", "content": text},
        ]
        return self.inference.chat_stream(messages, on_token=on_token)

    def export_chat(self, chat_html: str, filepath: str):
        """Exportar chat a TXT."""
        import re
        # Limpiar HTML
        text = re.sub(r'<[^>]+>', '', chat_html)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("📄 DocChat - Exportación de conversación\n")
            f.write("=" * 50 + "\n\n")
            f.write(text)
        return filepath

    def get_stats(self) -> Dict:
        stats = {
            "documents": self.vector_store.count,
            "sources": self.vector_store.sources,
            "model": self.chat_model,
            "available": self.is_available(),
            "lm_models": self.available_models(),
            "mode": self.mode,
            "using_local": self.inference.using_local,
        }
        # Agregar métricas
        if self.metrics:
            stats["metrics"] = self.metrics.get_summary()
        return stats

    def print_report(self):
        """Imprimir reporte completo."""
        if self.metrics:
            self.metrics.print_report()
        info = self.inference.get_info()
        print(f"\n🔧 Modo: {info['mode']}")
        print(f"   Local: {'✅' if info['using_local'] else '❌'}")
        print(f"   Disponible: {'✅' if info['available'] else '❌'}")
        if 'local_model' in info:
            lm = info['local_model']
            print(f"   Modelo: {lm.get('model', 'N/A')}")
            print(f"   Tamaño: {lm.get('size_gb', 'N/A')} GB")
        print(f"\n📄 Documentos: {self.vector_store.count}")
        print(f"📁 Fuentes: {', '.join(self.vector_store.sources) or 'Ninguna'}")
