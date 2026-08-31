import pandas as pd
import logging
from openai import AsyncOpenAI

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
# Used by query_pipeline.ask_rfq() as a "BOQ bypass" for
# broad questions (e.g. "list all BOQ items") that a top-k
# vector search would truncate.
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
            desc_keys = [k for k in row_dict.keys() if 'desc' in k.lower() or 'item' in k.lower()]
            if desc_keys and not str(row_dict[desc_keys[0]]).strip():
                continue

            row_details = [f"{k}: {v}" for k, v in row_dict.items() if str(v).strip() and k != "Unknown_Column"]
            boq_text_output.append(" | ".join(row_details))

    return "\n".join(boq_text_output)


# ==========================================
# 2. LLM SERVICE
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
