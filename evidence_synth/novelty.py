"""Novelty / evidence-saturation scanner.

Answers the question every systematic-review team should ask *before* spending
months on a review: **has this already been done, and is there enough NEW
evidence to justify a fresh one?**

It does three things against PubMed (live, via E-utilities):

1. Counts existing meta-analyses / systematic reviews on the topic.
2. Finds the most recent MA year and counts primary RCTs published AFTER it
   (the only evidence that can justify a new review).
3. Surfaces the year distribution of existing MAs (saturation trend).

Then it emits a scored verdict:
  - GO         : many new RCTs since the last MA (real gap)
  - CAUTION    : few new RCTs / heavily saturated
  - NO-GO      : topic already covered very recently by many MAs

Note: PROSPERO overlap checking still requires the browser (JS-rendered, per
the srma-topic-scoping skill). This module covers the PubMed-side saturation
signal; PROSPERO is flagged for manual follow-up.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def json_load(url: str) -> dict:
    return json.loads(urllib.request.urlopen(url, timeout=30).read().decode("utf-8", "ignore"))


def _esearch_count(term: str, retmax: int = 50, email: str = "") -> dict:
    params = f"db=pubmed&retmode=json&retmax={retmax}&term={urllib.parse.quote(term)}"
    if email:
        params += f"&tool=evidence-synth&email={urllib.parse.quote(email)}"
    url = f"{EUTILS}/esearch.fcgi?{params}"
    data = json_load(url)
    return data.get("esearchresult", {})


def _efetch_years(ids: List[str]) -> List[str]:
    if not ids:
        return []
    url = f"{EUTILS}/efetch.fcgi?db=pubmed&retmode=xml&id={','.join(ids)}"
    xml = urllib.request.urlopen(url, timeout=60).read().decode("utf-8", "ignore")
    return re.findall(r"<PubDate>.*?<Year>(\d{4})</Year>", xml, re.DOTALL)


@dataclass
class NoveltyResult:
    topic: str
    existing_ma_count: int
    recent_ma_year: Optional[int]
    ma_years: List[str] = field(default_factory=list)
    new_rcts_since_last_ma: int = 0
    new_rcts_window: str = ""
    new_rct_window_years: int = 4
    verdict: str = ""
    score: float = 0.0
    rationale: str = ""
    prospero_note: str = (
        "PROSPERO overlap must be checked manually in the browser "
        "(JS-rendered); not yet automatable via API."
    )

    def summary(self) -> str:
        return (
            f"Novelty Scan: {self.topic}\n"
            f"  Existing MAs/SRs : {self.existing_ma_count}\n"
            f"  Latest MA year   : {self.recent_ma_year}\n"
            f"  New RCTs (recent {self.new_rct_window_years}y): {self.new_rcts_since_last_ma} ({self.new_rcts_window})\n"
            f"  VERDICT          : {self.verdict}  (score {self.score:.2f})\n"
            f"  -> {self.rationale}\n"
            f"  [!] {self.prospero_note}"
        )


def _score(existing_ma: int, new_rcts: int):
    """Return (verdict, score, rationale) from raw counts. Pure / testable."""
    total = existing_ma + new_rcts
    novelty_ratio = (new_rcts / total) if total else 0.0
    sat = min(1.0, existing_ma / 100.0)  # 100+ MAs => fully saturated
    score = round(0.65 * novelty_ratio + 0.35 * (1 - sat), 3)

    if existing_ma >= 50 and novelty_ratio < 0.15:
        verdict = "NO-GO"
        rationale = (
            f"Heavily saturated ({existing_ma} MAs/SRs) with little new primary "
            f"evidence (only {new_rcts} RCTs in the recent window). A new review "
            "would almost certainly be redundant — pick a narrower PICO or move on."
        )
    elif novelty_ratio >= 0.30 or (existing_ma < 20 and new_rcts >= 5):
        verdict = "GO"
        rationale = (
            f"Real gap: {new_rcts} new RCTs vs {existing_ma} existing review(s) "
            f"(novelty ratio {novelty_ratio:.2f}). Enough fresh evidence to justify a "
            "new/updated review. Lock a focused PICO slice and register on PROSPERO."
        )
    else:
        verdict = "CAUTION"
        rationale = (
            "Mixed signal: moderate saturation and limited new evidence. Narrow the "
            "PICO (subgroup, outcome, or population) to carve a defensible gap, and "
            "confirm no PROSPERO registration already covers it."
        )
    return verdict, score, rationale


def scan(
    topic: str,
    base_query: str,
    email: str = "",
    new_rct_window_years: int = 4,
) -> NoveltyResult:
    """Run the saturation scan for ``topic`` using ``base_query`` (the PICO string).

    ``base_query`` should be the core topic, e.g. "statin cardiovascular".
    """
    ma_term = f'{base_query} AND "meta-analysis"[pt]'
    rct_term = f'{base_query} AND "randomized controlled trial"[pt]'

    ma_res = _esearch_count(ma_term, retmax=60, email=email)
    existing_ma = int(ma_res.get("count", 0))
    ma_ids = ma_res.get("idlist", [])
    ma_years = _efetch_years(ma_ids)
    recent_ma_year = max((int(y) for y in ma_years), default=None)

    new_rcts = 0
    window = ""
    current_year = 2026
    if recent_ma_year:
        # Count RCTs published in the most recent `new_rct_window_years`
        # (evidence that has accumulated and may justify a fresh review).
        lo = max(recent_ma_year, current_year - new_rct_window_years + 1)
        hi = current_year
        window = f"{lo}:{hi}[dp]"
        new_term = f"{rct_term} AND {lo}:{hi}[dp]"
        new_rcts = int(_esearch_count(new_term, retmax=1, email=email).get("count", 0))
    else:
        # no MA found -> everything is new
        window = "1900:2026[dp]"
        new_rcts = int(_esearch_count(rct_term, retmax=1, email=email).get("count", 0))

    verdict, score, rationale = _score(existing_ma, new_rcts)

    return NoveltyResult(
        topic=topic,
        existing_ma_count=existing_ma,
        recent_ma_year=recent_ma_year,
        ma_years=ma_years,
        new_rcts_since_last_ma=new_rcts,
        new_rcts_window=window,
        new_rct_window_years=new_rct_window_years,
        verdict=verdict,
        score=score,
        rationale=rationale,
    )
