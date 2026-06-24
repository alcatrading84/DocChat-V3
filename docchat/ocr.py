"""DocChat OCR v3 — Reconocimiento óptico para PDFs escaneados.

Convierte imágenes y PDFs escaneados a texto usando Tesseract OCR.
Funciona como fallback cuando la extracción normal no devuelve texto.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DETECCIÓN DE TESSERACT
# =============================================================================

def find_tesseract() -> Optional[str]:
    """Encontrar la ruta de Tesseract OCR en el sistema."""
    # Rutas comunes en Windows
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    # Buscar en PATH
    try:
        if sys.platform == "win32":
            result = subprocess.run(["where", "tesseract"],
                                    capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(["which", "tesseract"],
                                    capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass

    return None


def is_tesseract_available() -> bool:
    """Verificar si Tesseract está instalado."""
    return find_tesseract() is not None


def get_tesseract_version() -> str:
    """Obtener versión de Tesseract."""
    tesseract_path = find_tesseract()
    if not tesseract_path:
        return "No instalado"
    try:
        result = subprocess.run([tesseract_path, "--version"],
                                capture_output=True, text=True, timeout=5)
        return result.stdout.split("\n")[0] if result.stdout else "Desconocido"
    except Exception:
        return "Error al obtener versión"


# =============================================================================
# OCR CON PYTESSERACT
# =============================================================================

def ocr_image(image_path: str, lang: str = "spa+eng") -> str:
    """
    Extraer texto de una imagen usando Tesseract OCR.

    Args:
        image_path: Ruta a la imagen (PNG, JPG, etc.)
        lang: Idioma(s) para OCR ("spa+eng" = español + inglés)

    Returns:
        Texto extraído

    Raises:
        RuntimeError: Si Tesseract no está instalado
    """
    tesseract_path = find_tesseract()
    if not tesseract_path:
        raise RuntimeError(
            "Tesseract OCR no está instalado.\n\n"
            "Para instalar:\n"
            "  1. Descarga: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  2. Durante la instalación, marca idiomas: Spanish + English\n"
            "  3. Agrega al PATH o reinicia la app\n\n"
            "O usa pip: pip install pytesseract (requiere Tesseract instalado)"
        )

    try:
        from PIL import Image
        import pytesseract

        # Configurar ruta si es necesario
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Abrir imagen y extraer texto
        img = Image.open(image_path)

        # Preprocesar para mejor OCR (escala de grises + contraste)
        if img.mode != "L":
            img = img.convert("L")  # Escala de grises

        # Aplicar umbral para mejorar contraste
        img = img.point(lambda x: 0 if x < 128 else 255)

        text = pytesseract.image_to_string(img, lang=lang)
        return text.strip()

    except ImportError:
        raise RuntimeError(
            "Falta pytesseract o Pillow.\n"
            "  pip install pytesseract Pillow"
        )
    except Exception as e:
        raise RuntimeError(f"Error en OCR: {e}")


def ocr_pdf_page(pdf_path: str, page_num: int,
                 lang: str = "spa+eng",
                 dpi: int = 200) -> str:
    """
    Extraer texto de una página de PDF escaneado usando OCR.

    Convierte la página a imagen y aplica Tesseract.

    Args:
        pdf_path: Ruta al PDF
        page_num: Número de página (0-indexed)
        lang: Idioma(s) para OCR
        dpi: Resolución de conversión (mayor = mejor OCR, más lento)

    Returns:
        Texto extraído de la página
    """
    try:
        # Convertir PDF a imagen con pdf2image (si está disponible)
        try:
            from pdf2image import convert_from_path
        except ImportError:
            # Fallback: usar PyMuPDF (fitz)
            try:
                import fitz
            except ImportError:
                raise ImportError(
                    "Para OCR en PDFs necesitas:\n"
                    "  pip install pdf2image\n"
                    "O: pip install PyMuPDF"
                )

            doc = fitz.open(pdf_path)
            page = doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            img_path = os.path.join(
                os.path.dirname(pdf_path),
                f"_ocr_temp_{page_num}.png"
            )
            pix.save(img_path)
            doc.close()

            try:
                text = ocr_image(img_path, lang)
                return text
            finally:
                if os.path.exists(img_path):
                    os.remove(img_path)

        # Usar pdf2image
        images = convert_from_path(
            pdf_path,
            first_page=page_num + 1,
            last_page=page_num + 1,
            dpi=dpi,
        )
        if not images:
            return ""

        img_path = os.path.join(
            os.path.dirname(pdf_path),
            f"_ocr_temp_{page_num}.png"
        )
        images[0].save(img_path, "PNG")

        try:
            text = ocr_image(img_path, lang)
            return text
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    except ImportError as e:
        raise RuntimeError(f"Faltan dependencias para OCR: {e}")
    except Exception as e:
        raise RuntimeError(f"Error en OCR de página {page_num}: {e}")


def ocr_full_pdf(pdf_path: str, lang: str = "spa+eng",
                 on_progress=None) -> str:
    """
    OCR completo de un PDF escaneado (todas las páginas).

    Args:
        pdf_path: Ruta al PDF
        lang: Idioma(s) para OCR
        on_progress: Callback (actual, total, mensaje)

    Returns:
        Texto completo del PDF
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        total = len(reader.pages)
    except Exception:
        # Si no podemos leer metadatos, asumir N páginas
        total = 0

    all_text = []
    page_num = 0

    while True:
        if on_progress:
            on_progress(page_num + 1, total or "?", f"OCR página {page_num + 1}")

        try:
            text = ocr_pdf_page(pdf_path, page_num, lang)
            if text.strip():
                all_text.append(text)
            page_num += 1
        except Exception as e:
            logger.warning(f"Error en página {page_num}: {e}")
            break

        # Si no sabemos el total, detectar fin
        if total == 0 and page_num > 50:
            break
        if total > 0 and page_num >= total:
            break

    return "\n\n".join(t for t in all_text if t.strip())


def needs_ocr(text: str) -> bool:
    """
    Determinar si un texto extraído necesita OCR.
    Un texto muy corto o sin palabras reales sugiere PDF escaneado.
    """
    if not text or len(text.strip()) < 50:
        return True

    # Contar palabras reales vs basura
    words = text.strip().split()
    real_words = sum(1 for w in words if any(c.isalpha() for c in w))

    if len(words) == 0:
        return True

    ratio = real_words / len(words)
    return ratio < 0.3  # Menos del 30% son palabras reales
