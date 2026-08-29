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

        # 🔥 AWAIT the pipeline we built! 
        # This returns our perfectly formatted dictionary.
        result = await ask_rfq(question=request.question)

        # Assuming your QueryResponse model matches the keys we output:
        # { question, answer, sources, chunks_used, context_preview }
        return result

    except Exception as e:
        logger.error(f"❌ API Query Error: {str(e)}")
        # 🔥 Raise an HTTPException so FastAPI handles the error gracefully 
        # without failing Pydantic validation!
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )