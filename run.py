#!/usr/bin/env python3
"""DocChat v3 — Lanzador con todas las mejoras.

USO:
  python run.py              # Modo normal (UI escritorio)
  python run.py --web        # Abrir Web UI directamente
  python run.py --debug      # Modo debug (consola detallada)
  python run.py --report     # Mostrar reporte de métricas
  python run.py --update     # Buscar actualizaciones
"""

import sys
import os
import logging
import traceback
import argparse

# Añadir directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# MANEJADOR GLOBAL DE ERRORES
# =============================================================================

def global_exception_handler(exctype, value, tb):
    """Captura cualquier error no manejado."""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    try:
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("❌ Error inesperado")
        msg.setText("DocChat tuvo un error inesperado.")
        msg.setDetailedText(error_msg)
        msg.exec()
    except Exception:
        print(f"\n❌ ERROR INESPERADO:\n{error_msg}", file=sys.stderr)
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_exception_handler


# =============================================================================
# VERIFICACIÓN DE DEPENDENCIAS
# =============================================================================

def check_dependencies():
    """Verificar que las dependencias principales estén instaladas."""
    required = [
        ('PyQt6.QtWidgets', 'PyQt6'),
        ('httpx', 'httpx'),
        ('pypdf', 'pypdf'),
    ]
    optional = [
        ('llama_cpp', 'llama-cpp-python'),
        ('pytesseract', 'pytesseract'),
        ('flask', 'flask'),
        ('openpyxl', 'openpyxl'),
        ('pptx', 'python-pptx'),
    ]

    missing = []
    for mod, name in required:
        try:
            __import__(mod.split('.')[0])
        except ImportError:
            missing.append(name)

    if missing:
        print(f"\n❌ Faltan dependencias obligatorias: {', '.join(missing)}")
        print(f"   pip install {' '.join(missing)}")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    # Opcionales: solo informar
    missing_opt = []
    for mod, name in optional:
        try:
            __import__(mod.split('.')[0])
        except ImportError:
            missing_opt.append(name)

    if missing_opt:
        print(f"\nℹ️  Dependencias opcionales no instaladas:")
        for m in missing_opt:
            print(f"   • {m}")
        print(f"   pip install {' '.join(missing_opt)}")
        print("   (DocChat funcionará sin ellas, pero con menos funciones)\n")


# =============================================================================
# CLI ARGUMENTS
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="📄 DocChat v3 — Asistente Local de Documentos"
    )
    parser.add_argument("--web", action="store_true",
                        help="Iniciar Web UI directamente")
    parser.add_argument("--debug", action="store_true",
                        help="Modo debug (consola detallada)")
    parser.add_argument("--report", action="store_true",
                        help="Mostrar reporte de métricas")
    parser.add_argument("--update", action="store_true",
                        help="Buscar actualizaciones")
    parser.add_argument("--mode", type=str,
                        choices=["lmstudio", "cloud", "local_gguf", "auto", "offline", "online"],
                        default="lmstudio", help="Modo de inferencia")
    return parser.parse_args()


# =============================================================================
# MAIN
# =============================================================================

def main():
    args = parse_args()

    # Mapear modos legacy a los nuevos
    mode_map = {"auto": "lmstudio", "offline": "local_gguf", "online": "lmstudio"}
    engine_mode = mode_map.get(args.mode, args.mode)

    # Configurar logging
    if args.debug:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    logging.basicConfig(
        level=logging_level,
        format="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    # Verificar dependencias
    check_dependencies()

    # Modo reporte
    if args.report:
        print("\n📊 Generando reporte de DocChat...")
        from docchat.engine import DocChatEngine
        engine = DocChatEngine(mode=engine_mode)
        engine.print_report()
        sys.exit(0)

    # Modo update
    if args.update:
        from docchat.updater import check_for_updates
        info = check_for_updates()
        if info:
            print(f"\n🔄 Nueva versión disponible: v{info['version']}")
            print(f"   Actual: v{info['current']}")
            print(f"   Descargar: {info.get('download_url', 'N/A')}")
        else:
            print("\n✅ Tienes la versión más reciente.")
        sys.exit(0)

    # Modo web
    if args.web:
        print("\n🌐 Iniciando DocChat Web UI...")
        from docchat.engine import DocChatEngine
        from docchat.web_ui import start_web_ui
        engine = DocChatEngine(mode=engine_mode)
        server = start_web_ui(engine, host="127.0.0.1", port=5000,
                              open_browser=True)
        print("Presiona Ctrl+C para detener el servidor.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Servidor detenido.")
            sys.exit(0)

    # Modo normal (UI escritorio)
    logger.info("🚀 Iniciando DocChat v3...")
    logger.info(f"   Python: {sys.version}")
    logger.info(f"   Directorio: {os.path.dirname(os.path.abspath(__file__))}")

    try:
        from docchat.ui import main as ui_main
        ui_main()
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"\n❌ Error al iniciar DocChat: {e}")
        traceback.print_exc()
        input("\nPresiona Enter para salir...")
        sys.exit(1)


if __name__ == "__main__":
    main()
