"""Tests for the forest plot renderer (in-memory SVG, no network).

``evidence_synth.forest.forest_plot`` writes a file and returns the path, so
each test renders into a tmp_path and asserts on the resulting markup:
XML escaping of free-text fields, the empty-effects path, and the
non-positive-estimate guard.
"""
import xml.dom.minidom as minidom

import pytest

from evidence_synth.extraction import EffectSize, MetaResult
from evidence_synth.forest import forest_plot


def _result():
    return MetaResult(
        pooled_log=0.0,
        pooled_se=0.1,
        pooled_estimate=1.0,
        pooled_ci_low=0.82,
        pooled_ci_high=1.22,
        tau2=0.01,
        i2=0.2,
        q=3.0,
        q_pvalue=0.08,
        k=2,
        measure="OR",
    )


def _effect(study_id="S1", estimate=0.8, ci_low=0.6, ci_high=1.05, weight=1.0):
    return EffectSize(
        study_id=study_id,
        measure="OR",
        estimate=estimate,
        ci_low=ci_low,
        ci_high=ci_high,
        weight=weight,
    )


def test_study_id_is_xml_escaped(tmp_path):
    # A study id carrying markup characters must be escaped, not spliced in
    # raw, or the resulting SVG is malformed / injectable.
    effects = [_effect(study_id='A & B <script>alert("x")</script>')]
    out = forest_plot(effects, _result(), str(tmp_path / "forest.svg"))
    svg = open(out, encoding="utf-8").read()

    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
    assert "&amp;" in svg
    # the output is still well-formed XML
    minidom.parse(out)


def test_measure_name_is_xml_escaped(tmp_path):
    result = _result()
    result.measure = 'OR & <b>HR</b>'
    out = forest_plot([_effect()], result, str(tmp_path / "forest.svg"))
    svg = open(out, encoding="utf-8").read()
    assert "&lt;b&gt;HR&lt;/b&gt;" in svg
    minidom.parse(out)


def test_empty_effects_renders_valid_svg(tmp_path):
    # An empty effect list used to raise ValueError from min()/max().
    out = forest_plot([], _result(), str(tmp_path / "forest.svg"))
    svg = open(out, encoding="utf-8").read()

    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "nothing to plot" in svg
    minidom.parse(out)


def test_empty_effects_svg_has_sane_height(tmp_path):
    out = forest_plot([], _result(), str(tmp_path / "forest.svg"))
    svg = open(out, encoding="utf-8").read()
    # header (40) + no rows + 80 tail
    assert 'height="120"' in svg


def test_nonpositive_estimate_raises_clear_error(tmp_path):
    # Log-space plotting cannot take log(0) or log(<0); surface a readable
    # error instead of a bare math domain error deep in the renderer.
    effects = [_effect(study_id="S1", estimate=0.0)]
    with pytest.raises(ValueError, match="must be positive"):
        forest_plot(effects, _result(), str(tmp_path / "forest.svg"))


def test_negative_ci_bound_raises_clear_error(tmp_path):
    effects = [_effect(study_id="S2", ci_low=-0.5)]
    with pytest.raises(ValueError, match="ci_low"):
        forest_plot(effects, _result(), str(tmp_path / "forest.svg"))


def test_valid_effects_render_and_parse(tmp_path):
    effects = [
        _effect(study_id="S1", estimate=0.8, weight=1.0),
        _effect(study_id="S2", estimate=1.2, weight=2.0),
    ]
    out = forest_plot(effects, _result(), str(tmp_path / "forest.svg"))
    minidom.parse(out)
    svg = open(out, encoding="utf-8").read()
    assert "S1" in svg and "S2" in svg
