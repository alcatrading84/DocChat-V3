# 📄 DocChat — Asistente Local de Documentos con IA

> **Chat con tus PDF, Word y TXT. 100% local. Sin API keys. Sin internet.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Estado-Funcional-brightgreen)

---

## 🚀 ¿Qué hace?

Cargas un documento (PDF, Word o TXT) y le haces preguntas. La IA responde **basándose exclusivamente en el contenido de tus documentos**.

```
Tú: ¿Cuál es el plazo de entrega del proyecto?
DocChat: Según el documento "contrato.pdf", el plazo de entrega es 30 días
         a partir de la firma del acuerdo (página 3).
```

## ✨ Características

| Característica | ✅ |
|---------------|-----|
| **100% local** — No envía datos a internet | ✅ |
| **Sin API keys** — No necesita OpenAI ni nada | ✅ |
| **Gratuito** — Sin costos de uso | ✅ |
| **PDF, DOCX, TXT** — Formatos más usados | ✅ |
| **Interfaz bonita** — PyQt6 nativa, no Electron | ✅ |
| **Rápido** — Modelo local en GPU/CPU | ✅ |
| **Privado** — Tus documentos nunca salen de tu PC | ✅ |

## 🖥️ Captura

```
┌──────────────────────────────────────────────────┐
│  📄 DocChat — Asistente Local de Documentos      │
├──────────┬───────────────────────────────────────┤
│ 📁 Docs  │  🧠 [qwen2.5-coder] [📄 RAG ON]      │
│          ├───────────────────────────────────────┤
│ ┌──────┐ │  🤖 DocChat:                         │
│ │Arrastra││  Según el documento "manual.pdf",    │
│ │ PDFs   ││  el proceso consta de 3 pasos:      │
│ │ aquí   ││  1. Análisis de requisitos          │
│ └──────┘ ││  2. Desarrollo del prototipo        │
│          ││  3. Pruebas y validación            │
│ ✅ doc1  ││                                      │
│ ✅ doc2  │├───────────────────────────────────────┤
│          ││ ┌─────────────────────────────┐ ▶ │  │
│          ││ │Pregunta aquí...             │    │  │
│          ││ └─────────────────────────────┘    │  │
└──────────┴───────────────────────────────────────┘
```

## 📋 Requisitos

1. **LM Studio** — Descárgalo de [lmstudio.ai](https://lmstudio.ai)
2. **Python 3.10+**
3. Un modelo cargado en LM Studio (ej: Qwen 2.5, Llama 3, DeepSeek)

## 🔧 Instalación

```bash
# 1. Clonar
git clone https://github.com/tuusuario/DocChat.git
cd DocChat

# 2. Instalar dependencias
pip install PyQt6 httpx pypdf python-docx numpy

# 3. Abrir LM Studio y cargar un modelo
#    (Ej: qwen2.5-coder-3b-instruct)
#    Activar el servidor en http://localhost:1234

# 4. Ejecutar
python run.py
```

## 🎮 Cómo usar

```
1. Abre LM Studio → Carga un modelo → Activa servidor
2. Ejecuta: python run.py
3. Arrastra tus documentos al panel izquierdo
4. Escribe preguntas sobre ellos
5. ¡La IA responde!
```

## 🧠 Modelos recomendados

| Modelo | Tamaño | RAM | Calidad |
|--------|--------|-----|---------|
| Qwen 2.5 3B | 1.8 GB | 4 GB | ⭐⭐⭐⭐ |
| Llama 3.2 3B | 2.0 GB | 4 GB | ⭐⭐⭐⭐ |
| DeepSeek R1 8B | 4.5 GB | 8 GB | ⭐⭐⭐⭐⭐ |
| Gemma 4 4B | 2.5 GB | 6 GB | ⭐⭐⭐⭐ |

## 📁 Estructura

```
DocChat/
├── run.py              # Lanzador
├── docchat/
│   ├── __init__.py
│   ├── engine.py       # Motor RAG (documentos, embeddings, búsqueda)
│   └── ui.py           # Interfaz de escritorio (PyQt6)
└── README.md
```

## 🛠️ Tecnologías

| Tecnología | Para qué |
|-----------|---------|
| **Python 3** | Lenguaje base |
| **PyQt6** | Interfaz de escritorio nativa |
| **LM Studio** | Inferencia de IA local |
| **numpy** | Cálculos vectoriales |
| **pypdf** | Lectura de PDFs |
| **python-docx** | Lectura de Word |
| **httpx** | Comunicación con LM Studio |

## 📊 ¿Por qué este proyecto?

| Aspecto | Lo que demuestra |
|---------|-----------------|
| **RAG** | Técnica más demandada en 2026 |
| **Python** | Código limpio y modular |
| **UI desktop** | PyQt6, no Electron (ligero) |
| **IA local** | Modelos sin depender de APIs |
| **Producto completo** | De principio a fin |

## 📄 Licencia

MIT — Haz lo que quieras con este código.

---

**¿Preguntas? Abre un issue o contribuye.**
