"""Pydantic schemas for image ingestion, structured tags, and confidence validation."""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class ImageTagSchema(BaseModel):
    """Structured vision classification metadata contract."""
    subject: str = Field(..., description="Primary subject of the image (e.g. 'red fox')", min_length=1)
    category: str = Field(..., description="Broader taxonomic category (e.g. 'wildlife', 'technology')", min_length=1)
    attributes: List[str] = Field(default_factory=list, description="Visual descriptors or traits")
    caption: str = Field(..., description="Descriptive sentence summarizing the image content", min_length=5)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model self-confidence score in [0.0, 1.0]")

    @field_validator("subject", "category")
    @classmethod
    def clean_strings(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only")
        return cleaned

class ImageCreateRequest(BaseModel):
    id: Optional[str] = None
    url: str = Field(..., min_length=5)
    filename: str = Field(..., min_length=3)
    structured_tags: Optional[ImageTagSchema] = None

class ImageResponse(BaseModel):
    id: str
    url: str
    filename: str
    status: str
    subject: Optional[str] = None
    category: Optional[str] = None
    attributes: List[str] = []
    caption: Optional[str] = None
    confidence: Optional[float] = None
    is_flagged: bool = False
    created_at: str

class BatchProcessRequest(BaseModel):
    image_ids: Optional[List[str]] = None
    force_reprocess: bool = False

class BatchJobStatusResponse(BaseModel):
    job_id: str
    status: str
    total_items: int
    processed_items: int
    flagged_items: int
    failed_items: int
    completed_at: Optional[str] = None
