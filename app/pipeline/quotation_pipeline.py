import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

# ----- Services -----
from app.services.excel_service import extract_boq_data
from app.brain.conflict_engine import detect_conflicts
from app.pipeline.rfq_pipeline import process_rfq

logger = logging.getLogger(__name__)

def safe_int(val, default=1):
    try:
        # Strip out non-numeric characters before converting (e.g., "25 Nos" -> "25")
        num_str = re.sub(r"[^\d.]", "", str(val))
        return int(float(num_str)) if num_str else default
    except Exception:
        return default

def clean_item(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def normalize_entity(item, quantity, source, etype, path):
    return {
        "item": clean_item(item),
        "quantity": safe_int(quantity),
        "source": source,
        "type": etype,
        "file_path": path,
    }

def deduplicate_entities(entities):
    seen = set()
    unique = []
    for e in entities:
        if not isinstance(e, dict) or "item" not in e:
            continue
        key = (e["item"], e["type"], e["file_path"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique

def group_by_item(entities):
    grouped = defaultdict(list)
    for e in entities:
        if isinstance(e, dict) and "item" in e:
            grouped[e["item"]].append(e)
    return grouped

# --- HELPER: FUZZY MATCHER (Imported or redefined for safety) ---
def get_fuzzy_val(row_dict: dict, possible_keys: list) -> str:
    lower_row = {str(k).lower().strip(): v for k, v in row_dict.items() if k}
    for key in possible_keys:
        if key.lower() in lower_row and lower_row[key.lower()] is not None:
            return str(lower_row[key.lower()]).strip()
    return ""
# ----------------------------------------------------------------

# ==========================================
# MULTI-FILE RFQ ORCHESTRATOR
# ==========================================
async def process_rfq_bundle(project_name: str, file_paths: List[str]) -> Dict[str, Any]:
    logger.info("Starting Multi-File processing for project: %s", project_name)

    all_normalized_entities: List[Dict[str, Any]] = []
    processed_results: List[Dict[str, Any]] = []
    EXCEL_EXTS = {"xlsx", "xls"}

    for i, raw_path in enumerate(file_paths):
        path = Path(raw_path)
        filename = path.name

        try:
            logger.info("Processing %d/%d: %s", i + 1, len(file_paths), filename)

            if not path.exists() or path.stat().st_size == 0:
                raise ValueError("File not found or empty")

            ext = path.suffix.lower().lstrip(".")
            entities: List[Dict[str, Any]] = []

            # --------------------------------------------------
            # 🔥 STEP 1: EMBED EVERYTHING FIRST
            # By routing EVERYTHING through process_rfq, we guarantee 
            # Excel files get chunked and saved to the Chatbot's Vector Store.
            # --------------------------------------------------
            result = await process_rfq(str(path))
            
            if not result or result.get("status") == "error":
                raise ValueError(result.get("message", "Vector/Pipeline extraction error"))

            file_result: Dict[str, Any] = {
                "file": filename,
                "file_type": ext,
                "status": "processed",
                **{k: v for k, v in result.items() if k not in ["status", "entities"]}
            }

            # --------------------------------------------------
            # 🔥 STEP 2: EXTRACT ENTITIES FOR CONFLICT ENGINE
            # --------------------------------------------------
            
            # EXCEL HANDLING
            if ext in EXCEL_EXTS:
                boq_data = extract_boq_data(str(path))
                
                # boq_data should be a list of rows
                if isinstance(boq_data, list):
                    for row in boq_data:
                        if not row: continue
                        
                        item = get_fuzzy_val(row, ["Item", "Item No", "S.No", "ID"])
                        desc = get_fuzzy_val(row, ["Material", "Description", "Name"])
                        qty = get_fuzzy_val(row, ["Quantity", "Qty", "Amount"])
                        
                        # Use Description as fallback if Item ID is missing
                        entity_name = item if item else desc
                        
                        if entity_name and qty:
                            entities.append(normalize_entity(
                                entity_name, qty, f"BOQ ({filename})", "BOQ", str(path)
                            ))
                file_result["status"] = "processed as BOQ"

            # PDF / CAD HANDLING
            else:
                # CAD entities
                for entity in result.get("cad_entities", []) or []:
                    if isinstance(entity, dict):
                        entities.append(normalize_entity(
                            entity.get("item", "Unknown"), entity.get("qty"),
                            f"CAD ({filename})", "CAD", str(path)
                        ))

                # BOM entities
                for item in result.get("bom", []) or []:
                    if isinstance(item, dict):
                        entities.append(normalize_entity(
                            item.get("item", "Unknown"), item.get("quantity"),
                            f"Spec BOM ({filename})", "Spec BOM", str(path)
                        ))
                
                file_result["status"] = "processed as unstructured"

            # Store the extracted entities
            if not entities:
                file_result["status"] += " (no entities found)"
            
            file_result["entities"] = entities
            processed_results.append(file_result)
            all_normalized_entities.extend(entities)

        except Exception as e:
            logger.exception("Error processing file %s", filename)
            processed_results.append({
                "file": filename,
                "status": "error",
                "message": str(e),
                "entities": [],
            })

    # =====================
    # CLEAN, GROUP & DETECT
    # =====================
    all_normalized_entities = deduplicate_entities(all_normalized_entities)
    logger.info("Checking %d items for conflicts...", len(all_normalized_entities))

    try:
        conflict_report = detect_conflicts(all_normalized_entities)
    except Exception as e:
        logger.exception("Conflict detection failed")
        conflict_report = {"error": str(e)}

    # =====================
    # SUMMARY
    # =====================
    success_count = sum(1 for f in processed_results if "processed" in f["status"])
    error_count = sum(1 for f in processed_results if f["status"] == "error")

    return {
        "project_name": project_name,
        "files_processed": len(file_paths),
        "summary": {"success": success_count, "errors": error_count},
        "file_details": processed_results,
        "engineering_analysis": conflict_report,
    }