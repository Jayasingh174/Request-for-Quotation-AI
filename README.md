# RFQ AI System: Engineering Analysis & RAG Pipeline

A powerful AI-driven system designed to process Request for Quotation (RFQ) documents. It cross-references Bill of Quantities (Excel), Technical Specifications (PDF), and Engineering Drawings (CAD/DWG) to detect conflicts and provide intelligent answers.

## 🚀 Features
- **Hybrid RAG Pipeline:** Combines FAISS (Vector Search) and BM25 (Keyword Search) for high-accuracy retrieval.
- **Multi-Format Parsing:** - **Excel (BOQ):** Row-by-row fuzzy matching for item descriptions and quantities.
  - **CAD (DWG/DXF):** Extraction of layers, blocks, and technical annotations.
  - **PDF/Docx:** Technical specification extraction with table support.
- **Engineering Conflict Engine:** Automatically detects discrepancies between drawings, specs, and price sheets.
- **Interactive UI:** Real-time chat with document grounding and source attribution.

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.9+
- OpenAI API Key

### 2. Upgrade Pip
First, ensure your package manager is up to date:
```bash
python -m pip install --upgrade pip
```

### 3. Install Dependencies
Install the required libraries:
```bash
pip install -r requirements.txt
```
*Note: If using `camelot-py`, ensure **Ghostscript** is installed on your OS.*

### 4. Configuration
Create a `.env` file or update `app/config.py` with your credentials:
```python
OPENAI_API_KEY = "your_api_key_here"
```

---

## ⚡ Execution

To start the backend server, run:
```bash
uvicorn app.main:app --reload --port 8000
```

- **API Documentation:** View the interactive Swagger UI at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Frontend UI:** Access the main dashboard at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 📂 Project Structure
```text
├── app/
│   ├── brain/           # AI Core (Vector Store, Embeddings, LLM Service)
│   ├── pipeline/        # Business Logic (RAG Pipeline, Conflict Engine)
│   ├── routers/         # API Endpoints (Upload, Query, Export)
│   ├── services/        # Document Parsers (PDF, Excel, CAD)
│   ├── models/          # Pydantic Data Models
│   ├── web/             # Frontend Assets (HTML/JS/CSS)
│   └── main.py          # FastAPI Entry Point
├── uploads/             # Temporary storage for uploaded RFQs
├── vectorstore/         # Persistent FAISS database
├── requirements.txt     # Project dependencies
└── README.md            # You are here!
```

---

## 🤖 Example Queries
- "List all items from the BOQ with their quantities."
- "Are there any conflicts between the CAD drawings and the BOQ?"
- "What are the fire safety standards required by the specifications?""# Request-for-Quotation" 
