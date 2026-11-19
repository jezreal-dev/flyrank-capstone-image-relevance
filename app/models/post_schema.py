"""Pydantic schemas for editorial articles/posts."""
from typing import Optional
from pydantic import BaseModel, Field

class PostCreateRequest(BaseModel):
    id: Optional[str] = None
    title: str = Field(..., min_length=3)
    slug: Optional[str] = None
    content: str = Field(..., min_length=10)
    target_subject: Optional[str] = Field(None, description="Expected primary subject (e.g. 'red fox')")

class PostResponse(BaseModel):
    id: str
    title: str
    slug: str
    content: str
    target_subject: Optional[str] = None
    status: str
    created_at: str
