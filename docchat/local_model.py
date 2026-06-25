"""DocChat Local Model v3 — Inferencia local sin LM Studio.

Usa llama-cpp-python para ejecutar modelos GGUF directamente.
No necesita servidor externo, todo corre en el mismo proceso.

Características:
- 🏆 Sin LM Studio: modelo empaquetado/descargado automáticamente
- 🔄 Streaming de tokens en tiempo real
- 📐 Embeddings integrados (mismo modelo)
- 📦 Auto-descarga del modelo en primera ejecución
"""

import os
import sys
import json
import time
import math
import hashlib
import shutil
import pickle
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple, Generator
from dataclasses import dataclass, field

from docchat import config

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN DE MODELOS
# =============================================================================

# Las constantes están centralizadas en docchat/config.py
# Los valores por defecto se importan desde allí.

# Modelo pequeño recomendado: Qwen2.5-1.5B-Instruct Q4_K_M (~1GB)
# Descomenta el que prefieras en config.py:
#   - Qwen2.5-1.5B: ~1GB, 4GB RAM mínimo
#   - Qwen2.5-0.5B: ~350MB, 2GB RAM mínimo
#   - Llama 3.2 1B: ~700MB, 4GB RAM


# =============================================================================
# DESCARGA DE MODELOS
# =============================================================================

def get_model_path(model_file: str = config.DEFAULT_MODEL_FILE) -> str:
    """Obtener la ruta del modelo GGUF, descargarlo si no existe."""
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    model_path = os.path.join(config.MODELS_DIR, model_file)

    if os.path.exists(model_path):
        logger.info(f"✅ Modelo encontrado: {model_path}")
        return model_path

    # No existe → descargar
    logger.info(f"📥 Modelo no encontrado. Descargando {model_file}...")
    print(f"\n📥 Descargando modelo {model_file} (~1GB)...")
    print("   Esto solo ocurre la primera vez.\n")

    url = f"{config.HF_BASE_URL}/{config.DEFAULT_MODEL_REPO}/resolve/main/{model_file}"
    _download_file(url, model_path)

    return model_path


def _download_file(url: str, dest: str):
    """Descargar archivo con barra de progreso."""
    import urllib.request

    def report(block_num, block_size, total_size):
        downloaded = block_num * block_size / (1024 * 1024)
        total_mb = total_size / (1024 * 1024) if total_size > 0 else 0
        pct = (block_num * block_size / total_size * 100) if total_size > 0 else 0
        sys.stdout.write(f"\r   📦 {downloaded:.0f} / {total_mb:.0f} MB ({pct:.0f}%)")
        sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, dest, report)
        print("\n   ✅ Descarga completada!\n")
    except Exception as e:
        if os.path.exists(dest):
            os.remove(dest)
        raise RuntimeError(f"Error descargando modelo: {e}\n"
                           "Verifica tu conexión a internet.")


# =============================================================================
# MODELO LOCAL (llama-cpp-python)
# =============================================================================

