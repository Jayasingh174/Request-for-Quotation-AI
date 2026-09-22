# app/pipeline/rfq_pipeline.py
import os
import logging
from typing import List, Dict, Any, Optional

from app.services.pdf_service import extract_pdf
from app.services.docx_service import extract_docx
from app.services.csv_service import extract_csv
from app.services.excel_service import extract_boq_data
from app.services.text_service import extract_text
from app.services.cad_service import extract_dwg, parse_dxf, summarize_dxf

# 🔧 FIX: app.brain, not app.rag — that split doesn't exist in this repo
from app.brain.chunk_service import chunk_text
from app.brain.embedding_service import embed_texts
from app.brain.vector_service import vector_store

from app.extraction.bom_extractor import extract_bom
from app.extraction.spec_extractor import extract_specs
from app.extraction.table_extractor import extract_tables

from app.utils.fuzzy_match import get_fuzzy_val
from app.config import DWG_TEMP_DIR

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".csv", ".xlsx", ".xls", ".txt", ".dwg", ".dxf"
}


async def process_rfq(file_path: str) -> Dict[str, Any]:
    """
    Complete RFQ pipeline, one function: extract → chunk → embed → store →
    structured extraction (BOM/specs/tables/CAD). This is the single source
    of truth — app/brain/document_service.py should be deleted, its logic
    now lives entirely here.
    """
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"File not found: {file_path}"}

    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        return {"status": "error", "message": "File exceeds maximum allowed size (10MB)"}

    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return {"status": "error", "message": f"Unsupported file type: {ext}"}

    try:
        chunks: List[str] = []
        clean_text = ""
        boq_data: Optional[list] = None
        cad_data: Optional[dict] = None
        cad_summary: Optional[str] = None

        if ext in [".xlsx", ".xls"]:
            boq_data = extract_boq_data(file_path)

            if not boq_data:
                raise ValueError("No data extracted from Excel")

            for row in boq_data:
                if not row or not isinstance(row, dict):
                    continue

                item = get_fuzzy_val(row, ["Item", "Item No", "S.No", "ID", "No."])
                desc = get_fuzzy_val(row, ["Material", "Description", "Item Description", "Name", "Spec"])
                qty = get_fuzzy_val(row, ["Quantity", "Qty", "Qty.", "Amount"])
                unit = get_fuzzy_val(row, ["Unit", "UOM", "Unit of Measure"])

                if not desc and not qty:
                    continue

                chunks.append(f"Item {item}: {desc} | Qty: {qty} {unit}")

            clean_text = "\n".join(chunks)
            logger.info(f"📊 Excel processed → {len(chunks)} BOQ chunks")

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

            raw_chunks = chunk_text(clean_text)
            chunks = [c.strip() for c in raw_chunks if c and len(c.strip()) > 20]

            logger.info(f"📄 Text processed → {len(chunks)} chunks")

        if not chunks:
            raise ValueError("No valid chunks generated")

        embeddings = await embed_texts(chunks)

        if embeddings is None or len(embeddings) == 0:
            raise ValueError("Embedding generation failed")

        filename = os.path.basename(file_path)

        vector_store.add_documents(
            chunks=chunks,
            embeddings=embeddings,
            source_filename=filename
        )

        logger.info(f"✅ Document indexed successfully: {filename}")

        bom = extract_bom(clean_text)
        specs = extract_specs(clean_text)
        tables = extract_tables(clean_text)

        return {
            "status": "success",
            "source_file": filename,
            "bom": bom,
            "specifications": specs,
            "tables": tables,
            "boq_data": boq_data,
            "cad_entities": cad_data,
            "cad_summary": cad_summary,
            "message": "Document extracted, indexed, and structured data parsed."
        }

    except Exception as e:
        logger.error(f"❌ RFQ processing failed: {file_path} | {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
