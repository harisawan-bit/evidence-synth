"""Smoke tests for the evidence-synth pipeline (no network required)."""
import os
import xml.dom.minidom as minidom

from evidence_synth import Pipeline
from evidence_synth.models import Decision
from evidence_synth.screening import cohen_kappa
from evidence_synth.novelty import NoveltyResult, _score


def _elig(s):
    text = (s.title + " " + s.abstract).lower()
    has_effect = any(t in text for t in ["or ", "rr ", "hr ", "odds ratio",
                                         "risk ratio", "hazard ratio"])
    is_rct = any(t in text for t in ["random", "rct", "trial"])
    return (Decision.INCLUDE, "RCT w/ effect size") if (has_effect and is_rct) \
        else (Decision.EXCLUDE, "no effect size / not RCT")


def test_dedup_merges_duplicates():
    p = Pipeline().load_sample().deduplicate()
    ids = {s.id for s in p.studies}
    assert "S02" not in ids and "S11" not in ids
    assert "S01" in ids
    assert p.merged.get("S02") == "S01"


def test_screen_includes_effect_size_rcts():
    p = Pipeline().load_sample().deduplicate().screen(_elig)
    inc = [s for s in p.studies if s.decision == Decision.INCLUDE]
    assert len(inc) >= 5


def test_meta_analysis_runs():
    p = Pipeline().load_sample().deduplicate().screen(_elig)
    p.extract().meta_analyze(measure=None, out_dir="output")
    r = p.result
    assert r.k >= 2
    assert 0 < r.pooled_ci_low <= r.pooled_estimate <= r.pooled_ci_high
    assert 0.0 <= r.i2 <= 1.0
    assert os.path.exists("output/prisma.svg")
    assert os.path.exists("output/forest.svg")
    minidom.parse("output/prisma.svg")
    minidom.parse("output/forest.svg")


def test_kappa():
    a = [Decision.INCLUDE, Decision.EXCLUDE, Decision.INCLUDE]
    assert cohen_kappa(a, a) == 1.0
    b = [Decision.EXCLUDE, Decision.INCLUDE, Decision.EXCLUDE]
    assert cohen_kappa(a, b) < 0


def test_novelty_scoring_verdicts():
    # heavily saturated, few new RCTs -> NO-GO
    no = _score(existing_ma=266, new_rcts=21)
    assert no[0] == "NO-GO"
    # real gap: many new RCTs vs few MAs -> GO
    go = _score(existing_ma=20, new_rcts=14)
    assert go[0] == "GO"
    # mixed -> CAUTION
    ca = _score(existing_ma=21, new_rcts=6)
    assert ca[0] == "CAUTION"
    # brand-new topic, zero MAs, some RCTs -> GO
    fresh = _score(existing_ma=0, new_rcts=5)
    assert fresh[0] == "GO"

