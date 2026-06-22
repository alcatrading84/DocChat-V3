"""DocChat Engine v2 — Motor RAG local optimizado.

Mejoras:
- Streaming: respuestas en tiempo real (tokens visibles al instante)
- RAM estable: carga chunks de 1 en 1, no todo en memoria
- HDD estable: escrituras optimizadas, sin picos
- Progreso visible: el usuario sabe qué está pasando
"""

import os
import json
import hashlib
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Callable
import httpx


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
CHAT_MODEL = "qwen2.5-coder-3b-instruct"
CHUNK_SIZE = 300       # Más pequeños = más rápido de procesar
CHUNK_OVERLAP = 30
TOP_K = 3               # Menos fragmentos = respuesta más rápida
DATA_DIR = os.path.expanduser("~/.docchat")


# =============================================================================
# CLIENTE LM STUDIO (con streaming)
# =============================================================================

class LMStudioClient:
    """Cliente HTTP para LM Studio con streaming."""

    def __init__(self, base_url: str = LM_STUDIO_URL):
        self.base_url = base_url
        self._client = httpx.Client(timeout=180)

    def chat_stream(self, messages: List[Dict], model: str = CHAT_MODEL,
                    max_tokens: int = 1024, temperature: float = 0.7,
                    on_token: Callable = None) -> str:
        """Chat con streaming: llama a on_token por cada token recibido."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        full_response = ""
        with self._client.stream("POST", f"{self.base_url}/chat/completions",
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
                        import json as _json
                        data = _json.loads(data_str)
                        token = data["choices"][0].get("delta", {}).get("content", "")
                        if token:
                            full_response += token
                            if on_token:
                                on_token(token)
                    except Exception:
                        continue
        return full_response

    def chat(self, messages: List[Dict], model: str = CHAT_MODEL,
             max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Chat sin streaming (para consultas rápidas)."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        for intento in range(3):
            try:
                resp = self._client.post(f"{self.base_url}/chat/completions",
                                          json=payload, timeout=180)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                if intento < 2:
                    time.sleep(1)
                    continue
                raise TimeoutError("LM Studio no responde. "
                                   "Verifica que el modelo esté cargado.")
            except Exception as e:
                raise RuntimeError(f"Error LM Studio: {e}")

    def embed(self, text: str, model: str = EMBEDDING_MODEL) -> List[float]:
        """Embedding de un texto."""
        for intento in range(3):
            try:
                resp = self._client.post(f"{self.base_url}/embeddings",
                                          json={"model": model, "input": text},
                                          timeout=60)
                resp.raise_for_status()
                return resp.json()["data"][0]["embedding"]
            except httpx.TimeoutException:
                if intento < 2:
                    time.sleep(2)
                    continue
                raise TimeoutError("Embedding timeout. "
                                   "Verifica el modelo de embeddings en LM Studio.")
            except Exception as e:
                raise RuntimeError(f"Error embedding: {e}")

    def health_check(self) -> bool:
        try:
            r = self._client.get(f"{self.base_url}/models", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            r = self._client.get(f"{self.base_url}/models", timeout=5)
            if r.status_code == 200:
                return [m["id"] for m in r.json().get("data", [])]
        except Exception:
            pass
        return []


# =============================================================================
# PROCESADOR DE DOCUMENTOS
# =============================================================================

def load_document(filepath: str) -> str:
    """Cargar texto de PDF, DOCX o TXT."""
    ext = Path(filepath).suffix.lower()

    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    elif ext == ".docx":
        from docx import Document as DocxDoc
        doc = DocxDoc(filepath)
        return "\n".join(p.text for p in doc.paragraphs)

    elif ext == ".pdf":
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

        text = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text()
                if t and t.strip():
                    text.append(t)
            except Exception:
                pass

        result = "\n".join(text)
        if not result.strip():
            raise ValueError(
                "No se pudo extraer texto. "
                "Puede ser un PDF escaneado (imágenes)."
            )
        return result

    else:
        raise ValueError(f"Formato no soportado: {ext}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Dividir texto en chunks pequeños."""
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
# ALMACÉN VECTORIAL OPTIMIZADO
# =============================================================================

