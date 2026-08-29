import pandas as pd
import logging
from openai import AsyncOpenAI

# Assuming your config is set up correctly
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS,
)

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# 1. THE EXCEL PARSER (Formats data for the LLM)
# ==========================================
def extract_boq_as_text(file_path: str) -> str:
    """Reads the BOQ and formats it as a single highly readable text block."""
    try:
        sheets = pd.read_excel(file_path, sheet_name=None, header=None)
    except Exception as e:
        logger.error(f"Failed to read BOQ file: {e}")
        return ""

    boq_text_output = []

    for sheet_name, df in sheets.items():
        df = df.dropna(how='all').dropna(axis=1, how='all')
        if df.empty:
            continue

        # Find the header row dynamically
        header_row_idx = 0
        for idx, row in df.iterrows():
            row_text = ' '.join([str(val).lower() for val in row.values])
            if any(keyword in row_text for keyword in ['description', 'item', 'qty', 'quantity', 'unit']):
                header_row_idx = idx
                break
        
        df.columns = df.iloc[header_row_idx].fillna("Unknown_Column").astype(str)
        df = df.iloc[header_row_idx + 1:].dropna(how='all').fillna("")

        boq_text_output.append(f"\n--- [BOQ Sheet: {sheet_name}] ---")
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            # Skip empty descriptions
            desc_keys = [k for k in row_dict.keys() if 'desc' in k.lower() or 'item' in k.lower()]
            if desc_keys and not str(row_dict[desc_keys[0]]).strip():
                continue

            # Format as: Description: Item Name | Qty: 5 | Unit: Nos
            row_details = [f"{k}: {v}" for k, v in row_dict.items() if str(v).strip() and k != "Unknown_Column"]
            boq_text_output.append(" | ".join(row_details))

    return "\n".join(boq_text_output)


# ==========================================
# 2. YOUR LLM SERVICE (Unchanged)
# ==========================================
async def ask_llm(question: str, context: str) -> str:
    """Calls OpenAI LLM with strict RAG grounding."""
    logger.info(f"Processing query. Context length: {len(context) if context else 0}")
    
    if not context or len(context.strip()) < 10:
        return "No relevant data found in uploaded documents."

    try:
        safe_context = context[:100000] 

        system_prompt = (
            "You are an expert RFQ Engineering Assistant.\n"
            "Answer strictly using the provided context. If the exact information is missing, "
            "state exactly: 'Information not available in the documents.'\n\n"
            "RULES:\n"
            "- If summarizing a Bill of Quantities (BOQ), use clear bullet points or markdown tables.\n"
            "- Be highly precise with quantities, measurements, and item names.\n"
            "- Do not use outside knowledge or make assumptions."
        )

        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{safe_context}\n\nQuestion: {question}"}
            ],
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS,
        )

        answer = response.choices[0].message.content
        return answer.strip() if answer and answer.strip() else "Information not available in the documents."

    except Exception as e:
        logger.error(f"LLM Integration Error: {str(e)}", exc_info=True)
        return "LLM processing failed."


# ==========================================
# 3. THE MAGIC ROUTER (Fixes the "List All" bug)
# ==========================================
async def process_user_message(user_question: str, boq_file_path: str = None) -> str:
    """
    This function decides HOW to build the context before calling the LLM.
    You will wire this up to your FastAPI/Flask route.
    """
    user_question_lower = user_question.lower()
    context = ""

    # ROUTE A: Broad BOQ questions (Bypass Vector DB)
    if "all" in user_question_lower and ("boq" in user_question_lower or "items" in user_question_lower):
        logger.info("Triggered BOQ Bypass Router. Loading entire Excel file directly.")
        if boq_file_path:
            context = extract_boq_as_text(boq_file_path)
        else:
            return "Please upload the BOQ file first."

    # ROUTE B: Standard Specific Questions (Use Vector DB)
    else:
        logger.info("Triggered Standard Vector Search.")
        # Replace this comment with your actual Vector DB search code!
        # Example: docs = my_vector_db.similarity_search(user_question, k=5)
        # context = "\n".join([doc.text for doc in docs])
        context = "Text from your PDF chunking goes here based on similarity."

    # Finally, pass the properly built context to your LLM
    return await ask_llm(user_question, context)