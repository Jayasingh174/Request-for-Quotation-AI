import logging
# Import your newly created vector store instance
from app.brain.vector_service import vector_store 
# Import the ask_llm function we perfected earlier
from app.brain.llm_service import ask_llm
# Import the Excel parser from my previous message
from app.extraction.excel_parser import extract_boq_as_text 

logger = logging.getLogger(__name__)

async def get_openai_embedding(text: str) -> list:
    """Helper function to get embeddings (assuming you are using OpenAI text-embedding-3-small/large)"""
    from app.config import client # assuming your AsyncOpenAI client is here
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small" # Or whatever model your dimension=3072 uses
    )
    return response.data[0].embedding


async def process_user_message(user_question: str, uploaded_boq_path: str = None) -> str:
    """
    The main routing function. Put this right behind your API endpoint.
    """
    user_question_lower = user_question.lower()
    context = ""

    # ==========================================
    # ROUTE A: THE BOQ BYPASS (For "List all", "Summarize")
    # ==========================================
    # If the user is asking a broad question about the spreadsheet, skip the Vector DB!
    if "all" in user_question_lower and ("boq" in user_question_lower or "items" in user_question_lower):
        logger.info("Triggered BOQ Bypass Router. Loading entire Excel file directly.")
        
        if uploaded_boq_path:
            # Feed the entire formatted Excel sheet directly into the 128k context window
            context = extract_boq_as_text(uploaded_boq_path)
        else:
            return "Please upload the BOQ Excel file first so I can list all items."

    # ==========================================
    # ROUTE B: HYBRID VECTOR SEARCH (For specific questions)
    # ==========================================
    else:
        logger.info("Triggered Hybrid Vector Search.")
        
        # 1. Get the mathematical representation of the user's question
        query_embedding = await get_openai_embedding(user_question)

        # 2. Use your custom VectorService to find the best matching chunks!
        search_results = vector_store.hybrid_search(
            query=user_question, 
            query_embedding=query_embedding, 
            top_k=5
        )

        if not search_results:
            return "Information not available in the documents."

        # 3. Extract the actual text from the dictionaries your service returns
        # Remember, your hybrid_search returns: [{"text": "...", "hash": "...", ...}]
        context_chunks = [doc["text"] for doc in search_results]
        
        # Mash them together with a clear separator
        context = "\n\n---\n\n".join(context_chunks)

    # ==========================================
    # FINAL STEP: CALL THE LLM
    # ==========================================
    # Now that we have the perfect context (either the whole BOQ or the top 5 chunks), 
    # we hand it off to your ask_llm function.
    return await ask_llm(user_question, context)