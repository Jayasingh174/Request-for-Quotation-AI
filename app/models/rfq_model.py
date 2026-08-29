from pydantic import BaseModel
from typing import List


class RFQRequest(BaseModel):
    file_name: str


class RFQResponse(BaseModel):
    bom: List[str]
    specifications: List[str]
    drawing_info: str