from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    file_type: str
    uploaded_at: datetime
    chunk_count: int
