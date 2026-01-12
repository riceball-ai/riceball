from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID

class RetrievalChunk(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: Optional[float] = None
    kb_id: UUID
    doc_id: Optional[UUID] = None

class RetrievalResult(BaseModel):
    query: str
    chunks: List[RetrievalChunk]
