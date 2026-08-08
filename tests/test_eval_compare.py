"""test_eval_compare.py — a T012 gate (eval/compare.py) tesztjei."""

from __future__ import annotations

import json

import pytest

from eval.compare import compare, load_axis_averages

BASE_AXES = {"structure": 0.6, "content": 0.8, "template": 0.9, "hallucination": 1.0, "style": 0.45}


def _write_run(path, axes):
    path.write_text(json.dumps({
        "average_score": sum(axes.values()) / len(axes),
        "axis_averages": axes,
        "per_example": [{"score": 0.7, "axes": axes, "feedback": "..."}],
    }), encoding="utf-8")


class TestCompareGate:
    """The exit logic of the T012 thresholds (style >= +0.05, the others max -0.02)."""

    def test_green_when_style_improves_and_others_hold(self, tmp_path, capsys):
        _write_run(tmp_path / "base.json", BASE_AXES)
        _write_run(tmp_path / "opt.json", {**BASE_AXES, "style": 0.55})
        assert compare(tmp_path / "base.json", tmp_path / "opt.json") is True

    def test_red_when_style_delta_too_small(self, tmp_path):
        _write_run(tmp_path / "base.json", BASE_AXES)
        _write_run(tmp_path / "opt.json", {**BASE_AXES, "style": 0.48})
        assert compare(tmp_path / "base.json", tmp_path / "opt.json") is False

    def test_red_when_other_axis_regresses(self, tmp_path):
        _write_run(tmp_path / "base.json", BASE_AXES)
        _write_run(tmp_path / "opt.json", {**BASE_AXES, "style": 0.60, "content": 0.70})
        assert compare(tmp_path / "base.json", tmp_path / "opt.json") is False

    def test_legacy_file_without_axes_fails_loudly(self, tmp_path):
        """With a pre-T010c file (without the axes) the gate intentionally fails."""
        (tmp_path / "old.json").write_text(json.dumps(
            {"average_score": 0.7, "per_example": [{"score": 0.7, "feedback": "x"}]}
        ), encoding="utf-8")
        with pytest.raises(SystemExit):
            load_axis_averages(tmp_path / "old.json")

    def test_fallback_computes_averages_from_per_example(self, tmp_path):
        """If there is no top level axis_averages, it computes it from the per_example."""
        _write_run(tmp_path / "base.json", BASE_AXES)
        data = json.loads((tmp_path / "base.json").read_text())
        del data["axis_averages"]
        (tmp_path / "base2.json").write_text(json.dumps(data), encoding="utf-8")
        avg = load_axis_averages(tmp_path / "base2.json")
        assert avg["style"] == pytest.approx(0.45)
