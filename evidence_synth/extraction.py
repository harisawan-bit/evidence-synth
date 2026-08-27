"""Data extraction + meta-analysis.

Parses effect sizes (OR / RR / HR) and their 95% CI from free text or a
structured dict, then runs a DerSimonian-Laird random-effects meta-analysis
with the between-study variance tau^2 estimated via the method-of-moments and
heterogeneity reported as I^2 and Cochrane's Q.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from scipy import stats

from .models import Decision, Study


@dataclass
class EffectSize:
    study_id: str
    measure: str  # "OR" | "RR" | "HR"
    estimate: float
    ci_low: float
    ci_high: float
    weight: float = 0.0
    yi: float = 0.0  # log estimate
    vi: float = 0.0  # log variance

    @property
    def se(self) -> float:
        # SE of log(estimate) from CI: (ln(high)-ln(low)) / (2*1.96)
        return (math.log(self.ci_high) - math.log(self.ci_low)) / (2 * 1.959963985)


_MEASURE_RE = re.compile(
    r"\b(OR|RR|HR)\s*[=:]?\s*([0-9]*\.?[0-9]+)\s*[,;]?\s*"
    r"(?:95%\s*CI\s*)?\(?\s*([0-9]*\.?[0-9]+)\s*[-–to]+\s*([0-9]*\.?[0-9]+)\s*\)?",
    re.IGNORECASE,
)


def parse_effect_from_text(text: str) -> Optional[EffectSize]:
    """Heuristic parser for 'OR 0.72 (0.61-0.85)' style strings."""
    m = _MEASURE_RE.search(text)
    if not m:
        return None
    measure, est, lo, hi = m.group(1), m.group(2), m.group(3), m.group(4)
    try:
        est_f, lo_f, hi_f = float(est), float(lo), float(hi)
    except ValueError:
        return None
    if est_f <= 0 or lo_f <= 0 or hi_f <= 0:
        return None
    # Placeholder study_id; set by caller
    return EffectSize("?", measure.upper(), est_f, lo_f, hi_f)


def extract_effects(
    studies: List[Study], measure: Optional[str] = None
) -> List[EffectSize]:
    """Extract effect sizes from included studies (uses 'extracted' dict if present,
    else parses the abstract text)."""
    out: List[EffectSize] = []
    for s in studies:
        if s.decision not in (Decision.INCLUDE, None):
            continue
        if s.extracted:
            ex = s.extracted
            if measure and ex.get("measure", "").upper() != measure.upper():
                continue
            out.append(
                EffectSize(
                    s.id,
                    ex.get("measure", "OR"),
                    float(ex["estimate"]),
                    float(ex["ci_low"]),
                    float(ex["ci_high"]),
                )
            )
        else:
            es = parse_effect_from_text(s.abstract)
            if es:
                if measure and es.measure != measure.upper():
                    continue
                es.study_id = s.id
                out.append(es)
    return out


@dataclass
class MetaResult:
    pooled_log: float
    pooled_se: float
    pooled_estimate: float
    pooled_ci_low: float
    pooled_ci_high: float
    tau2: float
    i2: float
    q: float
    q_pvalue: float
    k: int
    measure: str

    def summary(self) -> str:
        return (
            f"Meta-analysis ({self.measure}, k={self.k})\n"
            f"  Pooled estimate = {self.pooled_estimate:.3f} "
            f"(95% CI {self.pooled_ci_low:.3f}-{self.pooled_ci_high:.3f})\n"
            f"  tau^2 = {self.tau2:.4f}   I^2 = {self.i2*100:.1f}%\n"
            f"  Cochrane Q = {self.q:.2f} (p={self.q_pvalue:.3f})"
        )


def meta_analyze(effects: List[EffectSize], measure: Optional[str] = None) -> MetaResult:
    """DerSimonian-Laird random-effects meta-analysis (method-of-moments tau^2).

    If ``measure`` is None (recommended), the most common effect measure among
    the supplied effects is chosen automatically and only those studies are
    pooled (effect sizes are only combinable within one measure).
    """
    if len(effects) < 2:
        raise ValueError("Need at least 2 studies for meta-analysis.")
    if measure is None:
        from collections import Counter
        measure = Counter(e.measure for e in effects).most_common(1)[0][0]
    measure = measure.upper()
    subset = [e for e in effects if e.measure == measure]
    if len(subset) < 2:
        raise ValueError(
            f"Only {len(subset)} study(ies) report measure '{measure}'; need >=2."
        )
    effects = subset

    yi = np.array([math.log(e.estimate) for e in effects])
    vi = np.array([(math.log(e.ci_high) - math.log(e.ci_low)) / (2 * 1.959963985) ** 2
                   for e in effects])
    # fixed-effect weights
    w_fixed = 1.0 / vi
    # Cochrane Q
    mu_fe = np.sum(w_fixed * yi) / np.sum(w_fixed)
    Q = float(np.sum(w_fixed * (yi - mu_fe) ** 2))
    df = len(effects) - 1
    Q_p = float(1 - stats.chi2.cdf(Q, df)) if df > 0 else 1.0
    # D-L tau^2
    C = np.sum(w_fixed) - np.sum(w_fixed ** 2) / np.sum(w_fixed)
    tau2 = max(0.0, (Q - df) / C)
    # random-effects weights
    w_re = 1.0 / (vi + tau2)
    mu_re = np.sum(w_re * yi) / np.sum(w_re)
    se_re = math.sqrt(1.0 / np.sum(w_re))
    ci_low = math.exp(mu_re - 1.959963985 * se_re)
    ci_high = math.exp(mu_re + 1.959963985 * se_re)
    i2 = max(0.0, (Q - df) / Q) if Q > 0 else 0.0

    # store weights for forest-plot use
    for e, w in zip(effects, w_re):
        e.weight = float(w)
        e.yi = float(math.log(e.estimate))
        e.vi = float(vi[list(effects).index(e)])

    return MetaResult(
        pooled_log=float(mu_re),
        pooled_se=se_re,
        pooled_estimate=float(math.exp(mu_re)),
        pooled_ci_low=ci_low,
        pooled_ci_high=ci_high,
        tau2=tau2,
        i2=i2,
        q=Q,
        q_pvalue=Q_p,
        k=len(effects),
        measure=measure,
    )
