#!/usr/bin/env python3
"""DocChat — Lanzador con protección contra cierres inesperados.

USO:
  python run.py          # Modo normal
  python run.py --debug  # Muestra errores en consola
"""

import sys
import os
import traceback

# Añadir directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Manejador global de errores no capturados
def global_exception_handler(exctype, value, tb):
    """Captura cualquier error no manejado y muestra un mensaje."""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    # Intentar mostrar con QMessageBox si es posible
    try:
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("❌ Error inesperado")
        msg.setText("DocChat tuvo un error inesperado.")
        msg.setDetailedText(error_msg)
        msg.exec()
    except Exception:
        # Si no podemos mostrar Qt, imprimir a consola
        print(f"\n❌ ERROR INESPERADO:\n{error_msg}", file=sys.stderr)
    
    # Llamar al manejador original
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_exception_handler

# Verificar dependencias
missing = []
for mod, name in [('PyQt6.QtWidgets', 'PyQt6'), ('httpx', 'httpx'), ('numpy', 'numpy')]:
    try:
        __import__(mod.split('.')[0])
    except ImportError:
        missing.append(name)

if missing:
    print(f"\n❌ Faltan dependencias: {', '.join(missing)}")
    print(f"   Para instalarlas:")
    print(f"   pip install {' '.join(missing)}")
    input("\nPresiona Enter para salir...")
    sys.exit(1)

# Verificar LM Studio
try:
    import httpx
    r = httpx.get("http://127.0.0.1:1234/v1/models", timeout=3)
    if r.status_code == 200:
        models = [m["id"] for m in r.json().get("data", [])]
        print(f"✅ LM Studio conectado. Modelos:")
        for m in models:
            print(f"   • {m}")
    else:
        print("⚠️  LM Studio responde con código inesperado")
except Exception:
    print("⚠️  LM Studio no está corriendo en localhost:1234")
    print("   Abre LM Studio, carga un modelo y activa el servidor.\n")

# Lanzar la app con protección
try:
    from docchat.ui import main
    main()
except Exception as e:
    print(f"\n❌ Error al iniciar DocChat: {e}")
    traceback.print_exc()
    input("\nPresiona Enter para salir...")
    sys.exit(1)
