"""High-level pipeline that wires the stages together.

Usage:
    from evidence_synth import Pipeline
    p = Pipeline()
    p.load_search(evidence_synth.search.sample_corpus)
    p.deduplicate()
    p.screen(eligibility=...)
    p.meta_analyze(measure="OR", out_dir="output")
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional

from . import dedup, extraction, forest, prisma, screening
from .models import Study
from .search import pubmed_search, sample_corpus


class Pipeline:
    def __init__(self, studies: Optional[List[Study]] = None):
        self.studies: List[Study] = studies or []
        self.merged: dict = {}
        self.effects: List[extraction.EffectSize] = []
        self.result: Optional[extraction.MetaResult] = None

    # ---- load ----
    def load(self, studies: List[Study]) -> "Pipeline":
        self.studies = studies
        return self

    def load_sample(self) -> "Pipeline":
        self.studies = sample_corpus()
        return self

    def load_pubmed(self, query: str, retmax: int = 50, email: str = "") -> "Pipeline":
        self.studies = pubmed_search(query, retmax=retmax, email=email)
        return self

    # ---- stages ----
    def deduplicate(self, fuzzy_threshold: float = 0.92) -> "Pipeline":
        self.studies, self.merged = dedup.deduplicate(self.studies, fuzzy_threshold)
        return self

    def screen(self, eligibility: Callable, reviewer: str = "ai") -> "Pipeline":
        screening.screen(self.studies, eligibility, reviewer=reviewer)
        return self

    def extract(self, measure: Optional[str] = None) -> "Pipeline":
        self.effects = extraction.extract_effects(self.studies, measure=measure)
        return self

    def meta_analyze(self, measure: Optional[str] = None, out_dir: str = "output") -> "Pipeline":
        if len(self.effects) < 2:
            raise RuntimeError(
                f"Only {len(self.effects)} extractable effect size(s); need >=2 to meta-analyze."
            )
        self.result = extraction.meta_analyze(self.effects, measure=measure)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            prisma.svg(self.studies, os.path.join(out_dir, "prisma.svg"))
            forest.forest_plot(self.effects, self.result, os.path.join(out_dir, "forest.svg"))
            with open(os.path.join(out_dir, "studies.json"), "w", encoding="utf-8") as f:
                import json
                json.dump([s.to_record() for s in self.studies], f, indent=2)
        return self

    # ---- reporting ----
    def report(self) -> str:
        lines = [prisma.text_summary(self.studies)]
        if self.result:
            lines.append("")
            lines.append(self.result.summary())
        if self.merged:
            lines.append("")
            lines.append("Deduplicated (merged -> survivor):")
            for k, v in self.merged.items():
                lines.append(f"  {k} -> {v}")
        return "\n".join(lines)
