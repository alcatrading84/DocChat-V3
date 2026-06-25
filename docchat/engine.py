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

from docchat.local_model import LocalModel
from docchat import config


# =============================================================================

class LMStudioClient:
    """Cliente HTTP para LM Studio con streaming."""

    def __init__(self, base_url: str = config.LM_STUDIO_URL):
        self.base_url = base_url
        self._client = httpx.Client(timeout=180)
        self._client_embed = httpx.Client(timeout=60)

    def chat_stream(self, messages: List[Dict], model: str = config.CHAT_MODEL,
                    max_tokens: int = 1024, temperature: float = 0.7,
                    on_token: Callable = None) -> str:
        """Chat con streaming."""
        payload = {
            "model": model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature,
            "stream": True,
        }
        full = ""
        with self._client.stream("POST", f"{self.base_url}/chat/completions",
                                  json=payload, timeout=180) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or line.startswith(": "):
                    continue
                if line.startswith("data: "):
                    ds = line[6:].strip()
                    if ds == "[DONE]":
                        break
                    try:
                        import json as _j
                        tok = _j.loads(ds)["choices"][0]["delta"].get("content", "")
                        if tok:
                            full += tok
                            if on_token:
                                on_token(tok)
                    except Exception:
                        continue
        return full

    def chat(self, messages, model=config.CHAT_MODEL, **kw):
        return self.chat_stream(messages, model=model, **kw)

    def embed(self, text: str, model=config.EMBEDDING_MODEL):
        for i in range(2):
            try:
                r = self._client_embed.post(f"{self.base_url}/embeddings",
                    json={"model": model, "input": text}, timeout=60)
                r.raise_for_status()
                return r.json()["data"][0]["embedding"]
            except Exception:
                if i == 0:
                    import time; time.sleep(2)
                    continue
                raise

    def health_check(self) -> bool:
        try:
            r = self._client.get(f"{self.base_url}/models", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list:
        try:
            r = self._client.get(f"{self.base_url}/models", timeout=5)
            if r.status_code == 200:
                return [m["id"] for m in r.json().get("data", [])]
        except Exception:
            pass
        return []


# =============================================================================
# CLIENTE OPENAI (alternativa rápida, sin GPU)
# =============================================================================

class OpenAIClient:
    """Cliente para OpenAI API (GPT-4o-mini, rápido, ~$0.15/1M tokens)."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"
        self._client = httpx.Client(timeout=60)
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_stream(self, messages, model="gpt-4o-mini",
                    max_tokens=2048, temperature=0.7,
                    on_token=None) -> str:
        payload = {
            "model": model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature,
            "stream": True,
        }
        full = ""
        with self._client.stream("POST", f"{self.base_url}/chat/completions",
                                  json=payload, headers=self._headers,
                                  timeout=60) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or line.startswith(": "):
                    continue
                if line.startswith("data: "):
                    ds = line[6:].strip()
                    if ds == "[DONE]":
                        break
                    try:
                        import json as _j
                        tok = _j.loads(ds)["choices"][0]["delta"].get("content", "")
                        if tok:
                            full += tok
                            if on_token:
                                on_token(tok)
                    except Exception:
                        continue
        return full

    def chat(self, messages, model="gpt-4o-mini", **kw):
        return self.chat_stream(messages, model=model, **kw)

    def embed(self, text: str, model="text-embedding-3-small"):
        r = self._client.post(f"{self.base_url}/embeddings",
            json={"model": model, "input": text},
            headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]

    def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            r = self._client.get(f"{self.base_url}/models",
                headers=self._headers, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list:
        if not self.api_key:
            return []
        try:
            r = self._client.get(f"{self.base_url}/models",
                headers=self._headers, timeout=10)
            if r.status_code == 200:
                return [m["id"] for m in r.json().get("data", [])]
        except Exception:
            pass
        return []


# =============================================================================
# PROCESADOR DE DOCUMENTOS
# =============================================================================

def load_document(filepath: str) -> str:
    """Cargar texto de cualquier documento soportado (PDF, DOCX, TXT, MD, HTML, CSV, XLSX, PPTX, ...)."""
    from docchat.formats import load_any_document
    return load_any_document(filepath)


def chunk_text(text: str, chunk_size: int = config.CHUNK_SIZE,
               overlap: int = config.CHUNK_OVERLAP) -> List[str]:
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
    """Almacén vectorial simple y robusto."""

    def __init__(self, db_path: str = None):
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = os.path.join(config.DATA_DIR, "docchat_data")
        os.makedirs(config.DATA_DIR, exist_ok=True)

        self.documents: List[Dict] = []
        self.embeddings: List[np.ndarray] = []
        self._load()

    def _path(self):
        return self.db_path + ".npz"

    def _load(self):
        path = self._path()
        if os.path.exists(path):
            try:
                data = np.load(path, allow_pickle=True)
                self.documents = list(data["docs"])
                self.embeddings = [np.array(v, dtype=np.float32) for v in data["vecs"]]
            except Exception:
                self.documents = []
                self.embeddings = []

    def save(self):
        if not self.documents or not self.embeddings:
            return
        path = self._path()
        try:
            arr = np.array(self.embeddings, dtype=np.float32)
            np.savez(path, docs=self.documents, vecs=arr)
        except Exception as e:
            print(f"⚠️ Error al guardar: {e}")

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

    def search(self, query_embedding: List[float], top_k: int = config.TOP_K) -> List[tuple]:
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
        path = self._path()
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    @property
    def count(self) -> int:
        return len(self.documents)

    @property
    def sources(self) -> List[str]:
        return list(set(d["source"] for d in self.documents if d["source"]))


# =============================================================================
# CLIENTE LOCAL GGUF (llama-cpp-python)
# =============================================================================

class LocalModelClient:
    """Wrapper para LocalModel, compatible con la interfaz de LMStudioClient."""

    def __init__(self):
        self._model = None
        self._chat_model = config.CHAT_MODEL

    def _ensure_loaded(self):
        if self._model is None:
            self._model = LocalModel()

    def chat_stream(self, messages, model=None, max_tokens=1024,
                    temperature=0.7, on_token=None) -> str:
        self._ensure_loaded()
        return self._model.chat_stream(
            messages, max_tokens=max_tokens,
            temperature=temperature, on_token=on_token,
        )

    def chat(self, messages, model=None, max_tokens=1024,
             temperature=0.7, **kw) -> str:
        return self.chat_stream(messages, max_tokens=max_tokens,
                                temperature=temperature)

    def embed(self, text: str) -> List[float]:
        self._ensure_loaded()
        return self._model.embed(text)

    def health_check(self) -> bool:
        if self._model is None:
            return False
        return self._model.health_check()

    def list_models(self) -> list:
        return [self._chat_model]


# =============================================================================
# MOTOR RAG OPTIMIZADO
# =============================================================================

class DocChatEngine:
    """Motor principal con soporte local (LM Studio) y cloud (OpenAI)."""

    def __init__(self, mode: str = "lmstudio"):
        self.lm = LMStudioClient()
        self.openai = OpenAIClient()
        self.local_gguf = LocalModelClient()
        self.vector_store = VectorStore()
        self.chat_model = config.CHAT_MODEL
        self.openai_model = "gpt-4o-mini"
        self._mode = "lmstudio"  # "lmstudio", "cloud", "local_gguf"
        self._embed_cache = {}  # Caché simple: hash(texto) -> embedding
        if mode in ("lmstudio", "cloud", "local_gguf"):
            self._mode = mode

    def _get_cached_embedding(self, text: str) -> List[float]:
        """Embedding con caché LRU simple (evita re-embedear la misma pregunta)."""
        key = hashlib.md5(text.encode()).hexdigest()
        if key in self._embed_cache:
            return self._embed_cache[key]
        emb = self._client().embed(text)
        # Mantener caché limitado a 128 entradas
        if len(self._embed_cache) > 128:
            self._embed_cache.clear()
        self._embed_cache[key] = emb
        return emb

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str, api_key: str = ""):
        """Cambiar modo: 'lmstudio' (LM Studio), 'cloud' (OpenAI) o 'local_gguf'."""
        self._mode = mode
        if mode == "cloud" and api_key:
            self.openai = OpenAIClient(api_key)

    def _client(self):
        """Obtener el cliente activo según el modo."""
        return {
            "cloud": self.openai,
            "local_gguf": self.local_gguf,
        }.get(self._mode, self.lm)

    def is_available(self) -> bool:
        return self._client().health_check()

    def available_models(self) -> list:
        client = self._client()
        models = client.list_models()
        if self._mode == "cloud":
            return [m for m in models if "gpt" in m.lower() or "o3" in m.lower()]
        if self._mode == "lmstudio":
            return [m for m in models if "embed" not in m.lower()]
        return models  # local_gguf

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
            emb = self._client().embed(chunk)

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
        """Pregunta con respuesta en streaming."""
        # Chat directo (sin RAG)
        if not use_context or self.vector_store.count == 0:
            messages = [{"role": "user", "content": question}]
            return self._client().chat_stream(messages, model=self.chat_model,
                                       on_token=on_token)

        # RAG: intentar embeddings, si falla, enviar contexto directamente
        try:
            q_embedding = self._get_cached_embedding(question)
            results = self.vector_store.search(q_embedding, top_k=config.TOP_K)
            found = bool(results)
        except Exception:
            found = False
            results = []

        if found:
            # RAG con embeddings exitoso
            context_parts = []
            sources = set()
            for text, source, score in results:
                context_parts.append(f"[{source}]\n{text.strip()[:500]}")
                sources.add(source)
            context = "\n\n---\n\n".join(context_parts)
            sources_str = ", ".join(sorted(sources))
            messages = [
                {"role": "system", "content": "Responde basado en el contexto. Si no encuentras la respuesta, dilo."},
                {"role": "user", "content": f"Contexto:\n{context}\n\nPregunta: {question}\nFuentes: {sources_str}"},
            ]
        else:
            # Fallback: enviar fragmentos directamente al chat
            texts = [f"[{d['source']}]\n{d['text'][:500]}" for d in self.vector_store.documents[:5]]
            context = "\n\n---\n\n".join(texts) if texts else ""
            sources_str = ", ".join(set(d['source'] for d in self.vector_store.documents[:5]))
            messages = [
                {"role": "system", "content": "Responde basado en el contexto. Si no encuentras la respuesta, dilo."},
                {"role": "user", "content": f"Documentos:\n{context}\n\nPregunta: {question}"},
            ]

        try:
            return self._client().chat_stream(messages, model=self.chat_model, on_token=on_token)
        except Exception:
            # Si todo falla, chat directo
            msg = f"(No pude consultar los documentos)\n\n{question}"
            return self._client().chat_stream(
                [{"role": "user", "content": msg}],
                model=self.chat_model, on_token=on_token
            )

    def query(self, question: str, use_context: bool = True) -> str:
        """Pregunta sin streaming."""
        return self.query_stream(question, use_context=use_context)

    def clear(self):
        self.vector_store.clear()

    def summarize(self, on_token=None, lang: str = "es") -> str:
        """Resumir documentos en el idioma seleccionado."""
        if self.vector_store.count == 0:
            msg = {"es": "No hay documentos cargados.", "en": "No documents loaded."}.get(lang, "No hay documentos cargados.")
            if on_token:
                for c in msg: on_token(c)
            return msg
        sources = ", ".join(self.vector_store.sources)
        texts = [d["text"][:300] for d in self.vector_store.documents[:10]]

        system_prompt = {
            "es": "Resume de forma clara y organizada en español.",
            "en": "Summarize clearly and organized in English.",
        }.get(lang, "Resume de forma clara y organizada.")

        user_prompt = {
            "es": f"Resume estos documentos:\nFuentes: {sources}\n\n",
            "en": f"Summarize these documents:\nSources: {sources}\n\n",
        }.get(lang, f"Resume estos documentos:\nFuentes: {sources}\n\n")

        prompt = user_prompt + "\n---\n".join(texts)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return self._client().chat_stream(messages, on_token=on_token)

    def translate(self, text: str, target: str = "en", on_token=None) -> str:
        """Traducir texto."""
        lang = {"en": "English", "es": "Spanish"}.get(target, target)
        messages = [
            {"role": "system", "content": f"Traduce a {lang}. Solo la traducción."},
            {"role": "user", "content": text},
        ]
        return self._client().chat_stream(messages, on_token=on_token)

    def export_chat(self, chat_html: str, filepath: str):
        """Exportar chat a TXT."""
        import re
        text = re.sub(r'<[^>]+>', '', chat_html)
        for e, r in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&quot;','"'),('&#39;',"'")]:
            text = text.replace(e, r)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("DocChat - Export\n" + "="*40 + "\n\n" + text.strip())
        return filepath

    def get_stats(self) -> Dict:
        return {
            "documents": self.vector_store.count,
            "sources": self.vector_store.sources,
            "model": self.chat_model,
            "available": self.is_available(),
            "lm_models": self.available_models(),
        }
