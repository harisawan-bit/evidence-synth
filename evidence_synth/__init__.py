"""Evidence Synthesis Automation Framework.

A PRISMA-compliant, end-to-end pipeline for systematic reviews and meta-analysis:
search -> deduplicate -> screen (AI-assisted) -> extract -> meta-analyze -> report.
"""
from .models import ScreeningDecision, Study
from .novelty import NoveltyResult
from .novelty import scan as scan_novelty
from .pipeline import Pipeline

__version__ = "0.2.0"
__all__ = ["NoveltyResult", "Pipeline", "ScreeningDecision", "Study", "scan_novelty"]
