"""Command-line interface for evidence-synth.

Examples
--------
  # Run the full offline demo pipeline (sample corpus -> PRISMA + forest)
  evidence-synth demo

  # Live PubMed search + pipeline
  evidence-synth run --query "statin cardiovascular RCT" --email you@example.com

  # Just deduplicate + screen the sample corpus and print the PRISMA summary
  evidence-synth demo --no-meta
"""
from __future__ import annotations

import argparse
import sys

from .models import Decision
from .pipeline import Pipeline
from . import screening


def _default_eligibility():
    """Heuristic: include RCTs reporting OR/RR/HR effect sizes."""
    def fn(study):
        text = (study.title + " " + study.abstract).lower()
        has_effect = any(t in text for t in ["or ", "rr ", "hr ", "odds ratio",
                                              "risk ratio", "hazard ratio"])
        is_rct = any(t in text for t in ["random", "rct", "trial"])
        if has_effect and is_rct:
            return Decision.INCLUDE, "RCT reporting effect size"
        if not has_effect:
            return Decision.EXCLUDE, "no extractable effect size"
        return Decision.EXCLUDE, "not an RCT"
    return fn


def cmd_demo(args) -> int:
    p = Pipeline().load_sample().deduplicate()
    p.screen(_default_eligibility())
    print(p.report())
    if not args.no_meta:
        try:
            p.extract().meta_analyze(measure=None, out_dir=args.out)
            print("\n" + p.result.summary())
            print(f"\nArtifacts written to: {args.out}/ (prisma.svg, forest.svg, studies.json)")
        except RuntimeError as e:
            print(f"[skip meta] {e}")
    return 0


def cmd_run(args) -> int:
    p = Pipeline().load_pubmed(args.query, retmax=args.retmax, email=args.email)
    if not p.studies:
        print("No studies retrieved (network/query issue).")
        return 1
    p.deduplicate().screen(_default_eligibility())
    print(p.report())
    try:
        p.extract().meta_analyze(measure=None, out_dir=args.out)
        print("\n" + p.result.summary())
    except RuntimeError as e:
        print(f"[skip meta] {e}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="evidence-synth",
        description="Evidence Synthesis Automation Framework (PRISMA pipeline).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo", help="Run the offline sample pipeline.")
    d.add_argument("--out", default="output", help="Output directory for diagrams.")
    d.add_argument("--no-meta", action="store_true", help="Skip meta-analysis.")
    d.set_defaults(func=cmd_demo)

    r = sub.add_parser("run", help="Run a live PubMed search + pipeline.")
    r.add_argument("--query", required=True, help="PubMed query string.")
    r.add_argument("--email", default="", help="Contact email for NCBI.")
    r.add_argument("--retmax", type=int, default=50)
    r.add_argument("--measure", default="OR", choices=["OR", "RR", "HR"])
    r.add_argument("--out", default="output")
    r.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
