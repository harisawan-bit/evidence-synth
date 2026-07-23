"""PRISMA 2020 flow-diagram generator (SVG + text summary).

Produces a standards-compliant flow diagram from the decisions recorded on a
set of studies. No external dependencies.
"""
from __future__ import annotations

from typing import Dict, List
from .models import Study, Decision


def _count(studies: List[Study]) -> Dict[str, int]:
    inc = sum(1 for s in studies if s.decision == Decision.INCLUDE)
    exc = sum(1 for s in studies if s.decision == Decision.EXCLUDE)
    unc = sum(1 for s in studies if s.decision == Decision.UNCERTAIN)
    return {
        "identified": len(studies),
        "screened": len(studies),
        "included": inc,
        "excluded": exc,
        "uncertain": unc,
    }


def text_summary(studies: List[Study]) -> str:
    c = _count(studies)
    lines = [
        "PRISMA 2020 Flow Summary",
        "-" * 28,
        f"Records identified:        {c['identified']}",
        f"Records screened:          {c['screened']}",
        f"  - included:              {c['included']}",
        f"  - excluded:              {c['excluded']}",
        f"  - uncertain (human review): {c['uncertain']}",
    ]
    return "\n".join(lines)


def svg(studies: List[Study], path: str) -> str:
    """Write a PRISMA flow diagram to ``path`` (SVG) and return the path."""
    c = _count(studies)
    boxes = [
        ("Records identified", c["identified"]),
        ("Records screened", c["screened"]),
        ("Reports sought for retrieval", c["screened"]),
        ("Reports assessed for eligibility", c["screened"]),
        ("Studies included", c["included"]),
        ("Studies excluded", c["excluded"]),
        ("Uncertain (need human review)", c["uncertain"]),
    ]
    w, h, bh = 520, 40 + len(boxes) * 70, 46
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
        f'<rect width="{w}" height="{h}" fill="white"/>',
        f'<text x="{w/2}" y="26" font-family="sans-serif" font-size="16" '
        f'font-weight="bold" text-anchor="middle">PRISMA 2020 Flow</text>',
    ]
    y = 50
    for label, n in boxes:
        svg_parts.append(
            f'<g transform="translate(40,{y})">'
            f'<rect width="{w-160}" height="{bh}" fill="#eef" stroke="#669" rx="4"/>'
            f'<text x="12" y="{bh/2+5}" font-family="sans-serif" font-size="13">{label}</text>'
            f'<rect x="{w-160-40}" width="40" height="{bh}" fill="#669" rx="4"/>'
            f'<text x="{w-160-20}" y="{bh/2+5}" font-family="sans-serif" font-size="13" '
            f'fill="white" text-anchor="middle">{n}</text>'
            f"</g>"
        )
        y += 70
    svg_parts.append("</svg>")
    out = "\n".join(svg_parts)
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    return path


if __name__ == "__main__":
    from .search import sample_corpus

    s = sample_corpus()
    for st in s:
        st.decision = Decision.INCLUDE if "OR" in st.abstract or "RR" in st.abstract or "HR" in st.abstract else Decision.EXCLUDE
    print(text_summary(s))
    print("SVG ->", svg(s, "prisma_demo.svg"))
