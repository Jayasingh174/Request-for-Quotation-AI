from fastapi import APIRouter, HTTPException

from app.brain.document_upload import get_documents, remove_document

router = APIRouter(prefix="/documents")


@router.get("/")
def list_documents():
    return {"documents": get_documents()}


@router.delete("/{filename}")
def delete_document(filename: str):
    removed = remove_document(filename)

    if not removed:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")

    return {"status": "deleted", "filename": filename}
