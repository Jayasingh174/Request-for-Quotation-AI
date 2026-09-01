from fastapi import APIRouter, HTTPException
import logging

from app.pipeline.query_pipeline import ask_rfq
from app.models.query_model import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])


# ==========================================
# 📦 STANDARD QUERY (JSON RESPONSE)
# ==========================================
@router.post("/ask", response_model=QueryResponse)
async def query_rfq(request: QueryRequest):
    """
    Takes a user question, searches the Vector Store,
    and returns an AI-generated answer with sources.
    """
    try:
        logger.info(f"Incoming user query: {request.question}")

        # 🔧 FIX: top_k and boq_file_path were previously accepted by the
        # request model but silently dropped — now actually passed through.
        result = await ask_rfq(
            question=request.question,
            top_k=request.top_k,
            boq_file_path=request.boq_file_path
        )

        return result

    except Exception as e:
        logger.error(f"❌ API Query Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )
