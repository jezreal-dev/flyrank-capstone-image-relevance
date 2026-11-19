"""Pydantic schemas for matching engine, Mismatch Guard decisions, and review API."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class GuardDecision(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED_CATEGORY_MISMATCH = "REJECTED_CATEGORY_MISMATCH"
    REJECTED_LOW_CONFIDENCE = "REJECTED_LOW_CONFIDENCE"
    REJECTED_LOW_SIMILARITY = "REJECTED_LOW_SIMILARITY"

class SuggestionItem(BaseModel):
    id: str
    image_id: str
    image_url: str
    image_caption: str
    image_subject: str
    image_category: str
    confidence: float
    similarity_score: float
    guard_decision: GuardDecision
    explanation: str
    rank: int

class PostSuggestionsResponse(BaseModel):
    post_id: str
    post_title: str
    status: str = Field(..., description="'MATCH_FOUND' or 'NO_CONFIDENT_MATCH'")
    top_recommendation: Optional[SuggestionItem] = None
    all_candidates: List[SuggestionItem] = []
    explanation: str

class ReviewDecisionEnum(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ReviewActionRequest(BaseModel):
    suggestion_id: str
    decision: ReviewDecisionEnum
    reviewer_notes: Optional[str] = None

class ReviewActionResponse(BaseModel):
    id: str
    suggestion_id: str
    decision: ReviewDecisionEnum
    reviewer_notes: Optional[str] = None
    decided_at: str
