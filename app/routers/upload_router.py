from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.models.rfq_model import RFQRequest, RFQResponse
from typing import List
import os

from app.brain.document_upload import add_document
from app.pipeline.rfq_pipeline import process_rfq  # 🔧 FIX: document_service.py deleted, process_rfq lives here now
from app.pipeline.quotation_pipeline import process_rfq_bundle
from app.config import UPLOAD_DIR

router = APIRouter(prefix="/upload")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------------------------------
# 1. Single File Process
# ---------------------------------------------------------
@router.post("/process", response_model=RFQResponse)
async def process_rfq_request(request: RFQRequest):
    """
    Process uploaded RFQ documents and DWG drawings.
    """
    try:
        file_path = request.file_path

        result = await process_rfq(file_path)

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return RFQResponse(
            status="success",
            message="RFQ processed successfully",
            data=result
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RFQ processing failed: {str(e)}"
        )


# ---------------------------------------------------------
# 2. Multi-File Bundle Upload (Phase 3)
# ---------------------------------------------------------
@router.post("/bundle")
async def upload_rfq_bundle(
    project_name: str = Form("New RFQ Project"),
    files: List[UploadFile] = File(...)
):
    """
    Receives a bundle of RFQ files, saves them, and runs the cross-file
    engineering conflict detection pipeline.
    """
    saved_filepaths = []

    for file in files:
        filepath = os.path.join(UPLOAD_DIR, file.filename)

        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        saved_filepaths.append(filepath)

        add_document(file.filename)
        print(f"Added to bundle: {filepath}")

    print(f"Processing bundle for {project_name} with {len(files)} files...")

    pipeline_result = await process_rfq_bundle(
        project_name=project_name,
        file_paths=saved_filepaths
    )

    return pipeline_result
