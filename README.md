# RFQ AI System: Engineering Analysis & RAG Pipeline

A powerful AI-driven system designed to process Request for Quotation (RFQ) documents. It cross-references Bill of Quantities (Excel), Technical Specifications (PDF), and Engineering Drawings (CAD/DWG) to detect conflicts and provide intelligent answers.

## 🚀 Features

- **Hybrid RAG Pipeline:** Combines FAISS (Vector Search) and BM25 (Keyword Search) for high-accuracy retrieval.
- **Multi-Format Parsing:**
  - **Excel (BOQ):** Row-by-row fuzzy matching for item descriptions and quantities.
  - **CAD (DWG/DXF):** Extraction of layers, blocks, and technical annotations.
  - **PDF/Docx:** Technical specification and Bill of Materials extraction.
- **Engineering Conflict Engine:** Automatically detects quantity discrepancies for the same item across drawings, specs, and BOQs.
- **Interactive UI:** Real-time chat with document grounding and source attribution.

---

## 🛠️ Setup & Installation

### 1. Prerequisites

- Python 3.9+
- An OpenAI API key
- **ODA File Converter** — only required if you plan to upload `.dwg` files (not needed for `.dxf`, PDF, DOCX, Excel, or CSV). [Download here](https://www.opendesign.com/guestfiles/oda_file_converter). Note its install path — you'll need it in step 4.

### 2. Upgrade Pip

```bash
python -m pip install --upgrade pip
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configuration

Create a `.env` file in the project root — **never** commit this file or put real credentials directly in `app/config.py`:

```env
OPENAI_API_KEY=your_api_key_here

# Only needed if you'll upload .dwg files:
ODA_PATH=/path/to/ODAFileConverter

# Optional — all have working defaults in app/config.py:
# CHUNK_SIZE=1000
# CHUNK_OVERLAP=200
# EMBEDDING_MODEL=text-embedding-3-large
# OPENAI_MODEL=gpt-4o-mini
# TOP_K=8
# MAX_CONTEXT_CHARS=12000
```

`OPENAI_API_KEY` is the only required variable — the app fails to start without it.

---

## ⚡ Execution

```bash
uvicorn app.main:app --reload --port 8000
```

- **API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Frontend UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 📂 Project Structure

```text
├── app/
│   ├── brain/           # AI Core (Vector Store, Chunking, Embeddings, LLM Service)
│   ├── extraction/       # Structured data extraction (BOM, Specs, Tables) from parsed text
│   ├── pipeline/         # Orchestration (RFQ Pipeline, Conflict Engine wiring)
│   ├── routers/           # API Endpoints (Upload, Query, Quote, Export, Documents)
│   ├── services/          # Document parsers (PDF, DOCX, Excel, CSV, Text, CAD)
│   ├── models/             # Pydantic Data Models
│   ├── web/                 # Frontend Assets (HTML/JS/CSS)
│   └── main.py               # FastAPI Entry Point
├── uploads/              # Uploaded RFQ files — persisted, not auto-cleaned
├── vectorstore/          # Persistent FAISS index + document store
├── temp_dxf/               # Intermediate DWG→DXF conversion output
├── requirements.txt
└── README.md
```

---

## 🤖 Example Queries

- "List all items from the BOQ with their quantities."
- "Are there any conflicts between the CAD drawings and the BOQ?"
- "What are the fire safety standards required by the specifications?"
