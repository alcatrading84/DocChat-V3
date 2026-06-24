# 📄 DocChat v3 — Asistente Local de Documentos con IA

> **Chat con tus documentos. 100% local. Sin API keys. Sin internet. Sin LM Studio.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/version-3.0.0-brightgreen)

---

## 🚀 Novedades v3

| Mejora | Estado |
|--------|--------|
| 🏆 **Modo offline** — Sin LM Studio. Usa llama-cpp-python | ✅ |
| 🖼️ **OCR** — Lee PDFs escaneados (con Tesseract) | ✅ |
| 📊 **Multi-formato** — CSV, Excel, PPTX, MD, HTML, código | ✅ |
| 🌐 **Web UI** — Interfaz desde el navegador (Flask) | ✅ |
| 📈 **Métricas** — Estadísticas de uso detalladas | ✅ |
| 🔄 **Auto-updates** — Verifica actualizaciones en GitHub | ✅ |
| 🎨 **UI mejorada** — Vista previa, modo selector, stats | ✅ |
| 📦 **Auto-descarga** — El modelo se descarga solo | ✅ |

---

## ✨ Características

| Característica | ✅ |
|---------------|-----|
| **100% local** — Sin enviar datos a internet | ✅ |
| **Sin API keys** — No necesita OpenAI ni nada | ✅ |
| **Sin LM Studio** — Modelo local empaquetado 🏆 | ✅ |
| **Gratuito** — Sin costos de uso | ✅ |
| **PDF, DOCX, TXT, MD, HTML, CSV, XLSX, PPTX** | ✅ |
| **OCR** para PDFs escaneados | ✅ |
| **Interfaz bonita** — PyQt6 nativa + Web UI | ✅ |
| **Rápido** — Modelo local optimizado (CPU/GPU) | ✅ |
| **Privado** — Tus documentos nunca salen de tu PC | ✅ |
| **Streaming** — Respuestas en tiempo real | ✅ |

---

## 📋 Requisitos

### Mínimos (modo offline)
- **Windows 10/11**, Linux o macOS
- **4 GB RAM** (8 GB recomendado)
- **1 GB espacio** para el modelo local

### Opcionales
- **Tesseract OCR** para PDFs escaneados
- **LM Studio** si prefieres modo online

---

## 🔧 Instalación

### Opción 1: Desde código fuente (recomendado)

```bash
# 1. Clonar
git clone https://github.com/tuusuario/DocChat.git
cd DocChat

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Instalar modelo local (opcional, se descarga solo)
#    La primera vez que ejecutes, descargará ~1GB

# 4. Ejecutar
python run.py
```

### Opción 2: Ejecutable (Windows)

1. Descarga `DocChat.exe` desde [GitHub Releases](https://github.com/tuusuario/DocChat/releases)
2. Haz doble clic para ejecutar
3. En la primera ejecución, **descarga el modelo automáticamente** (~1GB)

---

## 🎮 Cómo usar

```
1. Ejecuta: python run.py (o abre DocChat.exe)
2. Espera a que se cargue el modelo (primera vez: ~1-2 min)
3. Arrastra documentos al panel izquierdo
4. Escribe preguntas sobre ellos
5. ¡La IA responde en tiempo real!
```

### Opciones de línea de comandos

```bash
python run.py              # UI de escritorio (recomendado)
python run.py --web        # Abrir Web UI en el navegador
python run.py --debug      # Modo debug (consola)
python run.py --report     # Mostrar reporte de métricas
python run.py --update     # Buscar actualizaciones
python run.py --mode offline  # Forzar modo local
python run.py --mode online   # Forzar LM Studio
```

---

## 🌐 Web UI

Además de la interfaz de escritorio, DocChat incluye una **Web UI**:

```bash
python run.py --web
# Abre http://localhost:5000 en tu navegador
```

O desde la UI: haz clic en el botón **🌐 Web UI**.

---

## 🧠 Modelos

### Modo Local (por defecto)
- **Qwen 2.5 1.5B** — Descarga automática (~1GB)
- Alternativa ligera: **Qwen 2.5 0.5B** (~350MB)
- Para más RAM: **Llama 3.2 1B** (~700MB)

### Modo LM Studio (opcional)
Si ya tienes LM Studio, puedes usarlo:
```bash
python run.py --mode online
```

O desde la UI: selecciona "☁️ LM Studio" en el selector de modo.

---

## 📁 Formatos soportados

| Formato | Extensión | Cargador |
|---------|-----------|----------|
| PDF | .pdf | pypdf + OCR |
| Word | .docx | python-docx |
| Texto | .txt | nativo |
| Markdown | .md | nativo |
| HTML | .html, .htm | parser HTML |
| CSV | .csv | csv |
| Excel | .xlsx, .xls | openpyxl |
| PowerPoint | .pptx | python-pptx |
| JSON | .json | json |
| XML | .xml | nativo |
| YAML | .yaml, .yml | pyyaml |
| Código | .py, .js, .ts, .java, .cpp, .c, .go, .rs, .rb, .php, .swift, .kt, .sql, .sh, .bat, .ps1, .r | nativo |

---

## 📊 Estructura del proyecto

```
DocChat/
├── run.py                 # Lanzador (CLI + args)
├── requirements.txt       # Dependencias
├── DocChat.spec           # PyInstaller config
├── README.md              # Esta documentación
├── docchat/
│   ├── __init__.py
│   ├── engine.py          # 🏆 Motor RAG v3 (unificado)
│   ├── local_model.py     # 🧠 Modelo local (llama-cpp-python)
│   ├── ui.py              # 🖥️ UI de escritorio (PyQt6)
│   ├── web_ui.py          # 🌐 Web UI (Flask)
│   ├── ocr.py             # 👁️ OCR para PDFs escaneados
│   ├── formats.py         # 📊 Multi-formato
│   ├── metrics.py         # 📈 Métricas de uso
│   ├── updater.py         # 🔄 Auto-updates
│   └── lang.py            # 🌍 Traducciones ES/EN
└── favicon.ico            # Icono
```

---

## 🛠️ Tecnologías

| Tecnología | Para qué |
|-----------|---------|
| **Python 3.10+** | Lenguaje base |
| **PyQt6** | Interfaz de escritorio nativa |
| **llama-cpp-python** | 🏆 Inferencia local sin LM Studio |
| **Flask** | 🌐 Web UI alternativa |
| **pypdf** | Lectura de PDFs |
| **pytesseract** | 👁️ OCR para escaneados |
| **python-docx** | Lectura de Word |
| **python-pptx** | Lectura de PowerPoint |
| **openpyxl** | Lectura de Excel |
| **httpx** | Comunicación HTTP |
| **RAG** | Búsqueda semántica en documentos |

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea tu rama: `git checkout -b feature/nueva-mejora`
3. Commit: `git commit -m 'Agrega nueva mejora'`
4. Push: `git push origin feature/nueva-mejora`
5. Abre un Pull Request

---

## 📄 Licencia

MIT — Haz lo que quieras con este código.

---

## 🏆 ¿Por qué este proyecto brilla?

| Aspecto | Lo que demuestra |
|---------|-----------------|
| **RAG** | Técnica más demandada en 2026 |
| **Arquitectura limpia** | Módulos separados, código legible |
| **UI dual** | Escritorio + Web |
| **IA local** | Sin depender de APIs externas |
| **Producto completo** | De principio a fin, listo para producción |
| **Documentación** | README completo, guía de usuario |
| **Auto-instalable** | Descarga de modelo, updates, empaquetado |

---

**¿Preguntas?** Abre un issue o contribuye al proyecto.
