"""DocChat Metrics v3 — Estadísticas de uso y logging.

Registra:
- Documentos procesados (cantidad, tamaño, tiempo)
- Consultas realizadas (con/sin contexto)
- Tiempos de respuesta
- Errores frecuentes
- Estado del sistema
"""

import os
import json
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field, asdict

from docchat import config

logger = logging.getLogger(__name__)

# Archivo de métricas (centralizado en config.py)
METRICS_FILE = config.METRICS_FILE


# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Configurar el sistema de logging.

    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Ruta al archivo de log (None = solo consola)
    """
    log_dir = os.path.join(os.path.expanduser("~"), ".docchat", "logs")
    os.makedirs(log_dir, exist_ok=True)

    if log_file is None:
        log_file = os.path.join(
            log_dir,
            f"docchat_{datetime.now().strftime('%Y%m%d')}.log"
        )

    # Formato
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

    # Handler de archivo
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))

    # Raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # El handler filtra
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info(f"📝 Logging iniciado: {log_file}")
    return log_file


# =============================================================================
# MÉTRICAS DE USO
# =============================================================================

@dataclass
class DocEvent:
    """Evento de documento procesado."""
    filename: str
    format: str
    chars: int
    chunks: int
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class QueryEvent:
    """Evento de consulta."""
    question_length: int
    had_context: bool
    response_length: int
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ErrorEvent:
    """Evento de error."""
    error_type: str
    message: str
    context: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MetricsCollector:
    """Recolector de métricas de uso."""

    def __init__(self, metrics_file: str = METRICS_FILE):
        self.metrics_file = metrics_file
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """Cargar métricas desde archivo."""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.data = data
            except Exception:
                self.data = self._empty()
        else:
            self.data = self._empty()

    def _empty(self) -> Dict:
        return {
            "docs_processed": 0,
            "queries": 0,
            "errors": 0,
            "total_chars_processed": 0,
            "total_response_chars": 0,
            "total_duration_ms": 0,
            "formats_used": defaultdict(int),
            "recent_errors": [],
            "session_start": datetime.now().isoformat(),
            "queries_by_hour": defaultdict(int),
        }

    def _save(self):
        """Guardar métricas a archivo (thread-safe)."""
        with self._lock:
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            tmp = self.metrics_file + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    # Convertir defaultdicts a dicts normales
                    data = dict(self.data)
                    data["formats_used"] = dict(data.get("formats_used", {}))
                    data["queries_by_hour"] = dict(data.get("queries_by_hour", {}))
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(tmp, self.metrics_file)
            except Exception as e:
                logger.warning(f"No se pudieron guardar métricas: {e}")
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass

    def log_doc(self, event: DocEvent):
        """Registrar un documento procesado."""
        self.data["docs_processed"] += 1
        self.data["total_chars_processed"] += event.chars
        self.data["total_duration_ms"] += event.duration_ms
        fmt = event.format
        if isinstance(self.data["formats_used"], dict):
            self.data["formats_used"][fmt] = self.data["formats_used"].get(fmt, 0) + 1
        logger.info(
            f"📄 Documento: {event.filename} | "
            f"{event.chars} chars | {event.chunks} chunks | "
            f"{event.duration_ms:.0f}ms"
        )
        if self.data["docs_processed"] % 5 == 0:
            self._save()

    def log_query(self, event: QueryEvent):
        """Registrar una consulta."""
        self.data["queries"] += 1
        self.data["total_response_chars"] += event.response_length
        self.data["total_duration_ms"] += event.duration_ms

        hour = datetime.now().hour
        if isinstance(self.data["queries_by_hour"], dict):
            self.data["queries_by_hour"][str(hour)] = \
                self.data["queries_by_hour"].get(str(hour), 0) + 1

        logger.debug(
            f"💬 Query: {event.question_length}chars | "
            f"context={'yes' if event.had_context else 'no'} | "
            f"{event.duration_ms:.0f}ms"
        )

    def log_error(self, event: ErrorEvent):
        """Registrar un error."""
        self.data["errors"] += 1
        recent = self.data.get("recent_errors", [])
        recent.append(asdict(event))
        if len(recent) > 20:
            recent = recent[-20:]
        self.data["recent_errors"] = recent
        logger.error(f"❌ {event.error_type}: {event.message}")
        self._save()

    def get_summary(self) -> Dict:
        """Obtener resumen de métricas."""
        self._load()
        data = dict(self.data)

        # Calcular promedios
        total_docs = data.get("docs_processed", 0)
        total_queries = data.get("queries", 0)

        data["avg_doc_chars"] = round(
            data.get("total_chars_processed", 0) / max(total_docs, 1)
        )
        data["avg_response_chars"] = round(
            data.get("total_response_chars", 0) / max(total_queries, 1)
        )
        data["avg_duration_ms"] = round(
            data.get("total_duration_ms", 0) / max(total_queries + total_docs, 1)
        )

        return data

    def print_report(self):
        """Imprimir reporte en consola."""
        s = self.get_summary()
        print("\n" + "=" * 50)
        print("📊 DOCCHAT - REPORTE DE USO")
        print("=" * 50)
        print(f"📄 Documentos procesados: {s['docs_processed']}")
        print(f"💬 Consultas realizadas:   {s['queries']}")
        print(f"❌ Errores:                {s['errors']}")
        print(f"📏 Promedio chars/doc:     {s['avg_doc_chars']}")
        print(f"📏 Promedio chars/resp:    {s['avg_response_chars']}")
        print(f"⏱️  Duración promedio:      {s['avg_duration_ms']}ms")
        print(f"📁 Formatos usados:        {s.get('formats_used', {})}")
        print("=" * 50)

    def reset(self):
        """Reiniciar métricas."""
        self.data = self._empty()
        self._save()
        logger.info("🔄 Métricas reiniciadas")
