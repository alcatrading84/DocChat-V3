# 📄 DocChat v3 — Asistente Local de Documentos con IA

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?style=flat&logo=qt&logoColor=white)
![Flask](https://img.shields.io/badge/Web-Flask-000000?style=flat&logo=flask&logoColor=white)
![RAG](https://img.shields.io/badge/RAG-Semantic%20Search-8B5CF6?style=flat)
![OCR](https://img.shields.io/badge/OCR-Tesseract-FF6B35?style=flat)
![LLM](https://img.shields.io/badge/LLM-GGUF%20%7C%20LM%20Studio%20%7C%20OpenAI-00A67E?style=flat)
![Status](https://img.shields.io/badge/Status-Stable-22C55E?style=flat)

> **100% local · Sin API keys · Sin internet · Multi-formato**

DocChat es un asistente de IA que te permite chatear con tus documentos (PDF, Word, Excel, PowerPoint, código y más). Todo funciona 100% local en tu PC.

---

## 🚀 Cómo Empezar

[![Download](https://img.shields.io/badge/Download-Latest%20Release-3A83F1?style=for-the-badge&logo=github)](https://github.com/alcatrading84/DocChat-V3/releases/latest)

### Opción A: Ejecutable (Recomendado)
```bash
# 1. Ve a GitHub Releases
# 2. Descarga DocChat.exe
# 3. Haz doble clic para ejecutar
```

### Opción B: Desde código fuente
```bash
git clone https://github.com/alcatrading84/DocChat-V3.git
cd DocChat-V3
pip install -r requirements.txt
python run.py
```

---

## 🖥️ Cómo Ejecutar

| Comando | Función |
|---------|---------|
| `python run.py` | Interfaz de escritorio (PyQt6) |
| `python run.py --web` | Web UI en el navegador → http://localhost:5000 |
| `python run.py --debug` | Modo debug con consola detallada |
| `python run.py --report` | Mostrar reporte de métricas de uso |
| `python run.py --update` | Buscar actualizaciones en GitHub |
| `python run.py --mode lmstudio` | Forzar modo LM Studio |
| `python run.py --mode cloud` | Forzar modo OpenAI Cloud |
| `python run.py --mode local_gguf` | Forzar modo GGUF local |
| `python run.py --mode online` | Alias para `lmstudio` |
| `python run.py --mode offline` | Alias para `local_gguf` |

---

## 🧠 Modos de Funcionamiento

### 🖥️ Modo LM Studio (por defecto)
Conecta con **LM Studio** corriendo en `http://127.0.0.1:1234`.
- Modelos más grandes, mayor calidad
- Requiere LM Studio abierto con un modelo cargado

### ☁️ Modo Cloud (OpenAI)
Usa la API de **OpenAI** (modelo `gpt-4o-mini`).
- Máxima calidad
- Requiere API key de OpenAI

### 🏠 Modo GGUF Local (NUEVO en v3)
Usa **llama-cpp-python** para inferencia 100% local sin LM Studio.

| Modelo | Tamaño | RAM Mínima |
|--------|--------|------------|
| Qwen 2.5 1.5B (por defecto) | ~1 GB | 4 GB |
| Qwen 2.5 0.5B (alternativa ligera) | ~350 MB | 2 GB |
| Llama 3.2 1B (alternativa) | ~700 MB | 4 GB |

> El modelo se descarga **automáticamente** la primera vez que ejecutas DocChat en modo GGUF.

---

## 📁 Formatos Soportados (20+)

| Formato | Extensión | Cargador |
|---------|-----------|----------|
| PDF | `.pdf` | pypdf + **OCR automático** para escaneados |
| Word | `.docx` | python-docx |
| Texto | `.txt` | Nativo |
| Markdown | `.md` | Nativo |
| HTML | `.html`, `.htm` | Parser HTML |
| CSV | `.csv` | csv |
| Excel | `.xlsx`, `.xls` | openpyxl |
| PowerPoint | `.pptx` | python-pptx |
| JSON | `.json` | json |
| XML | `.xml` | Nativo |
| YAML | `.yaml`, `.yml` | pyyaml |
| Código fuente | `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.c`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`, `.sql`, `.sh`, `.bat`, `.ps1`, `.r` | Nativo |

---

## 🎯 Funcionalidades

- 📊 **Resumir documentos** al instante
- 🔍 **Buscar información** con RAG semántico
- 🌐 **Traducir respuestas** a inglés/español
- 📋 **Exportar chat** a TXT
- 🔄 **Auto-actualizaciones** desde GitHub
- 🌙 **Tema oscuro/claro** intercambiable
- 🌍 **Interfaz en español e inglés**
- 🚀 **Streaming en tiempo real** (SSE real en Web UI)
- 💾 **Caché de embeddings** para respuestas rápidas
- 👁️ **OCR** para PDFs escaneados (con Tesseract)

---

## 🛠️ Tecnologías

| Tecnología | Para qué |
|------------|----------|
| Python 3.10+ | Lenguaje base |
| PyQt6 | Interfaz de escritorio nativa |
| llama-cpp-python | Inferencia local sin LM Studio |
| Flask | Web UI alternativa |
| pypdf | Lectura de PDFs |
| pytesseract | OCR para escaneados |
| python-docx | Lectura de Word |
| python-pptx | Lectura de PowerPoint |
| openpyxl | Lectura de Excel |
| httpx | Comunicación HTTP con LM Studio |
| RAG | Búsqueda semántica en documentos |

---

## 📂 Estructura del Proyecto

```
DocChat/
├── run.py                 # 🚀 Lanzador (CLI + args)
├── requirements.txt       # Dependencias
├── DocChat.spec           # PyInstaller config
├── README.md              # Documentación
├── favicon.ico            # Icono de la aplicación
├── docchat/
│   ├── __init__.py
│   ├── config.py          # ⚙️ Configuración centralizada
│   ├── version.py         # 📌 Versión del proyecto
│   ├── engine.py          # 🏆 Motor RAG v3
│   ├── local_model.py     # 🧠 Modelo local (llama-cpp-python)
│   ├── ui.py              # 🖥️ UI de escritorio (PyQt6)
│   ├── web_ui.py          # 🌐 Web UI (Flask)
│   ├── ocr.py             # 👁️ OCR para PDFs escaneados
│   ├── formats.py         # 📊 Multi-formato (20+)
│   ├── metrics.py         # 📈 Métricas de uso
│   ├── updater.py         # 🔄 Auto-updates
│   └── lang.py            # 🌍 Traducciones ES/EN
├── docchat/
│   └── Guia_DocChat_v3.pdf  # 📄 Guía de usuario completa
└── dist/
    └── DocChat.exe        # 📦 Ejecutable portable
```

---

## 📥 Requisitos

- **Sistema:** Windows 10/11, Linux o macOS
- **RAM:** 4 GB (8 GB recomendado)
- **Disco:** 1 GB libre
- **Python:** 3.10+ (solo código fuente)

### Opcionales
- **Tesseract OCR** → Para leer PDFs escaneados
- **LM Studio** → Para modo LM Studio con modelos grandes

---

## 📄 Licencia

MIT — Haz lo que quieras con este código.
