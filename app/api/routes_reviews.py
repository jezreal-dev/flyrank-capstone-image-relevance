"""API routes for human review workflow: approve, reject, inspect."""
from typing import List
from fastapi import APIRouter, HTTPException
from app.models.matching_schema import ReviewActionRequest, ReviewActionResponse
from app.services.review_service import review_service

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

@router.post("", response_model=ReviewActionResponse, status_code=201)
def submit_review_decision(payload: ReviewActionRequest):
    try:
        decision = review_service.record_decision(
            suggestion_id=payload.suggestion_id,
            decision=payload.decision,
            reviewer_notes=payload.reviewer_notes
        )
        return decision
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", status_code=200)
def list_review_history():
    return review_service.get_review_history()
