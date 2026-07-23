"""AI-assisted title/abstract screening with pluggable backends.

Backends:
  - "heuristic" (default, no network): rule-based inclusion/exclusion using a
    PICO eligibility function you supply. Great for offline demos, CI, and as a
    baseline to compare an LLM against.
  - "openai": uses the OpenAI Chat Completions API (requires `pip install
    evidence-synth[openai]` and OPENAI_API_KEY). Sends title+abstract and asks
    for a structured decision.

Agreement with a human gold standard is measured with Cohen's kappa.
"""
from __future__ import annotations

import os
import re
from typing import Callable, List, Optional

from .models import Study, Decision, ScreeningDecision

# A PICO eligibility function: given a Study, return (decision, reason).
EligibilityFn = Callable[[Study], tuple[Decision, str]]


def heuristic_screener(
    include_if: Callable[[Study], bool],
    include_reason: str = "matches PICO",
    exclude_reason: str = "does not meet PICO",
) -> EligibilityFn:
    """Build a heuristic eligibility function from a predicate."""

    def fn(s: Study) -> tuple[Decision, str]:
        if include_if(s):
            return Decision.INCLUDE, include_reason
        return Decision.EXCLUDE, exclude_reason

    return fn


def openai_screener(model: str = "gpt-4o-mini") -> EligibilityFn:
    """Return an eligibility function backed by the OpenAI API.

    The model is asked to return JSON: {"decision": "include|exclude",
    "reason": "..."}. Falls back to UNCERTAIN if parsing fails.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def fn(s: Study) -> tuple[Decision, str]:
        prompt = (
            "You are a systematic-review screener. Given a study title and "
            "abstract, decide INCLUDE or EXCLUDE for a meta-analysis of "
            "pharmacologic cardiovascular efficacy (RCTs reporting effect sizes "
            "such as OR/RR/HR). Respond ONLY with JSON: "
            '{"decision": "include"|"exclude", "reason": "short reason"}.'
        )
        user = f"TITLE: {s.title}\nABSTRACT: {s.abstract}"
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            import json

            data = json.loads(resp.choices[0].message.content)
            dec = data.get("decision", "exclude").lower()
            decision = Decision.INCLUDE if dec == "include" else Decision.EXCLUDE
            return decision, data.get("reason", "")
        except Exception as e:  # noqa: BLE001
            return Decision.UNCERTAIN, f"openai error: {e}"

    return fn


def screen(
    studies: List[Study],
    eligibility: EligibilityFn,
    reviewer: str = "ai",
    confidence_fn: Optional[Callable[[Study], float]] = None,
) -> List[ScreeningDecision]:
    """Screen studies. Mutates each Study.decision in place and returns decisions."""
    decisions: List[ScreeningDecision] = []
    for s in studies:
        decision, reason = eligibility(s)
        conf = confidence_fn(s) if confidence_fn else 1.0
        s.decision = decision
        s.decision_reason = reason
        s.reviewer = reviewer
        decisions.append(
            ScreeningDecision(
                study_id=s.id,
                decision=decision,
                reason=reason,
                confidence=conf,
                reviewer=reviewer,
            )
        )
    return decisions


# -------- agreement statistics --------------------------------------------
def cohen_kappa(a: List[Decision], b: List[Decision]) -> float:
    """Cohen's kappa between two raters over a set of decisions.

    Decisions are treated as the 3-class label set {include, exclude, uncertain}.
    """
    labels = [Decision.INCLUDE, Decision.EXCLUDE, Decision.UNCERTAIN]
    idx = {l: i for i, l in enumerate(labels)}
    n = len(labels)
    cm = [[0] * n for _ in range(n)]
    for x, y in zip(a, b):
        cm[idx[x]][idx[y]] += 1
    total = sum(sum(r) for r in cm)
    if total == 0:
        return 1.0
    po = sum(cm[i][i] for i in range(n)) / total
    pe = 0.0
    for i in range(n):
        row = sum(cm[i])
        col = sum(cm[r][i] for r in range(n))
        pe += (row / total) * (col / total)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def agreement_report(
    studies: List[Study],
    gold: dict[str, Decision],
    reviewer: str = "ai",
) -> dict:
    """Compare AI decisions to a human gold-standard mapping {study_id: Decision}."""
    pred, obs = [], []
    for s in studies:
        if s.id in gold:
            pred.append(s.decision or Decision.EXCLUDE)
            obs.append(gold[s.id])
    kappa = cohen_kappa(obs, pred)
    tp = sum(1 for o, p in zip(obs, pred) if o == p == Decision.INCLUDE)
    fp = sum(1 for o, p in zip(obs, pred) if o != Decision.INCLUDE and p == Decision.INCLUDE)
    fn = sum(1 for o, p in zip(obs, pred) if o == Decision.INCLUDE and p != Decision.INCLUDE)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return {"kappa": kappa, "precision": prec, "recall": rec, "n": len(obs)}
