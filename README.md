# evidence-synth

**Evidence Synthesis Automation Framework** — a PRISMA-compliant, end-to-end
pipeline for systematic reviews and meta-analysis.

> The GitHub gap this fills: `evidence synthesis automation` returns **3 repos**
> total (vs. 321+ for "awesome AI agents"). This is a near-empty space with real,
> recurring demand from anyone running systematic reviews / meta-analyses.

## What it does

```
search  ->  deduplicate  ->  screen (AI-assisted)  ->  extract  ->  meta-analyze  ->  report
```

- **Search** — live PubMed E-utilities (`pubmed_search`) or a bundled offline
  sample corpus so the whole framework runs with zero network access.
- **Deduplicate** — exact (DOI / normalized title) + fuzzy (token-sorted Jaccard)
  merge, with a full merge map for reproducibility.
- **Screen** — pluggable eligibility backends: a deterministic `heuristic`
  screener (no API key, great baseline/CI) and an `openai` screener
  (`pip install evidence-synth[openai]` + `OPENAI_API_KEY`). Agreement with a
  human gold standard is scored with **Cohen's kappa**, precision, and recall.
- **Extract** — parses OR / RR / HR effect sizes and 95% CIs from abstract text
  (or from a structured `extracted` dict).
- **Meta-analyze** — DerSimonian–Laird **random-effects** model (method-of-moments
  τ²), pooled log estimate + 95% CI, **I²** and Cochrane's **Q** for heterogeneity.
  Auto-selects the dominant effect measure so mixed OR/RR/HR inputs still pool.
- **Report** — PRISMA 2020 **flow diagram** (SVG), a **forest plot** (SVG), and a
  machine-readable `studies.json`.

## Install

```bash
pip install -e .
# optional: LLM screening backend
pip install -e ".[openai]"
```

## Quick start

```bash
# Full offline demo: sample corpus -> dedup -> screen -> PRISMA + forest plot
evidence-synth demo

# Live PubMed search + pipeline
evidence-synth run --query "statin cardiovascular RCT" --email you@example.com --out output
```

### As a library

```python
from evidence_synth import Pipeline
from evidence_synth.models import Decision

p = (Pipeline()
     .load_sample()          # or .load_pubmed("query", email="you@x.com")
     .deduplicate()          # removes near-duplicates (S02/S11 -> S01)
     .screen(lambda s: (
         Decision.INCLUDE, "RCT w/ effect size")
         if ("random" in (s.title+s.abstract).lower()
             and any(t in (s.title+s.abstract).lower() for t in ["or ","rr ","hr "]))
         else (Decision.EXCLUDE, "no effect size / not RCT"))
     .extract()
     .meta_analyze(measure=None, out_dir="output"))

print(p.report())
print(p.result.summary())
```

## Project layout

```
evidence_synth/
  search.py       PubMed E-utilities + bundled sample corpus
  dedup.py        deterministic + fuzzy deduplication
  screening.py    heuristic / OpenAI backends + Cohen's kappa
  extraction.py   effect-size parsing + D-L random-effects meta-analysis
  prisma.py       PRISMA 2020 flow diagram (SVG)
  forest.py       forest plot (SVG)
  pipeline.py     orchestration
  cli.py          `evidence-synth` command
```

## Caveats (read before you cite anything)

This framework **automates the mechanics** of a review. It does **not** replace
protocol registration (PROSPERO), peer review, or methodological judgment. The
bundled sample corpus is synthetic and for demonstration only. Always:

- register your protocol *before* screening,
- keep a human in the loop for the final include/exclude calls,
- verify extracted effect sizes against the source PDFs,
- report PRISMA 2020 items and a risk-of-bias assessment alongside the numbers.

## License

MIT
