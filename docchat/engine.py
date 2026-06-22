"""DocChat Engine — Motor RAG local usando LM Studio.

Sin API keys. Sin internet. Solo tu LM Studio local.
"""

import os
import json
import math
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import httpx


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
CHAT_MODEL = "qwen2.5-coder-3b-instruct"  # Cambiable en settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5
DATA_DIR = os.path.expanduser("~/.docchat")


# =============================================================================
# CLIENTE LM STUDIO
# =============================================================================

class LMStudioClient:
    """Cliente HTTP para LM Studio."""

    def __init__(self, base_url: str = LM_STUDIO_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=120)  # 2 min para modelos grandes

    def _post(self, endpoint: str, payload: dict, max_retries: int = 2) -> dict:
        """POST con reintentos y timeout más largo."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                resp = self.client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    timeout=180,  # 3 min por si el modelo tarda
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException as e:
                last_error = f"Timeout ({attempt+1}/{max_retries+1}): el modelo está procesando"
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"LM Studio error {e.response.status_code}: {e.response.text[:200]}")
            except Exception as e:
                last_error = str(e)
        raise TimeoutError(f"LM Studio no responde después de {max_retries+1} intentos. "
                          f"Verifica que el modelo esté cargado en LM Studio. Error: {last_error}")

    def chat(self, messages: List[Dict], model: str = CHAT_MODEL,
             max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Enviar mensaje y obtener respuesta."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        data = self._post("/chat/completions", payload)
        return data["choices"][0]["message"]["content"]

    def embed(self, text: str, model: str = EMBEDDING_MODEL) -> List[float]:
        """Obtener embedding de un texto."""
        payload = {"model": model, "input": text}
        data = self._post("/embeddings", payload)
        return data["data"][0]["embedding"]

    def embed_batch(self, texts: List[str], model: str = EMBEDDING_MODEL) -> List[List[float]]:
        """Obtener embeddings de múltiples textos."""
        payload = {"model": model, "input": texts}
        data = self._post("/embeddings", payload)
        return [d["embedding"] for d in sorted(data["data"], key=lambda x: x["index"])]

    def health_check(self) -> bool:
        """Verificar que LM Studio está corriendo."""
        try:
            resp = self.client.get(f"{self.base_url}/models", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Listar modelos disponibles."""
        try:
            resp = self.client.get(f"{self.base_url}/models", timeout=5)
            if resp.status_code == 200:
                return [m["id"] for m in resp.json().get("data", [])]
        except Exception:
            pass
        return []


# =============================================================================
# PROCESADOR DE DOCUMENTOS
# =============================================================================

def load_document(filepath: str) -> str:
    """Cargar texto de un documento (PDF, DOCX, TXT)."""
    ext = Path(filepath).suffix.lower()

    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    elif ext == ".docx":
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs)

    elif ext == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(filepath)
        except Exception as e:
            raise ValueError(f"No se pudo abrir el PDF: {e}")

        # Intentar desencriptar si está protegido
        if reader.is_encrypted:
            try:
                reader.decrypt("")  # Intentar sin contraseña
            except Exception:
                raise ValueError(
                    "El PDF está encriptado y no se puede leer. "
                    "Prueba con un PDF sin protección."
                )

        text = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text()
                if t and t.strip():
                    text.append(t)
            except Exception:
                text.append(f"[Página {i+1}: no se pudo extraer texto]")

        result = "\n".join(text)
        if not result.strip():
            raise ValueError(
                "No se pudo extraer texto del PDF. "
                "Puede ser un PDF escaneado (imágenes). "
                "Prueba con un PDF con texto seleccionable."
            )
        return result

    else:
        raise ValueError(f"Formato no soportado: {ext}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Dividir texto en chunks superpuestos."""
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
# ALMACÉN VECTORIAL (simple, sin dependencias pesadas)
# =============================================================================

class VectorStore:
    """Almacén vectorial simple basado en JSON + numpy."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(DATA_DIR, "vectors.json")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.documents: List[Dict] = []
        self.embeddings: List[np.ndarray] = []
        self._load()

    def _load(self):
        """Cargar datos desde disco."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.documents = data.get("documents", [])
                self.embeddings = [np.array(e) for e in data.get("embeddings", [])]
            except Exception:
                self.documents = []
                self.embeddings = []

    def _save(self):
        """Guardar datos a disco."""
        data = {
            "documents": self.documents,
            "embeddings": [e.tolist() for e in self.embeddings],
        }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, texts: List[str], embeddings: List[List[float]],
            metadata: Optional[List[Dict]] = None):
        """Agregar textos con sus embeddings."""
        for i, (text, emb) in enumerate(zip(texts, embeddings)):
            doc_id = hashlib.md5(text.encode()).hexdigest()[:12]
            self.documents.append({
                "id": doc_id,
                "text": text,
                "source": metadata[i].get("source", "") if metadata else "",
                "page": metadata[i].get("page", 0) if metadata else 0,
            })
            self.embeddings.append(np.array(emb))
        self._save()

    def search(self, query_embedding: List[float], top_k: int = TOP_K) -> List[Tuple[str, str, float]]:
        """Buscar los textos más similares a un embedding."""
        if not self.embeddings:
            return []

        query_vec = np.array(query_embedding)

        # Coseno similitud
        scores = []
        for emb in self.embeddings:
            dot = np.dot(query_vec, emb)
            norm = np.linalg.norm(query_vec) * np.linalg.norm(emb)
            sim = dot / norm if norm > 0 else 0
            scores.append(sim)

        # Top-K
        indices = np.argsort(scores)[-top_k:][::-1]
        results = []
        for idx in indices:
            doc = self.documents[idx]
            results.append((doc["text"], doc["source"], float(scores[idx])))

        return results

    def clear(self):
        """Limpiar todos los datos."""
        self.documents = []
        self.embeddings = []
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    @property
    def count(self) -> int:
        return len(self.documents)

    @property
    def sources(self) -> List[str]:
        return list(set(d["source"] for d in self.documents if d["source"]))


