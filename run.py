#!/usr/bin/env python3
"""DocChat — Lanzador de la aplicación.

REQUISITOS:
  1. LM Studio corriendo con un modelo cargado
     (http://127.0.0.1:1234)
  2. Python 3.10+ con: pip install PyQt6 httpx pypdf python-docx numpy

USO:
  python run.py
"""

import sys
import os

# Añadir directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Verificar dependencias
missing = []
try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    missing.append("PyQt6")

try:
    import httpx
except ImportError:
    missing.append("httpx")

try:
    import numpy as np
except ImportError:
    missing.append("numpy")

if missing:
    print("❌ Faltan dependencias. Instálalas con:")
    print(f"   pip install {' '.join(missing)}\n")
    sys.exit(1)

# Verificar LM Studio
import httpx as _httpx
try:
    r = _httpx.get("http://127.0.0.1:1234/v1/models", timeout=3)
    if r.status_code == 200:
        models = [m["id"] for m in r.json().get("data", [])]
        print(f"✅ LM Studio conectado. Modelos disponibles:")
        for m in models:
            print(f"   • {m}")
    else:
        print("⚠️  LM Studio responde pero con código inesperado")
except Exception:
    print("⚠️  LM Studio no está corriendo en localhost:1234")
    print("   Abre LM Studio, carga un modelo y activa el servidor.")
    print("   La app se abrirá igualmente.\n")

# Lanzar la app
from docchat.ui import main
main()
