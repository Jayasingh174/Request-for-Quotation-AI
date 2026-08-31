from pydantic import BaseModel
from typing import List, Dict, Any


class RFQRequest(BaseModel):
    file_path: str          # 🔧 FIX: was file_name — upload_router.py needs a resolvable path


class RFQResponse(BaseModel):
    status: str              # 🔧 FIX: was bom/specifications/drawing_info — didn't match handler's return
    message: str
    data: Dict[str, Any]
