import pandas as pd
import logging

logger = logging.getLogger(__name__)

def extract_boq_data(file_path: str) -> list:
    """
    Reads an Excel BOQ, dynamically finds the header row, and returns 
    a list of semantically formatted text chunks for better RAG retrieval.
    """
    try:
        sheets = pd.read_excel(file_path, sheet_name=None, header=None) # Don't assume row 0 is header
    except Exception as e:
        logger.exception(f"Failed to read Excel file {file_path}")
        raise ValueError(f"Failed to read Excel file: {e}")

    all_semantic_rows = []

    for sheet_name, df in sheets.items():
        df = df.dropna(how='all').dropna(axis=1, how='all')
        if df.empty:
            continue

        # 1. Find the real header row dynamically
        # Look for a row containing typical BOQ keywords
        header_row_idx = 0
        for idx, row in df.iterrows():
            row_text = ' '.join([str(val).lower() for val in row.values])
            if any(keyword in row_text for keyword in ['description', 'item', 'qty', 'quantity', 'unit']):
                header_row_idx = idx
                break
        
        # 2. Reassign headers and drop the junk rows above it
        df.columns = df.iloc[header_row_idx].fillna("Unknown_Column").astype(str)
        df = df.iloc[header_row_idx + 1:] # Keep data below the header
        
        # 3. Clean up the data
        df = df.dropna(how='all') # Drop rows that are now empty
        df = df.fillna("")

        # 4. Convert to Semantic Text instead of raw dicts
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            
            # Skip rows where the main description is empty
            # (You might need to adjust 'Description' to match your actual BOQ column names)
            desc_keys = [k for k in row_dict.keys() if 'desc' in k.lower() or 'item' in k.lower()]
            if desc_keys and row_dict[desc_keys[0]] == "":
                continue

            # Create a human-readable string for the embedder
            semantic_string = f"[Sheet: {sheet_name}] "
            row_details = []
            for col_name, value in row_dict.items():
                if str(value).strip() != "" and col_name != "Unknown_Column":
                    row_details.append(f"{col_name}: {value}")
            
            semantic_string += " | ".join(row_details)
            all_semantic_rows.append(semantic_string)

    logger.info(f"📊 Extracted {len(all_semantic_rows)} semantic chunks from Excel.")
    
    return all_semantic_rows