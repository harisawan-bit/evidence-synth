"""Core data models for the evidence-synthesis pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Decision(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"


@dataclass
class Study:
    """A single literature record flowing through the pipeline."""

    id: str
    title: str
    abstract: str = ""
    authors: str = ""
    year: Optional[int] = None
    journal: str = ""
    doi: Optional[str] = None
    source: str = ""
    # Fields populated downstream:
    dedupe_key: str = ""
    decision: Optional[Decision] = None
    decision_reason: str = ""
    reviewer: str = "human"  # "human" | "ai" | model name
    extracted: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "source": self.source,
            "dedupe_key": self.dedupe_key,
            "decision": self.decision.value if self.decision else None,
            "decision_reason": self.decision_reason,
            "reviewer": self.reviewer,
            "extracted": self.extracted,
        }


@dataclass
class ScreeningDecision:
    study_id: str
    decision: Decision
    reason: str = ""
    confidence: float = 1.0
    reviewer: str = "ai"
