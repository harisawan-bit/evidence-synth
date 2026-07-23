"""Deterministic deduplication using a normalized similarity key.

Two-stage strategy:
  1. Exact-match on a normalized dedupe key (DOI > normalized title).
  2. Fuzzy-match on normalized title via token-sorted Jaccard similarity.

Returns the surviving studies plus a mapping of which IDs were merged.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple
from .models import Study
from .search import _norm_title


def doi_of(s: Study) -> str:
    return (s.doi or "").strip().lower()


def similarity_key(s: Study) -> str:
    """Preferred exact key: DOI if present, else normalized title."""
    d = doi_of(s)
    if d:
        return f"doi:{d}"
    return f"title:{_norm_title(s.title)}"


def _tokens(s: str) -> set:
    return set(_norm_title(s).split())


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def deduplicate(studies: List[Study], fuzzy_threshold: float = 0.92) -> Tuple[List[Study], Dict[str, str]]:
    """Remove duplicates. Returns (unique_studies, merged_map).

    ``merged_map`` maps every removed study id -> the id it was merged into.
    """
    survivors: List[Study] = []
    merged: Dict[str, str] = {}
    # assign dedupe_key for transparency
    for s in studies:
        s.dedupe_key = similarity_key(s)

    for s in studies:
        # exact key match
        exact = [x for x in survivors if x.dedupe_key == s.dedupe_key]
        if exact:
            merged[s.id] = exact[0].id
            continue
        # fuzzy title match
        hit = None
        for x in survivors:
            if _jaccard(s.title, x.title) >= fuzzy_threshold:
                hit = x
                break
        if hit:
            merged[s.id] = hit.id
            # keep the version with a DOI if available
            if not doi_of(hit) and doi_of(s):
                hit.doi = s.doi
                hit.dedupe_key = similarity_key(hit)
            continue
        survivors.append(s)
    return survivors, merged


if __name__ == "__main__":
    from .search import sample_corpus

    uni, merged = deduplicate(sample_corpus())
    print(f"Input: {len(sample_corpus())}  ->  Unique: {len(uni)}  (removed {len(merged)})")
    for k, v in merged.items():
        print(f"  {k}  merged into  {v}")
