import os
import logging
from typing import Dict, Any, List

from app.brain.embedding_service import embed_query
from app.brain.llm_service import ask_llm

# 🔥 NEW: Import the unified VectorService instance
from app.brain.vector_service import vector_store 

logger = logging.getLogger(__name__)

def safe_get(d: dict, key: str, default=None):
    try:
        return d.get(key, default)
    except Exception:
        return default

async def ask_rfq(question: str, top_k: int = 8) -> Dict[str, Any]:
    """
    Full RFQ query pipeline
    """
    try:
        logger.info("RFQ Query: %s", question)

        # --------------------------------------------------
        # 1️⃣ Generate embedding
        # --------------------------------------------------
        embedding = await embed_query(question)

        # --------------------------------------------------
        # 2️⃣ Hybrid retrieval (USING NEW CLASS)
        # --------------------------------------------------
        # 🔥 Call the hybrid_search method on our vector_store instance
        results = vector_store.hybrid_search(
            query=question, 
            query_embedding=embedding, 
            top_k=top_k
        ) or []

        logger.info(f"Retrieved results: {len(results)}")

        if not results:
            return {
                "question": question,
                "answer": "No relevant information found in the documents.",
                "sources": [],
                "chunks_used": 0,
                "context_preview": ""
            }

        sources: List[str] = []
        context_parts: List[str] = []
        seen_texts = set()

        # --------------------------------------------------
        # 3️⃣ Process results (dedupe + extract)
        # --------------------------------------------------
        for r in results:
            text = safe_get(r, "text", "").strip()

            if not text or text in seen_texts:
                continue

            seen_texts.add(text)
            context_parts.append(text)

            meta = safe_get(r, "metadata", {}) or {}

            source_path = (
                meta.get("source")
                or meta.get("file")
                or meta.get("file_path")
                or meta.get("file_name") # Catching the key we used in document_service
            )

            if isinstance(source_path, str):
                filename = os.path.basename(source_path.strip())

                if filename and filename.lower() not in ["unknown", "none"]:
                    if filename not in sources:
                        sources.append(filename)

        # --------------------------------------------------
        # 4️⃣ Smart context building
        # --------------------------------------------------
        MAX_CONTEXT_CHARS = 4000
        context = ""
        chunks_used = 0

        for chunk in context_parts:
            if len(context) + len(chunk) > MAX_CONTEXT_CHARS:
                break
            context += chunk + "\n\n"
            chunks_used += 1

        # --------------------------------------------------
        # 5️⃣ Weak context guard (ADJUSTED FOR BOQ)
        # --------------------------------------------------
        # Lowered to 20 characters to allow for short, single-row BOQ answers.
        # If it's literally empty, then we block it.
        if len(context.strip()) < 20: 
            logger.warning("⚠️ Weak context detected")

            return {
                "question": question,
                "answer": "Not enough relevant information found in documents.",
                "sources": sources,
                "chunks_used": chunks_used,
                "context_preview": context[:500]
            }

        logger.info(f"Context size: {len(context)} | Chunks: {chunks_used}")

        # --------------------------------------------------
        # 6️⃣ Ask LLM
        # --------------------------------------------------
        answer = await ask_llm(question, context)

        logger.info("✅ Answer generated")

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "chunks_used": chunks_used,
            "context_preview": context[:500]
        }

    except Exception as e:
        logger.exception("❌ Query processing failed")

        return {
            "question": question,
            "answer": "I encountered an error while analyzing the documents.",
            "error": str(e),
            "sources": [],
            "chunks_used": 0,
            "context_preview": ""
        }