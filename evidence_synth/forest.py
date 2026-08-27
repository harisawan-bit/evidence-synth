"""Forest plot generator (SVG, no matplotlib dependency)."""
from __future__ import annotations

from typing import List

from .extraction import EffectSize, MetaResult


def forest_plot(effects: List[EffectSize], result: MetaResult, path: str) -> str:
    """Render a simple forest plot to SVG and return the path."""
    w = 720
    row_h = 34
    header = 40
    h = header + len(effects) * row_h + 80
    # x-scale: log space mapped to pixels; center on pooled estimate
    vals = [math_log(e.estimate) for e in effects]
    lo = min([*vals, result.pooled_log]) - 0.4
    hi = max([*vals, result.pooled_log]) + 0.4
    x0, x1 = 200, 660
    def px(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
        f'<rect width="{w}" height="{h}" fill="white"/>',
        f'<text x="20" y="26" font-family="sans-serif" font-size="14" '
        f'font-weight="bold">Forest plot ({result.measure}, random-effects)</text>',
    ]
    y = header + 10
    # pooled vertical line
    pxm = px(result.pooled_log)
    parts.append(f'<line x1="{pxm}" y1="{header}" x2="{pxm}" y2="{h-40}" stroke="#999" stroke-dasharray="4"/>')
    for e in effects:
        lv = math_log(e.estimate)
        llo = math_log(e.ci_low)
        lhi = math_log(e.ci_high)
        # weight-scaled box width
        bw = max(4, int(40 * e.weight / max(x.weight for x in effects)))
        parts.append(
            f'<g transform="translate(0,{y})">'
            f'<text x="12" y="14" font-family="sans-serif" font-size="11">{e.study_id}</text>'
            f'<line x1="{px(llo)}" y1="10" x2="{px(lhi)}" y2="10" stroke="#333"/>'
            f'<rect x="{px(lv)-bw/2}" y="6" width="{bw}" height="8" fill="#2255aa"/>'
            f'<text x="{x1+12}" y="14" font-family="sans-serif" font-size="10" '
            f'>{e.estimate:.2f} ({e.ci_low:.2f}-{e.ci_high:.2f})</text>'
            f"</g>"
        )
        y += row_h
    # pooled diamond
    y += 6
    dl, dh = result.pooled_log - result.pooled_se * 1.96, result.pooled_log + result.pooled_se * 1.96
    pxl, pxh = px(dl), px(dh)
    parts.append(
        f'<polygon points="{pxl},{y} {pxm},{y-8} {pxh},{y} {pxm},{y+8}" fill="#cc0000" opacity="0.8"/>'
    )
    parts.append(
        f'<text x="12" y="{y+4}" font-family="sans-serif" font-size="11" font-weight="bold">'
        f'Pooled {result.measure} = {result.pooled_estimate:.2f}</text>'
    )
    parts.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return path


def math_log(x):
    import math
    return math.log(x)
