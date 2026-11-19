"""Tests for pure Python vector mathematics and cosine similarity."""
import pytest
from app.core.vector_math import (
    dot_product,
    vector_norm,
    cosine_similarity,
    generate_semantic_vector
)

def test_dot_product_identical():
    v1 = [1.0, 2.0, 3.0]
    assert dot_product(v1, v1) == 14.0

def test_dot_product_dimension_mismatch():
    with pytest.raises(ValueError):
        dot_product([1.0], [1.0, 2.0])

def test_vector_norm():
    v = [3.0, 4.0]
    assert vector_norm(v) == 5.0

def test_cosine_similarity_identical():
    v = [0.5, 0.5, 0.5, 0.5]
    sim = cosine_similarity(v, v)
    assert pytest.approx(sim, 0.001) == 1.0

def test_cosine_similarity_orthogonal():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    assert cosine_similarity(v1, v2) == 0.0

def test_cosine_similarity_empty_or_zero():
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

def test_semantic_concept_equivalence_latin_vulpes():
    vec_fox = generate_semantic_vector("red fox in autumn forest")
    vec_vulpes = generate_semantic_vector("Vulpes vulpes hunting in woodland")
    sim = cosine_similarity(vec_fox, vec_vulpes)
    assert sim > 0.70, f"Expected high semantic similarity for Vulpes vulpes concept, got {sim}"

def test_semantic_separation_fox_vs_colosseum():
    vec_fox = generate_semantic_vector("red fox in autumn forest")
    vec_colosseum = generate_semantic_vector("ancient Roman Colosseum stone arches")
    sim = cosine_similarity(vec_fox, vec_colosseum)
    assert sim < 0.20, f"Expected low similarity between fox and Colosseum, got {sim}"
