"""DocChat Config — Configuración centralizada de toda la aplicación.

Todas las constantes se definen aquí y se importan desde los módulos.
"""

import os

from docchat.version import __version__, __github_repo__

# =============================================================================
# RUTAS
# =============================================================================

# Directorio de datos del usuario (~/.docchat)
DATA_DIR = os.path.join(os.path.expanduser("~"), ".docchat")
if os.name == "nt":
    DATA_DIR = DATA_DIR.replace("/", "\\")

# Archivo de métricas
METRICS_FILE = os.path.join(DATA_DIR, "metrics.json")

# Directorio de modelos GGUF
MODELS_DIR = os.path.join(DATA_DIR, "models")

# Archivo de control de actualizaciones
UPDATE_CHECK_FILE = os.path.join(DATA_DIR, "last_update_check.json")

# Directorio de uploads (Web UI)
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

# =============================================================================
# LM STUDIO
# =============================================================================

LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"

# =============================================================================
# MODELO DE CHAT
# =============================================================================

CHAT_MODEL = "qwen2.5-coder-3b-instruct"
CHAT_MODEL_NAME = "docchat_local"  # Nombre interno para modelo GGUF

# =============================================================================
# CHUNKING (RAG)
# =============================================================================

CHUNK_SIZE = 300          # Tamaño de fragmento (palabras)
CHUNK_OVERLAP = 30        # Solapamiento entre fragmentos
TOP_K = 3                 # Fragmentos relevantes a recuperar

# =============================================================================
# MODELO LOCAL GGUF (llama-cpp-python)
# =============================================================================

DEFAULT_MODEL_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
DEFAULT_MODEL_FILE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
HF_BASE_URL = "https://huggingface.co"

# Alternativas (descomentar para usar):
# DEFAULT_MODEL_REPO = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
# DEFAULT_MODEL_FILE = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
# DEFAULT_MODEL_REPO = "QuantFactory/Llama-3.2-1B-Instruct-GGUF"
# DEFAULT_MODEL_FILE = "Llama-3.2-1B-Instruct.Q4_K_M.gguf"

# =============================================================================
# ACTUALIZACIONES
# =============================================================================

GITHUB_REPO = __github_repo__
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = __version__

# =============================================================================
# OPENAI
# =============================================================================

OPENAI_MODEL = "gpt-4o-mini"
