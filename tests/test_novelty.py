"""Tests for the novelty / evidence-saturation verdict logic (no network).

The scoring function ``evidence_synth.novelty._score`` is pure: it maps raw
PubMed counts (existing MA/SR count, new-RCT count) to a (verdict, score,
rationale) tuple. We exercise the full decision surface with mocked counts so
the test never touches the network.
"""
import pytest

from evidence_synth.novelty import NoveltyResult, _score


def test_score_returns_three_tuple():
    out = _score(existing_ma=20, new_rcts=14)
    assert isinstance(out, tuple) and len(out) == 3
    verdict, score, rationale = out
    assert verdict in {"GO", "CAUTION", "NO-GO"}
    assert 0.0 <= score <= 1.0
    assert isinstance(rationale, str) and rationale


@pytest.mark.parametrize(
    "existing_ma,new_rcts,expected",
    [
        # Heavily saturated, almost no new evidence -> NO-GO
        (266, 21, "NO-GO"),
        (120, 5, "NO-GO"),
        # Real gap: many new RCTs vs few reviews -> GO
        (20, 14, "GO"),
        # Brand-new topic, zero MAs (all evidence is new) -> GO
        (0, 5, "GO"),
        (0, 1, "GO"),
        # Mixed signal -> CAUTION
        (21, 6, "CAUTION"),
        (40, 8, "CAUTION"),
    ],
)
def test_score_verdicts(existing_ma, new_rcts, expected):
    verdict, _, _ = _score(existing_ma, new_rcts)
    assert verdict == expected


def test_score_zero_total_no_division_error():
    # 0 MAs and 0 RCTs must not raise (avoids ZeroDivisionError) and yields a
    # valid verdict. With no evidence either way the model stays cautious.
    verdict, score, _ = _score(existing_ma=0, new_rcts=0)
    assert verdict == "CAUTION"
    assert 0.0 <= score <= 1.0


def test_novelty_result_summary_renders():
    res = NoveltyResult(
        topic="Finerenone in CKD",
        existing_ma_count=20,
        recent_ma_year=2021,
        new_rcts_since_last_ma=14,
        verdict="GO",
        score=0.5,
        rationale="Real gap.",
    )
    text = res.summary()
    assert "Finerenone in CKD" in text
    assert "GO" in text
    assert "PROSPERO" in text  # manual-follow-up note is always present
