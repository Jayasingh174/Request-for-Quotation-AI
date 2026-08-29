from fastapi import APIRouter
from app.brain.document_upload import get_documents

router = APIRouter(prefix="/documents")

@router.get("/")
def list_documents():
    return {"documents": get_documents()}