"""Regression tests ensuring all 6 FlyRank Evaluator Acceptance Probes pass."""
import pytest
from scripts.verify_probes import (
    probe_1_batch_tags,
    probe_2_fox_ranking,
    probe_3_wolf_guard_refusal,
    probe_4_no_match_rejection,
    probe_5_eval_precision,
    probe_6_cost_tracking
)

def test_acceptance_probe_1_batch_and_confidence():
    probe_1_batch_tags()

def test_acceptance_probe_2_fox_ranking():
    probe_2_fox_ranking()

def test_acceptance_probe_3_wolf_guard_refusal():
    probe_3_wolf_guard_refusal()

def test_acceptance_probe_4_no_match_rejection():
    probe_4_no_match_rejection()

def test_acceptance_probe_5_eval_precision():
    probe_5_eval_precision()

def test_acceptance_probe_6_cost_tracking():
    probe_6_cost_tracking()