class VectorStore:
    """Almacén vectorial con escritura diferida (no picos de HDD)."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(DATA_DIR, "store")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.documents: List[Dict] = []
        self.embeddings: List[np.ndarray] = []
        self._dirty = False
        self._load()

    def _load(self):
        """Cargar desde disco (solo cuando es necesario)."""
        meta_path = self.db_path + "_meta.json"
        vec_path = self.db_path + "_vec.npy"

        if os.path.exists(meta_path) and os.path.exists(vec_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                self.embeddings = list(np.load(vec_path))
                # Si es un solo array 2D, convertir a lista de vectores
                if self.embeddings and isinstance(self.embeddings[0], np.ndarray) and \
                   self.embeddings[0].ndim == 1:
                    pass  # Ya está bien
                elif self.embeddings and isinstance(self.embeddings, np.ndarray):
                    self.embeddings = [np.array(v) for v in self.embeddings]
            except Exception:
                self.documents = []
                self.embeddings = []

    def save(self):
        """Guardar a disco (solo si hay cambios)."""
        if not self._dirty:
            return
        if not self.documents:
            return

        meta_path = self.db_path + "_meta.json"
        vec_path = self.db_path + "_vec.npy"

        # Guardar metadatos como JSON
        with open(meta_path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False)
        os.replace(meta_path + ".tmp", meta_path)

        # Guardar vectores como numpy (mucho más rápido que JSON)
        np.save(vec_path + ".tmp", np.array(self.embeddings))
        os.replace(vec_path + ".tmp", vec_path)

        self._dirty = False

    def add_one(self, text: str, embedding: List[float], source: str = ""):
        """Agregar un solo texto con su embedding (sin pico de RAM)."""
        doc_id = hashlib.md5(text.encode()).hexdigest()[:12]
        self.documents.append({
            "id": doc_id,
            "text": text,
            "source": source,
        })
        self.embeddings.append(np.array(embedding, dtype=np.float32))
        self._dirty = True

    def search(self, query_embedding: List[float], top_k: int = TOP_K) -> List[tuple]:
        """Buscar textos similares (coseno)."""
        if not self.embeddings:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)
        # Normalizar para coseno
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm

        # Calcular similitud en lote (rápido con numpy)
        emb_array = np.array(self.embeddings, dtype=np.float32)
        norms = np.linalg.norm(emb_array, axis=1)
        norms[norms == 0] = 1
        emb_array = emb_array / norms[:, np.newaxis]

        scores = np.dot(emb_array, query_vec)

        indices = np.argsort(scores)[-top_k:][::-1]
        results = []
        for idx in indices:
            doc = self.documents[idx]
            results.append((doc["text"], doc["source"], float(scores[idx])))

        return results

    def clear(self):
        self.documents = []
        self.embeddings = []
        self._dirty = True
        self.save()
        for ext in ["_meta.json", "_vec.npy"]:
            p = self.db_path + ext
            if os.path.exists(p):
                os.remove(p)

    @property
    def count(self) -> int:
        return len(self.documents)

    @property
    def sources(self) -> List[str]:
        return list(set(d["source"] for d in self.documents if d["source"]))


# =============================================================================
# MOTOR RAG OPTIMIZADO
# =============================================================================

class DocChatEngine:
    """Motor principal optimizado para fluidez y RAM estable."""

    def __init__(self):
        self.lm = LMStudioClient()
        self.vector_store = VectorStore()
        self.chat_model = CHAT_MODEL

    def is_available(self) -> bool:
        return self.lm.health_check()

    def available_models(self) -> List[str]:
        models = self.lm.list_models()
        return [m for m in models if "embed" not in m.lower()]

    def add_document(self, filepath: str,
                     on_progress: Callable = None) -> Dict:
        """Cargar documento: UN chunk a la vez (sin picos de RAM)."""
        filename = os.path.basename(filepath)

        # 1. Cargar texto
        text = load_document(filepath)

        # 2. Dividir en chunks pequeños
        chunks = chunk_text(text)
        if not chunks:
            return {"status": "error", "message": "No se pudo extraer texto"}

        if on_progress:
            on_progress(0, len(chunks), "Iniciando...")

        # 3. Procesar UN chunk a la vez
        for i, chunk in enumerate(chunks):
            # Embedding individual (no embota todo)
            emb = self.lm.embed(chunk)

            # Guardar inmediatamente (no acumula en RAM)
            self.vector_store.add_one(chunk, emb, filename)

            # HDD: guardar cada 20 chunks (no cada 1)
            if i % 20 == 0:
                self.vector_store.save()

            if on_progress:
                on_progress(i + 1, len(chunks), f"Chunk {i+1}/{len(chunks)}")

        # Guardar final
        self.vector_store.save()

        return {
            "status": "ok",
            "filename": filename,
            "chunks": len(chunks),
            "total_chars": len(text),
        }

    def query_stream(self, question: str,
                     on_token: Callable = None,
                     use_context: bool = True) -> str:
        """Pregunta con respuesta en streaming (tokens visibles al instante)."""
        if not use_context or self.vector_store.count == 0:
            messages = [{"role": "user", "content": question}]
            return self.lm.chat_stream(messages, model=self.chat_model,
                                       on_token=on_token)

        # 1. Embedding de la pregunta
        q_embedding = self.lm.embed(question)

        # 2. Buscar chunks relevantes
        results = self.vector_store.search(q_embedding, top_k=TOP_K)

        if not results:
            no_result = "No encontré información relevante en los documentos."
            if on_token:
                for c in no_result:
                    on_token(c)
            return no_result

        # 3. Construir contexto (solo TOP_K = más rápido)
        context_parts = []
        sources = set()
        for text, source, score in results:
            context_parts.append(f"[{source}]\n{text.strip()[:500]}")  # Limitar tamaño
            sources.add(source)

        context = "\n\n---\n\n".join(context_parts)
        sources_str = ", ".join(sorted(sources))

        # 4. Prompt optimizado para respuestas rápidas
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
        return self.lm.chat_stream(messages, model=self.chat_model,
                                   on_token=on_token)

    def query(self, question: str, use_context: bool = True) -> str:
        """Pregunta sin streaming."""
        return self.query_stream(question, use_context=use_context)

    def clear(self):
        self.vector_store.clear()

    def get_stats(self) -> Dict:
        return {
            "documents": self.vector_store.count,
            "sources": self.vector_store.sources,
            "model": self.chat_model,
            "available": self.is_available(),
            "lm_models": self.available_models(),
        }
