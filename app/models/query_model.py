from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    question: str
    top_k: int = 3
    boq_file_path: Optional[str] = None  # 🔧 FIX: optional — enables the BOQ bypass in ask_rfq()


class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