# =============================================================================
# MOTOR RAG
# =============================================================================

class DocChatEngine:
    """Motor principal de DocChat."""

    def __init__(self):
        self.lm = LMStudioClient()
        self.vector_store = VectorStore()
        self.chat_model = CHAT_MODEL
        self._history: List[Dict] = []

    def is_available(self) -> bool:
        """Verificar que LM Studio está disponible."""
        return self.lm.health_check()

    def available_models(self) -> List[str]:
        """Listar modelos de chat disponibles."""
        models = self.lm.list_models()
        # Filtrar modelos de embedding
        return [m for m in models if "embed" not in m.lower()]

    def add_document(self, filepath: str) -> Dict:
        """Procesar y agregar un documento al índice."""
        filename = os.path.basename(filepath)

        # 1. Cargar texto
        text = load_document(filepath)

        # 2. Dividir en chunks
        chunks = chunk_text(text)
        if not chunks:
            return {"status": "error", "message": "No se pudo extraer texto"}

        # 3. Generar embeddings
        embeddings = self.lm.embed_batch(chunks)

        # 4. Guardar
        metadata = [{"source": filename} for _ in chunks]
        self.vector_store.add(chunks, embeddings, metadata)

        return {
            "status": "ok",
            "filename": filename,
            "chunks": len(chunks),
            "total_chars": len(text),
        }

    def query(self, question: str, use_context: bool = True) -> str:
        """Hacer una pregunta sobre los documentos cargados.

        Args:
            question: Pregunta del usuario
            use_context: Si True, busca en documentos. Si False, chat directo.

        Returns:
            Respuesta del modelo
        """
        if not use_context or self.vector_store.count == 0:
            # Chat directo sin contexto
            messages = [{"role": "user", "content": question}]
            return self.lm.chat(messages, model=self.chat_model)

        # 1. Generar embedding de la pregunta
        q_embedding = self.lm.embed(question)

        # 2. Buscar chunks relevantes
        results = self.vector_store.search(q_embedding, top_k=TOP_K)

        if not results:
            return "No encontré información relevante en los documentos."

        # 3. Construir contexto
        context_parts = []
        sources = set()
        for text, source, score in results:
            context_parts.append(f"[{source}]\n{text}")
            sources.add(source)

        context = "\n\n---\n\n".join(context_parts)
        sources_str = ", ".join(sorted(sources))

        # 4. Construir prompt con contexto
        system_prompt = (
            "Eres un asistente que responde preguntas basándote EXCLUSIVAMENTE "
            "en el contexto proporcionado. Si no encuentras la respuesta en el "
            "contexto, di 'No encontré esta información en los documentos.' "
            "Sé conciso y preciso. Cita las fuentes cuando sea posible."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"Contexto:\n{context}\n\n"
                f"Pregunta: {question}\n\n"
                f"Fuentes disponibles: {sources_str}"
            )},
        ]

        # 5. Obtener respuesta
        return self.lm.chat(messages, model=self.chat_model)

    def clear(self):
        """Limpiar documentos y memoria."""
        self.vector_store.clear()
        self._history = []

    def get_stats(self) -> Dict:
        """Obtener estadísticas del motor."""
        return {
            "documents": self.vector_store.count,
            "sources": self.vector_store.sources,
            "model": self.chat_model,
            "available": self.is_available(),
            "lm_models": self.available_models(),
        }
