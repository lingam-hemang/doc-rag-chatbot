# Doc API ChatBot

A Django-powered document chatbot. Upload PDFs, Word docs, text files, and images, then ask questions about their content. Uses local LLMs via Ollama and LangChain with a RAG (Retrieval-Augmented Generation) pipeline. Includes a built-in web UI served directly by Django — no separate frontend server needed.

## Features

- Web UI at `http://127.0.0.1:8000/` — dark-themed chat interface
- Upload documents via drag-and-drop or file picker
- Ask questions about uploaded documents with full conversation memory
- RAG pipeline: Chroma vector store + Ollama LLMs
- OCR support for scanned PDFs and images (EasyOCR)
- Model switcher — change the active Ollama model from the UI
- Per-file delete with automatic vector DB rebuild
- Persistent chat history and timestamped vector DB snapshots
- REST API for all operations

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Django 5.2.3 + Django REST Framework |
| UI | Vanilla HTML/CSS/JS (served by Django) |
| LLM orchestration | LangChain, LangChain-Ollama |
| Vector store | Chroma (via LangChain-Chroma) |
| Local LLM runtime | Ollama (default model: `mistral`) |
| PDF parsing | PyMuPDF (fitz) |
| Word parsing | python-docx |
| OCR | EasyOCR + Pillow |
| Database | SQLite3 |

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai) installed and running
- At least one model pulled in Ollama (e.g. `ollama pull mistral`)

## Installation

```bash
# Navigate to the project directory
cd "doc-rag-chatbot"

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install Django==5.2.3 djangorestframework \
    langchain langchain-chroma langchain-ollama \
    PyMuPDF python-docx easyocr pillow numpy

# Apply migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser to use the UI.
The API is available at `http://127.0.0.1:8000/api/`.

## Using the UI

1. **Upload documents** — drag files onto the left sidebar or click to browse. Supported: `.pdf`, `.docx`, `.txt`, `.png`, `.jpg`, `.jpeg`.
2. **Wait for indexing** — files are processed and embedded into the vector DB automatically.
3. **Ask questions** — type in the chat input and press Enter. The bot answers using content from your documents.
4. **Switch models** — use the dropdown in the top bar to change the active Ollama model.
5. **Delete files** — click the ✕ button next to any file in the sidebar. The vector DB rebuilds automatically.

## API Reference

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/get_response/` | Ask a question about uploaded documents |

**Request body:**
```json
{ "question": "What is this document about?" }
```

**Response:**
```json
{ "question": "...", "response": "..." }
```

---

### File Management

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload_file/` | Upload one or more files |
| `GET` | `/api/list_files/` | List all uploaded files by type |
| `GET` | `/api/get_file/?filename=<name>` | Download a specific file |
| `DELETE` | `/api/delete_file/?filename=<name>` | Delete a file and rebuild the vector DB |

**Upload example:**
```bash
curl -X POST http://127.0.0.1:8000/api/upload_file/ \
  -F "file=@document.pdf" \
  -F 'rename={"document": "my_document"}'
```

The optional `rename` field is a JSON object mapping original filename (without extension) to a new name.

---

### Model Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/list_models/` | List available Ollama models |
| `GET` | `/api/current_model/` | Get the currently active model |
| `POST` | `/api/select_model/?model_name=<name>` | Switch the active model |
| `POST` | `/api/add_model/?model_name=<name>` | Pull and add a new Ollama model |
| `DELETE` | `/api/delete_model/?model_name=<name>` | Remove an Ollama model |

---

## Project Structure

```
Project 1 (Doc API ChatBot)/
├── manage.py
├── db.sqlite3
├── llm_chat.ipynb                  # Jupyter notebook for manual testing
├── Project_1/                      # Django project configuration
│   ├── settings.py
│   └── urls.py
├── myapi/                          # Django app
│   ├── views.py                    # All API endpoints + UI view
│   ├── urls.py                     # API route definitions
│   ├── templates/
│   │   └── myapi/
│   │       └── index.html          # Web UI (single-page chat interface)
│   └── readers/                    # Document loader modules (unused — see ChatBot_functions)
├── ChatBot_functions/              # Core chatbot logic
│   ├── constants.py                # Paths and model configuration
│   ├── chat_helpers.py             # LLM chain, RAG pipeline, chat history, vector DB
│   ├── PDF_Reader.py               # PDF text extraction + OCR fallback
│   ├── Word_Reader.py              # DOCX paragraph extraction
│   ├── Text_Reader.py              # Plain text loading
│   └── Image_Reader.py             # Image OCR
├── ChatBot_Files/
│   ├── Chat_History/               # JSON chat session history + snapshots
│   └── VectorDB/                   # Chroma vector store (current + snapshots)
└── files/                          # Uploaded document storage
    ├── staging/                    # Temporary area during upload processing
    ├── pdfs/
    ├── docs/
    ├── txts/
    └── images/
```

## How It Works

### Document Upload Flow

```
File upload
  → Validate file type & check for duplicates
  → Save to staging/
  → Extract text (PDF / DOCX / TXT / OCR for images and scanned PDFs)
  → Split into chunks (1500 chars, 150 overlap)
  → Embed with OllamaEmbeddings and index into Chroma
  → Snapshot current vector DB and chat history
  → Move files from staging/ to permanent storage
  → Return saved/error file lists
```

### Chat (RAG) Flow

```
User question (POST /api/get_response/)
  → Load Chroma vector store
  → Load chat history from current.json
  → Build ConversationalRetrievalChain (LLM + retriever + memory)
  → Retrieve relevant document chunks
  → LLM generates answer with context + history
  → Save updated chat history
  → Return response
```

## Configuration

Key settings in `ChatBot_functions/constants.py`:

```python
MODEL = 'mistral'                   # Active Ollama model (updated by select_model API)
BASE_DATA_DIR     = ".../files"
STAGING_FOLDER    = ".../files/staging"
CHAT_HISTORY_DIR  = ".../ChatBot_Files/Chat_History"
BASE_VECTORDB_DIR = ".../ChatBot_Files/VectorDB"
```

All paths are resolved relative to `os.getcwd()`, so run `manage.py` from the project root.

## Notes

- Ollama must be running locally before starting the server (`ollama serve`).
- Switching models via the UI updates `constants.py` on disk; the new model is used from the next request onwards.
- Chat history and vector DB snapshots accumulate in `ChatBot_Files/` — clean them up manually if disk space is a concern.
- No authentication is implemented — intended for local/development use only.
