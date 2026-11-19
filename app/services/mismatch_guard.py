"""The Mismatch Guard: Production AI safety layer for preventing incorrect pairings."""
import os
import re
from typing import Tuple
from app.models.matching_schema import GuardDecision

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.70"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.60"))

# Incompatible taxonomic pairs: (expected_keywords, forbidden_candidate_keywords, diagnostic_reason)
TAXONOMIC_CONSTRAINTS = [
    (
        ["fox", "vulpes", "red fox"],
        ["wolf", "timber wolf", "canis lupus"],
        "Subject mismatch: expected 'fox', detected 'wolf' (canid predator divergence)"
    ),
    (
        ["fox", "vulpes", "red fox"],
        ["dog", "golden retriever", "canis familiaris", "domestic"],
        "Subject mismatch: expected wild 'fox', detected 'domestic dog'"
    ),
    (
        ["wolf", "timber wolf", "canis lupus"],
        ["fox", "vulpes", "red fox"],
        "Subject mismatch: expected apex predator 'wolf', detected 'fox'"
    ),
    (
        ["wolf", "canis lupus"],
        ["dog", "golden retriever", "domestic dog"],
        "Subject mismatch: expected wild 'wolf', detected 'domestic dog'"
    ),
    (
        ["bear", "grizzly", "ursus arctos"],
        ["tiger", "big cat", "lion"],
        "Subject mismatch: expected 'bear', detected feline 'tiger'"
    ),
    (
        ["server", "data center", "infrastructure"],
        ["laptop", "desk", "coffee"],
        "Scope mismatch: article targets datacenter enterprise infrastructure, candidate is personal developer workspace"
    ),
    (
        ["eiffel tower", "paris"],
        ["colosseum", "rome", "pagoda"],
        "Geographic mismatch: article targets Eiffel Tower (Paris), candidate is different architectural monument"
    )
]

class MismatchGuard:
    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        similarity_threshold: float = SIMILARITY_THRESHOLD
    ):
        self.confidence_threshold = confidence_threshold
        self.similarity_threshold = similarity_threshold

    def evaluate_candidate(
        self,
        post_title: str,
        post_content: str,
        target_subject: str | None,
        image_subject: str,
        image_category: str,
        image_confidence: float,
        similarity_score: float
    ) -> Tuple[GuardDecision, str]:
        """Evaluates whether an image candidate is safe and accurate for the post.
        Returns (GuardDecision, human_readable_explanation).
        """
        # 1. Confidence Safety Gate
        if image_confidence < self.confidence_threshold:
            return (
                GuardDecision.REJECTED_LOW_CONFIDENCE,
                f"Image classification confidence below acceptable safety threshold ({image_confidence:.2f} < {self.confidence_threshold:.2f})"
            )

        # 2. Explicit Taxonomic / Subject Mismatch Gate (Evaluated before similarity)
        combined_post_text = f"{post_title} {post_content} {target_subject or ''}".lower()
        candidate_subject_text = f"{image_subject} {image_category}".lower()

        for expected_terms, forbidden_terms, reason in TAXONOMIC_CONSTRAINTS:
            has_expected = any(re.search(r"\b" + re.escape(t) + r"\b", combined_post_text) for t in expected_terms)
            has_forbidden = any(re.search(r"\b" + re.escape(t) + r"\b", candidate_subject_text) for t in forbidden_terms)
            
            # If the post specifically discusses the expected concept, but the image is the forbidden concept
            if has_expected and has_forbidden:
                post_also_discusses_forbidden = any(re.search(r"\b" + re.escape(t) + r"\b", combined_post_text) for t in forbidden_terms)
                if not post_also_discusses_forbidden:
                    return (GuardDecision.REJECTED_CATEGORY_MISMATCH, reason)

        # 3. Semantic Similarity Gate
        if similarity_score < self.similarity_threshold:
            return (
                GuardDecision.REJECTED_LOW_SIMILARITY,
                f"Semantic similarity score ({similarity_score:.3f}) is below threshold ({self.similarity_threshold:.2f})"
            )

        # 4. Verified Acceptance
        return (
            GuardDecision.ACCEPTED,
            f"Verified match: high semantic similarity ({similarity_score:.3f} >= {self.similarity_threshold:.2f}) and aligned subject '{image_subject}' (confidence {image_confidence:.2f})"
        )

mismatch_guard = MismatchGuard()