class LocalModel:
    """Wrapper alrededor de llama-cpp-python para chat + embeddings."""

    def __init__(self, model_path: str = None, n_ctx: int = 4096,
                 n_threads: int = None, n_gpu_layers: int = 0):
        """
        Args:
            model_path: Ruta al archivo .gguf. Si es None, se descarga el default.
            n_ctx: Contexto máximo (tokens).
            n_threads: Hilos de CPU (auto si None).
            n_gpu_layers: Capas en GPU (0 = solo CPU).
        """
        self.model_path = model_path or get_model_path()
        self.n_ctx = n_ctx
        self.n_threads = n_threads or max(1, os.cpu_count() // 2)
        self.n_gpu_layers = n_gpu_layers
        self._model = None
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """Cargar el modelo (lazy)."""
        if self._model is not None:
            return

        logger.info(f"⏳ Cargando modelo: {os.path.basename(self.model_path)}")
        logger.info(f"   Contexto: {self.n_ctx} tokens")
        logger.info(f"   Hilos: {self.n_threads}, GPU layers: {self.n_gpu_layers}")
        print(f"⏳ Cargando modelo {os.path.basename(self.model_path)}...")

        try:
            from llama_cpp import Llama

            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
            )
            logger.info("✅ Modelo cargado exitosamente")
            print("✅ Modelo listo!\n")
        except ImportError:
            raise ImportError(
                "llama-cpp-python no está instalado.\n"
                "  pip install llama-cpp-python\n\n"
                "Si tienes problemas, instala la versión precompilada:\n"
                "  pip install llama-cpp-python --prefer-binary"
            )
        except Exception as e:
            raise RuntimeError(f"Error cargando modelo: {e}")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _ensure_loaded(self):
        if self._model is None:
            self._load()

    # -------------------------------------------------------------------------
    # CHAT (con streaming)
    # -------------------------------------------------------------------------

    def chat_stream(self, messages: List[Dict],
                    max_tokens: int = 1024,
                    temperature: float = 0.7,
                    top_p: float = 0.9,
                    on_token: Callable = None) -> str:
        """Chat con streaming de tokens."""
        self._ensure_loaded()

        # Convertir mensajes a formato llama.cpp
        prompt = self._format_chat_template(messages)

        full_response = ""
        with self._lock:
            try:
                generator = self._model.create_completion(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stream=True,
                    stop=["<|im_end|>", "<|end|>", "</s>", "<s>"],
                )

                for output in generator:
                    token = output["choices"][0].get("text", "")
                    if token:
                        full_response += token
                        if on_token:
                            on_token(token)

            except Exception as e:
                raise RuntimeError(f"Error en inferencia: {e}")

        return full_response.strip()

    def chat(self, messages: List[Dict],
             max_tokens: int = 1024,
             temperature: float = 0.7) -> str:
        """Chat sin streaming."""
        return self.chat_stream(messages, max_tokens, temperature)

    def _format_chat_template(self, messages: List[Dict]) -> str:
        """Formatear mensajes al estilo ChatML (Qwen)."""
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"
        return prompt

    # -------------------------------------------------------------------------
    # EMBEDDINGS (usando el mismo modelo)
    # -------------------------------------------------------------------------

    def embed(self, text: str) -> List[float]:
        """Generar embedding usando el modelo (último hidden state)."""
        self._ensure_loaded()
        with self._lock:
            try:
                # Truncar a 512 tokens para embeddings rápidos
                max_len = min(len(text), 2000)
                truncated = text[:max_len]

                result = self._model.create_embedding(input=truncated)
                return result["data"][0]["embedding"]
            except Exception as e:
                logger.warning(f"Error en embedding, usando fallback: {e}")
                # Fallback: embedding basado en hash
                return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str, dim: int = 768) -> List[float]:
        """Embedding de respaldo cuando el modelo no soporta embeddings."""
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(dim):
            val = (h[i % len(h)] / 255.0) * 2 - 1
            vec.append(val)
        return vec

    # -------------------------------------------------------------------------
    # UTILIDADES
    # -------------------------------------------------------------------------

    def health_check(self) -> bool:
        try:
            return self._model is not None
        except Exception:
            return False

    def get_info(self) -> Dict:
        info = {"loaded": self.is_loaded}
        if self.is_loaded:
            info.update({
                "model": os.path.basename(self.model_path),
                "context": self.n_ctx,
                "threads": self.n_threads,
                "gpu_layers": self.n_gpu_layers,
                "size_gb": round(os.path.getsize(self.model_path) / (1024**3), 2),
            })
        return info

    def unload(self):
        """Descargar el modelo de memoria."""
        if self._model is not None:
            try:
                self._model = None
                import gc
                gc.collect()
                logger.info("🧹 Modelo descargado de memoria")
            except Exception as e:
                logger.warning(f"Error al descargar modelo: {e}")


# =============================================================================
# MODO HÍBRIDO: LM Studio + Local
# =============================================================================

class HybridProvider:
    """Usa LM Studio si está disponible, si no, usa el modelo local."""

    def __init__(self, local_model: LocalModel = None):
        self.local = local_model or LocalModel()
        self._lm_client = None
        self._using_local = True

    @property
    def using_local(self) -> bool:
        return self._using_local

    def health_check(self) -> bool:
        """Verificar LM Studio primero, fallback a local."""
        try:
            import httpx
            r = httpx.get("http://127.0.0.1:1234/v1/models", timeout=2)
            if r.status_code == 200:
                self._using_local = False
                self._lm_client = r
                return True
        except Exception:
            pass

        # Fallback a local
        self._using_local = True
        return self.local.health_check()

    def chat_stream(self, messages: List[Dict],
                    on_token: Callable = None, **kwargs) -> str:
        if not self._using_local and self._lm_client is not None:
            return self._lm_chat_stream(messages, on_token, **kwargs)
        return self.local.chat_stream(messages, on_token=on_token, **kwargs)

    def _lm_chat_stream(self, messages, on_token, **kwargs):
        """Chat via LM Studio (heredado de engine.py)."""
        import httpx
        payload = {
            "model": kwargs.get("model", "local"),
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

    def embed(self, text: str) -> List[float]:
        if not self._using_local and self._lm_client is not None:
            return self._lm_embed(text)
        return self.local.embed(text)

    def _lm_embed(self, text: str) -> List[float]:
        import httpx
        try:
            resp = httpx.post("http://127.0.0.1:1234/v1/embeddings",
                json={"model": "text-embedding-nomic-embed-text-v1.5", "input": text},
                timeout=30)
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
        except Exception:
            return self.local.embed(text)
