from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.models.rfq_model import RFQRequest, RFQResponse
from typing import List
import os

# --- Import your existing services ---
from app.brain.document_upload import add_document

# --- Import your NEW Phase 3 Pipeline ---
from app.pipeline.rfq_pipeline import process_rfq
from app.pipeline.quotation_pipeline import process_rfq_bundle # Assuming this is the correct path

router = APIRouter(prefix="/upload")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. Single File Process
# ---------------------------------------------------------
@router.post("/process", response_model=RFQResponse)
async def process_rfq_request(request: RFQRequest): # 🔥 Added `async`
    """
    Process uploaded RFQ documents and DWG drawings.
    """
    try:
        file_path = request.file_path

        # 🔥 AWAIT the async pipeline!
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
    
    # Step 1: Securely save all uploaded files to disk
    for file in files:
        filepath = os.path.join(UPLOAD_DIR, file.filename)
        
        # 🔥 Async-safe file saving (Prevents blocking FastAPI's event loop)
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        saved_filepaths.append(filepath)
        
        # Assuming add_document is synchronous. If it's async, add `await`
        add_document(file.filename) 
        print(f"Added to bundle: {filepath}")

    # Step 2: Pass the entire list of files to our orchestrator
    print(f"Processing bundle for {project_name} with {len(files)} files...")
    
    # 🔥 AWAIT the heavy conflict detection pipeline
    pipeline_result = await process_rfq_bundle(
        project_name=project_name, 
        file_paths=saved_filepaths
    )

    # Step 3: Return the complete engineering analysis to the frontend
    return pipeline_result