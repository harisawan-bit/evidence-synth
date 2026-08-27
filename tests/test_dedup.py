"""Tests for deterministic + fuzzy deduplication (in-memory, no network).

``evidence_synth.dedup.deduplicate`` is pure given an input list of ``Study``
records: it returns the survivors and a merged-id map. We build small,
controlled in-memory sets to verify both the exact (DOI / normalized title)
match and the fuzzy (token-sorted Jaccard) merge behave deterministically.
"""

from evidence_synth.dedup import _jaccard, deduplicate, similarity_key
from evidence_synth.models import Study


def _study(id_, title, doi=None, abstract=""):
    return Study(id=id_, title=title, abstract=abstract, doi=doi)


def test_exact_doi_merge():
    studies = [
        _study("A", "Statin reduces MACE", doi="10.1000/xyz"),
        _study("B", "Statin reduces MACE (a randomized trial)", doi="10.1000/xyz"),
    ]
    survivors, merged = deduplicate(studies)
    assert len(survivors) == 1
    assert survivors[0].id == "A"
    assert merged == {"B": "A"}


def test_exact_normalized_title_merge():
    # Different casing / punctuation, same normalized title -> exact merge.
    studies = [
        _study("A", "Beta-blockers in heart failure", doi="10.1000/a"),
        _study("B", "Beta Blockers in Heart Failure!", doi="10.1000/b"),
    ]
    survivors, merged = deduplicate(studies)
    assert len(survivors) == 1
    assert merged == {"B": "A"}


def test_fuzzy_title_merge():
    # Near-duplicate titles (>0.92 token Jaccard), distinct DOIs -> fuzzy merge.
    # B is A plus a single extra token, giving Jaccard 16/17 ~= 0.94.
    base = (
        "Statin therapy reduces major adverse cardiovascular events in a large "
        "randomized controlled trial of high intensity"
    )
    studies = [
        _study("A", base, doi="10.1000/a"),
        _study("B", base + " now", doi="10.100.1000/b"),
    ]
    survivors, merged = deduplicate(studies)
    assert len(survivors) == 1
    assert merged == {"B": "A"}


def test_distinct_studies_survive():
    studies = [
        _study("A", "ACE inhibitors after myocardial infarction", doi="10.1000/a"),
        _study("B", "SGLT2 inhibitors in heart failure", doi="10.1000/b"),
        _study("C", "DOACs versus warfarin in atrial fibrillation", doi="10.1000/c"),
    ]
    survivors, merged = deduplicate(studies)
    assert len(survivors) == 3
    assert merged == {}


def test_merged_keeps_doi_when_survivor_lacks_one():
    # Survivor has no DOI, duplicate does -> DOI is carried onto survivor.
    studies = [
        _study("A", "Shared title here", doi=None),
        _study("B", "Shared title here", doi="10.1000/b"),
    ]
    survivors, merged = deduplicate(studies)
    assert merged == {"B": "A"}
    assert survivors[0].id == "A"
    assert survivors[0].doi == "10.1000/b"


def test_idempotent_on_second_pass():
    studies = [
        _study("A", "Statins reduce MACE", doi="10.1000/a"),
        _study("B", "Statins reduce MACE a trial", doi="10.1000/b"),
        _study("C", "SGLT2 inhibitors heart failure", doi="10.1000/c"),
    ]
    survivors, merged = deduplicate(studies)
    # Re-running dedup on the survivors must be a no-op.
    survivors2, merged2 = deduplicate(survivors)
    assert len(survivors2) == len(survivors)
    assert merged2 == {}


def test_similarity_key_doi_preferred():
    s = _study("A", "Some title", doi="10.1000/a")
    assert similarity_key(s).startswith("doi:")


def test_jaccard_boundary():
    assert _jaccard("a b c d", "a b c d") == 1.0
    assert _jaccard("a b c d", "w x y z") == 0.0
    assert _jaccard("", "a b") == 0.0
