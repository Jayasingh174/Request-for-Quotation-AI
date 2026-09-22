import os
import logging
from typing import List, Dict, Any, Optional

from app.services.pdf_service import extract_pdf
from app.services.docx_service import extract_docx
from app.services.csv_service import extract_csv
from app.services.excel_service import extract_boq_data
from app.services.text_service import extract_text
from app.services.cad_service import extract_dwg, parse_dxf, summarize_dxf

from app.utils.fuzzy_match import get_fuzzy_val

from app.extraction.bom_extractor import extract_bom
from app.extraction.spec_extractor import extract_specs
from app.extraction.table_extractor import extract_tables

from app.config import DWG_TEMP_DIR

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".csv", ".xlsx", ".xls", ".txt", ".dwg", ".dxf"
}


def process_document(file_path: str) -> Dict[str, Any]:
    """
    Pure extraction — no chunking, embedding, or vector storage here.
    Returns raw text plus any structured data (BOQ rows, CAD entities) for
    downstream use. Chunking/embedding/storage is the RAG layer's job
    (see app/rag/ingestion_service.py).

    Note: no longer async — nothing in this function awaits anything now
    that embed_texts() has moved out.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        raise ValueError("File exceeds maximum allowed size (10MB)")

    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    try:
        clean_text = ""
        pre_chunked: Optional[List[str]] = None
        boq_data: Optional[list] = None
        cad_data: Optional[dict] = None
        cad_summary: Optional[str] = None

        # 1️⃣ EXCEL (BOQ Handling) — row-level formatting is extraction
        # logic (tied to get_fuzzy_val/column detection), not generic
        # RAG chunking, so it stays here. Each formatted row becomes one
        # embedding unit downstream — that's why pre_chunked is set.
        if ext in [".xlsx", ".xls"]:
            boq_data = extract_boq_data(file_path)

            if not boq_data:
                raise ValueError("No data extracted from Excel")

            rows: List[str] = []
            for row in boq_data:
                if not row or not isinstance(row, dict):
                    continue

                item = get_fuzzy_val(row, ["Item", "Item No", "S.No", "ID", "No."])
                desc = get_fuzzy_val(row, ["Material", "Description", "Item Description", "Name", "Spec"])
                qty = get_fuzzy_val(row, ["Quantity", "Qty", "Qty.", "Amount"])
                unit = get_fuzzy_val(row, ["Unit", "UOM", "Unit of Measure"])

                if not desc and not qty:
                    continue

                rows.append(f"Item {item}: {desc} | Qty: {qty} {unit}")

            if not rows:
                raise ValueError("No valid BOQ rows extracted")

            clean_text = "\n".join(rows)
            pre_chunked = rows
            logger.info(f"📊 Excel processed → {len(rows)} BOQ rows")

        # 2️⃣ OTHER FILE TYPES — raw text only; chunking happens in the RAG layer
        else:
            if ext == ".pdf":
                raw = extract_pdf(file_path)
            elif ext == ".docx":
                raw = extract_docx(file_path)
            elif ext == ".csv":
                raw = extract_csv(file_path)
            elif ext == ".txt":
                raw = extract_text(file_path)
            elif ext == ".dwg":
                raw = extract_dwg(file_path, DWG_TEMP_DIR)
                cad_data = raw.get("parsed_entities") if isinstance(raw, dict) else None
                cad_summary = raw.get("summary") if isinstance(raw, dict) else None
            elif ext == ".dxf":
                cad_data = parse_dxf(file_path)
                cad_summary = summarize_dxf(cad_data)
                raw = {"summary": cad_summary, "text_chunks": []}
            else:
                raw = ""

            if isinstance(raw, dict):
                text_chunks = raw.get("text_chunks", [])
                summary = raw.get("summary", "")
                clean_text = f"{summary}\n\n{' '.join(text_chunks)}"
            else:
                clean_text = str(raw)

            clean_text = clean_text.strip()

            if len(clean_text) < 10:
                raise ValueError("No meaningful text extracted")

            logger.info(f"📄 Text extracted → {len(clean_text)} characters")

        return {
            "text": clean_text,
            "pre_chunked": pre_chunked,   # set only for Excel; None otherwise
            "boq_data": boq_data,
            "cad_data": cad_data,
            "cad_summary": cad_summary,
        }

    except Exception as e:
        logger.error(f"❌ Document extraction failed: {file_path} | {e}", exc_info=True)
        raise RuntimeError(f"Document extraction failed: {e}") from e


def process_rfq(file_path: str) -> Dict[str, Any]:
    """
    Extraction only — structured BOM/specs/tables on top of process_document().
    Does NOT store anything in the vector store. Caller must separately call
    app.rag.ingestion_service.ingest_document() if retrieval is needed.
    """
    try:
        doc_result = process_document(file_path)
        text = doc_result.get("text")

        if not text:
            raise ValueError("No text extracted from document")

        bom = extract_bom(text)
        specs = extract_specs(text)
        tables = extract_tables(text)

        filename = os.path.basename(file_path)

        return {
            "status": "success",
            "source_file": filename,
            "bom": bom,
            "specifications": specs,
            "tables": tables,
            "text": text,                              # 🔧 kept so the caller can ingest it
            "pre_chunked": doc_result.get("pre_chunked"),
            "boq_data": doc_result.get("boq_data"),
            "cad_entities": doc_result.get("cad_data"),
            "cad_summary": doc_result.get("cad_summary"),
            "message": "Document extracted. Call ingest_document() to index it for search."
        }

    except Exception as e:
        logger.error(f"❌ RFQ extraction failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
