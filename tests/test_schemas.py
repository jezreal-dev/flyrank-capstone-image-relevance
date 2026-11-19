"""Tests for Pydantic schema validation and boundary enforcement."""
import pytest
from pydantic import ValidationError
from app.models.image_schema import ImageTagSchema, ImageCreateRequest
from app.models.matching_schema import GuardDecision, ReviewDecisionEnum

def test_image_tag_schema_valid():
    payload = {
        "subject": "Red Fox",
        "category": "Wildlife",
        "attributes": ["orange fur", "bushy tail"],
        "caption": "A red fox standing in an autumn forest",
        "confidence": 0.94
    }
    tag = ImageTagSchema(**payload)
    assert tag.subject == "red fox"  # lowercased by validator
    assert tag.category == "wildlife"
    assert tag.confidence == 0.94

def test_image_tag_schema_invalid_confidence():
    with pytest.raises(ValidationError):
        ImageTagSchema(
            subject="Fox",
            category="Wildlife",
            attributes=["fur"],
            caption="A fox in forest",
            confidence=1.5  # Invalid: must be <= 1.0
        )

def test_image_tag_schema_empty_fields():
    with pytest.raises(ValidationError):
        ImageTagSchema(
            subject="   ",  # Empty
            category="Wildlife",
            attributes=["fur"],
            caption="A fox in forest",
            confidence=0.9
        )

def test_image_tag_schema_short_caption():
    with pytest.raises(ValidationError):
        ImageTagSchema(
            subject="Fox",
            category="Wildlife",
            attributes=["fur"],
            caption="Fox",  # min_length=5
            confidence=0.9
        )

def test_guard_decision_enums():
    assert GuardDecision.ACCEPTED == "ACCEPTED"
    assert GuardDecision.REJECTED_CATEGORY_MISMATCH == "REJECTED_CATEGORY_MISMATCH"
    assert GuardDecision.REJECTED_LOW_CONFIDENCE == "REJECTED_LOW_CONFIDENCE"
    assert GuardDecision.REJECTED_LOW_SIMILARITY == "REJECTED_LOW_SIMILARITY"

def test_review_decision_enums():
    assert ReviewDecisionEnum.APPROVED == "APPROVED"
    assert ReviewDecisionEnum.REJECTED == "REJECTED"
