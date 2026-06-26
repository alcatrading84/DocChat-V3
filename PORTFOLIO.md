# 📄 DocChat — Project Portfolio

> **A production-ready AI document assistant built from scratch.**
> _100% local · No API keys required · 20+ formats · Dual UI_

---

## 👤 Role

**Full-Stack Python Developer & AI Engineer** — Sole developer, architect, and maintainer.
- Designed the entire system architecture
- Implemented all modules from scratch
- Packaged and distributed the application

---

## 🎯 Problem

Users needed a way to chat with their documents (PDFs, Word files, Excel sheets, code) using AI — but existing solutions required:
- Sending files to cloud services (privacy risk)
- API keys and paid subscriptions
- Complex setup and configuration
- Internet connectivity

---

## 💡 Solution

DocChat is a **complete offline AI document assistant** that runs entirely on the user's machine. Key design decisions:

| Decision | Rationale |
|----------|-----------|
| **Local-first** | All processing happens on-device. No data ever leaves the PC. |
| **Modular monolith** | Clear separation of concerns without microservice complexity |
| **Dual UI** | Desktop (PyQt6) for power users + Web UI (Flask) for quick access |
| **3 AI backends** | Choose between local GGUF, LM Studio, or OpenAI — same interface |
| **Plug-in formats** | Format handlers are independent functions, easy to extend |

---

## 🧱 Architecture

```
┌─────────────────────────────────────────────┐
│                run.py (CLI)                  │
├──────────────────────┬──────────────────────┤
│   ui.py (PyQt6)      │  web_ui.py (Flask)   │
│   Desktop GUI        │  REST API + SSE      │
├──────────────────────┴──────────────────────┤
│              engine.py (RAG Core)            │
│  ┌──────────┬──────────┬──────────────────┐  │
│  │LM Studio │ OpenAI   │  LocalModel      │  │
│  │Client    │ Client   │  (GGUF/llama-cpp)│  │
│  └──────────┴──────────┴──────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │        VectorStore (cosine search)    │  │
│  └────────────────────────────────────────┘  │
├─────────────────────────────────────────────┤
│  formats.py   │  ocr.py   │  metrics.py     │
├─────────────────────────────────────────────┤
│  config.py    │  lang.py  │  updater.py     │
└─────────────────────────────────────────────┘
```

---

## 🛠️ Technologies Demonstrated

### Core Development
| Technology | Proficiency Level | Used For |
|-----------|------------------|----------|
| **Python 3.10+** | Advanced | Entire application |
| **PyQt6** | Advanced | Desktop GUI, threading, theming |
| **Flask** | Intermediate | REST API, SSE streaming |
| **llama-cpp-python** | Intermediate | Local LLM inference |
| **httpx** | Intermediate | Async HTTP client for AI APIs |

### AI & Machine Learning
| Concept | Implementation |
|---------|---------------|
| **RAG (Retrieval-Augmented Generation)** | Custom chunking → embeddings → cosine similarity → context injection |
| **Vector Search** | NumPy-based cosine similarity, configurable top-K |
| **Embeddings** | LM Studio & local model embedding API |
| **Streaming** | Token-by-token generation with real-time UI updates |
| **Caching** | LRU embedding cache for repeated queries |
| **Model Management** | Auto-download, auto-detection, multiple backends |

### Software Engineering
| Practice | How It Shows |
|----------|-------------|
| **Clean Architecture** | 10+ modules with single responsibility |
| **OOP** | Client abstraction, workers, engine encapsulation |
| **Threading** | QThread workers with signal/slot pattern |
| **Error Handling** | Global exception handler, user-friendly messages |
| **Dependency Management** | Verified imports, optional dependencies |
| **I18n** | Complete Spanish/English translation system |
| **Packaging** | PyInstaller distribution, version management |
| **Auto-Updates** | GitHub API integration, background checking |

### Document Processing
| Technology | Purpose |
|-----------|---------|
| **pypdf** | PDF text extraction + encryption handling |
| **python-docx** | Microsoft Word documents |
| **python-pptx** | PowerPoint presentations |
| **openpyxl** | Excel spreadsheets |
| **pytesseract** | OCR for scanned PDFs/images |
| **Custom parsers** | CSV, JSON, XML, YAML, Markdown, HTML, code files |

---

## 🔑 Key Accomplishments

### 1. Unified RAG Pipeline
Built a complete RAG system from scratch: document chunking → embedding generation → vector storage → semantic search → context-aware LLM prompting. No external RAG frameworks — pure Python + NumPy.

### 2. Triple AI Backend Abstraction
Designed a polymorphic client interface so the same application works with:
- **Local GGUF models** (llama-cpp-python, ~1GB, no dependencies)
- **LM Studio** (OpenAI-compatible API, larger models)
- **OpenAI API** (GPT-4o-mini, maximum quality)

Switching backends is instant via UI dropdown.

### 3. Multi-Format Document Engine
Support for **20+ file formats** from PDFs to Excel to Python scripts — all unified through a single `load_any_document()` interface. Automatic OCR fallback for scanned PDFs with Tesseract.

### 4. Production-Quality UI
Professional dark-themed interface with:
- Live token streaming
- Drag-and-drop document loading
- Async workers (no UI freezing)
- Dark/light theme toggle
- English/Spanish bilingual support
- Status bar with connection monitoring

### 5. Complete Packaging & Distribution
- Standalone `.exe` (88 MB) via PyInstaller
- GitHub Releases with auto-updater
- Version management through single `version.py`
- Centralized configuration in `config.py`

---

## 📊 Code Quality

| Metric | Value |
|--------|-------|
| **Total modules** | 12 Python files |
| **Architecture layers** | CLI → UI → Engine → Backend |
| **Document formats** | 20+ supported |
| **AI backends** | 3 (local GGUF, LM Studio, OpenAI) |
| **UI frameworks** | 2 (PyQt6 desktop + Flask web) |
| **Languages** | English + Spanish |
| **Dependencies** | 15 packages (requirements.txt) |

---

## 🚀 Impact

DocChat enables users to:
- ✅ Analyze documents **privately** — no cloud uploads
- ✅ Work **offline** — no internet required
- ✅ Process **any format** — PDFs, Office, code, etc.
- ✅ Get answers **in real time** — streaming responses
- ✅ Save **money** — no API keys or subscriptions

---

## 🔗 Links

| Resource | URL |
|----------|-----|
| **GitHub Repository** | https://github.com/alcatrading84/DocChat-V3 |
| **Latest Release** | https://github.com/alcatrading84/DocChat-V3/releases/latest |
| **Download .exe** | https://github.com/alcatrading84/DocChat-V3/releases/download/v3.0.0/DocChat.exe |

---

## 📞 Contact

**[Your Name]**
- 🌐 GitHub: https://github.com/alcatrading84
- 📧 Email: [your-email@example.com]
- 💼 LinkedIn: https://linkedin.com/in/[your-profile]

---

<p align="center">
  <i>This project is open source under the MIT license.</i>
  <br>
  <i>Built with ❤️ using Python, PyQt6, and llama-cpp-python.</i>
</p>
