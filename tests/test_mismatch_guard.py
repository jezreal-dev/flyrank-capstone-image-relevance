"""Tests for the Mismatch Guard safety layer."""
import pytest
from app.services.mismatch_guard import MismatchGuard
from app.models.matching_schema import GuardDecision

@pytest.fixture
def guard():
    return MismatchGuard(confidence_threshold=0.70, similarity_threshold=0.60)

def test_guard_accepts_valid_match(guard):
    decision, reason = guard.evaluate_candidate(
        post_title="The Elusive Red Fox",
        post_content="Autumn hunting habits of the red fox.",
        target_subject="red fox",
        image_subject="red fox",
        image_category="wildlife",
        image_confidence=0.95,
        similarity_score=0.92
    )
    assert decision == GuardDecision.ACCEPTED
    assert "Verified match" in reason

def test_guard_rejects_low_confidence(guard):
    decision, reason = guard.evaluate_candidate(
        post_title="The Elusive Red Fox",
        post_content="Autumn hunting habits of the red fox.",
        target_subject="red fox",
        image_subject="red fox",
        image_category="wildlife",
        image_confidence=0.62,  # < 0.70
        similarity_score=0.92
    )
    assert decision == GuardDecision.REJECTED_LOW_CONFIDENCE
    assert "below acceptable safety threshold" in reason

def test_guard_rejects_category_mismatch_wolf_for_fox(guard):
    decision, reason = guard.evaluate_candidate(
        post_title="The Elusive Red Fox",
        post_content="Autumn hunting habits of the red fox in forest.",
        target_subject="red fox",
        image_subject="gray wolf",  # Forbidden predator
        image_category="wildlife",
        image_confidence=0.95,
        similarity_score=0.88  # Even with high similarity!
    )
    assert decision == GuardDecision.REJECTED_CATEGORY_MISMATCH
    assert "Subject mismatch: expected 'fox', detected 'wolf'" in reason

def test_guard_rejects_category_mismatch_dog_for_fox(guard):
    decision, reason = guard.evaluate_candidate(
        post_title="The Behavior of Red Foxes",
        post_content="Wild red foxes in temperate forests.",
        target_subject="red fox",
        image_subject="golden retriever",
        image_category="domestic_animal",
        image_confidence=0.98,
        similarity_score=0.80
    )
    assert decision == GuardDecision.REJECTED_CATEGORY_MISMATCH
    assert "domestic dog" in reason

def test_guard_rejects_low_similarity(guard):
    decision, reason = guard.evaluate_candidate(
        post_title="Superconducting Qubits in Cryogenic Systems",
        post_content="Quantum teleportation and dilution refrigerators.",
        target_subject="quantum physics",
        image_subject="quaint urban cafe",
        image_category="architecture",
        image_confidence=0.95,
        similarity_score=0.12  # < 0.60
    )
    assert decision == GuardDecision.REJECTED_LOW_SIMILARITY
    assert "below threshold" in reason
