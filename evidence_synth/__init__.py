"""Evidence Synthesis Automation Framework.

A PRISMA-compliant, end-to-end pipeline for systematic reviews and meta-analysis:
search -> deduplicate -> screen (AI-assisted) -> extract -> meta-analyze -> report.
"""
from .models import Study, ScreeningDecision
from .pipeline import Pipeline
from .novelty import scan as scan_novelty, NoveltyResult

__version__ = "0.1.0"
__all__ = ["Study", "ScreeningDecision", "Pipeline", "scan_novelty", "NoveltyResult"]
