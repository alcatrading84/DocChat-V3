"""DocChat Updater v3 — Actualizaciones automáticas desde GitHub.

Verifica si hay nuevas versiones en GitHub Releases.
Puede descargar e instalar la última versión automáticamente.
"""

import os
import sys
import json
import logging
import subprocess
import threading
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

from docchat import config

logger = logging.getLogger(__name__)

# Configuración (centralizada en docchat/config.py)
GITHUB_REPO = config.GITHUB_REPO
GITHUB_API = config.GITHUB_API
CURRENT_VERSION = config.CURRENT_VERSION
UPDATE_CHECK_FILE = config.UPDATE_CHECK_FILE


# =============================================================================
# VERIFICADOR DE VERSIONES
# =============================================================================

def get_current_version() -> str:
    """Obtener la versión actual de la aplicación."""
    return CURRENT_VERSION


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Convertir '3.0.0' a (3, 0, 0)."""
    try:
        return tuple(int(x) for x in version_str.split("."))
    except Exception:
        return (0, 0, 0)


def is_newer(remote: str, current: str) -> bool:
    """Comparar versiones semánticas."""
    return parse_version(remote) > parse_version(current)


def check_for_updates() -> Optional[Dict]:
    """
    Verificar si hay una nueva versión en GitHub Releases.

    Returns:
        Dict con info de la actualización, o None si no hay.
        Ej: {"version": "3.1.0", "url": "...", "notes": "..."}
    """
    try:
        import httpx
        resp = httpx.get(GITHUB_API, timeout=10,
                         headers={"Accept": "application/json"})
        resp.raise_for_status()
        release = resp.json()

        remote_version = release.get("tag_name", "").lstrip("v")
        if not remote_version:
            return None

        if not is_newer(remote_version, CURRENT_VERSION):
            logger.info(f"✅ Versión actual ({CURRENT_VERSION}) es la más reciente")
            return None

        # Buscar el asset (exe) correcto
        assets = release.get("assets", [])
        exe_asset = None
        for asset in assets:
            name = asset.get("name", "")
            if name.endswith(".exe") and "DocChat" in name:
                exe_asset = asset
                break

        update_info = {
            "version": remote_version,
            "current": CURRENT_VERSION,
            "url": exe_asset["browser_download_url"] if exe_asset else None,
            "notes": release.get("body", "")[:500],
            "download_url": release["html_url"],
        }

        logger.info(f"🔄 Nueva versión disponible: {remote_version}")
        return update_info

    except httpx.TimeoutException:
        logger.debug("Update check timed out (no internet)")
        return None
    except Exception as e:
        logger.debug(f"Error checking updates: {e}")
        return None


def check_for_updates_async(callback=None):
    """Verificar actualizaciones en segundo plano."""

    def _check():
        # No verificar más de una vez cada 24 horas
        if os.path.exists(UPDATE_CHECK_FILE):
            try:
                with open(UPDATE_CHECK_FILE, "r") as f:
                    data = json.load(f)
                last = datetime.fromisoformat(data.get("last_check", "2000-01-01"))
                if datetime.now() - last < timedelta(hours=24):
                    return
            except Exception:
                pass

        result = check_for_updates()

        # Guardar timestamp
        os.makedirs(os.path.dirname(UPDATE_CHECK_FILE), exist_ok=True)
        with open(UPDATE_CHECK_FILE, "w") as f:
            json.dump({"last_check": datetime.now().isoformat(),
                       "result": result}, f)

        if callback and result:
            callback(result)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


# =============================================================================
# DESCARGA E INSTALACIÓN
# =============================================================================

def download_update(update_info: Dict,
                    on_progress=None) -> Optional[str]:
    """
    Descargar la última versión del ejecutable.

    Args:
        update_info: Info de la actualización (de check_for_updates)
        on_progress: Callback (downloaded_mb, total_mb)

    Returns:
        Ruta al archivo descargado, o None si falló
    """
    url = update_info.get("url")
    if not url:
        logger.error("No hay URL de descarga disponible")
        return None

    version = update_info.get("version", "latest")
    dest_dir = tempfile.gettempdir()
    dest_path = os.path.join(dest_dir, f"DocChat_v{version}.exe")

    try:
        import httpx
        logger.info(f"📥 Descargando DocChat v{version}...")

        with httpx.stream("GET", url, follow_redirects=True,
                          timeout=300) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(dest_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress and total > 0:
                        on_progress(downloaded / (1024 * 1024),
                                    total / (1024 * 1024))

        logger.info(f"✅ Descargado: {dest_path}")
        return dest_path

    except Exception as e:
        logger.error(f"Error descargando actualización: {e}")
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        return None


def install_update(exe_path: str) -> bool:
    """
    Instalar la actualización descargada.

    Cierra la app actual y lanza el nuevo ejecutable.
    """
    if not os.path.exists(exe_path):
        logger.error(f"Actualización no encontrada: {exe_path}")
        return False

    try:
        # En Windows, renombrar y ejecutar
        if sys.platform == "win32":
            current_exe = sys.argv[0]
            backup = current_exe + ".bak"

            # Renombrar actual a .bak
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(current_exe, backup)

            # Copiar nuevo
            import shutil
            shutil.copy2(exe_path, current_exe)

            # Lanzar nuevo
            subprocess.Popen([current_exe],
                             creationflags=subprocess.CREATE_NEW_CONSOLE)

            # Cerrar este proceso
            logger.info("🔄 Actualización instalada. Reiniciando...")
            sys.exit(0)
        else:
            logger.info(f"Actualización descargada en: {exe_path}")
            return True

    except Exception as e:
        logger.error(f"Error instalando actualización: {e}")
        return False
