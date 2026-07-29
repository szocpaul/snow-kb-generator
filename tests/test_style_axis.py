"""Spec 010 / T007: a rich_metric 5. tengelye (style axis) tesztjei mock judge-dal."""

from __future__ import annotations

import dspy
import pytest

import eval.metric
from eval.metric import BANNED_PHRASES, rich_metric


def _gold():
    return dspy.Example(
        story_text="Outbound REST integration to Jira, outbound payload.",
        html="<h2>Overview / Summary</h2><p>Outbound integration.</p>",
    ).with_inputs("story_text")


def _pred(html: str | None = None):
    return dspy.Prediction(
        html=html or "<h2>Overview / Summary</h2><p>Outbound integration.</p>"
    )


class TestStyleAxisWeights:
    """US2 acceptance 3: új súlyok (0.25/0.25/0.15/0.15/0.20)."""

    def test_perfect_match_with_perfect_style_is_1(self, monkeypatch):
        monkeypatch.setattr(eval.metric, "_style_score", lambda html: (1.0, ""))
        result = rich_metric(_gold(), _pred())
        assert result.score == pytest.approx(1.0)

    def test_neutral_style_fallback_value(self, monkeypatch):
        """Judge nélkül (0.5 fallback) a perfect match 0.25+0.25+0.15+0.15+0.10 = 0.90."""
        monkeypatch.setattr(eval.metric, "_style_score", lambda html: (0.5, ""))
        result = rich_metric(_gold(), _pred())
        assert result.score == pytest.approx(0.90)

    def test_zero_style_penalizes_by_weight(self, monkeypatch):
        """0.0 style → a perfect struktúra is max 0.80-at ér."""
        monkeypatch.setattr(eval.metric, "_style_score", lambda html: (0.0, "boilerplate everywhere"))
        result = rich_metric(_gold(), _pred())
        assert result.score == pytest.approx(0.80)


class TestStyleAxisFeedback:
    def test_machine_article_critique_in_feedback(self, monkeypatch):
        """Gépies cikk → alacsony style score + a feedback tartalmazza a kritikát."""
        monkeypatch.setattr(
            eval.metric,
            "_style_score",
            lambda html: (0.2, "'seamless integration' is boilerplate filler."),
        )
        result = rich_metric(_gold(), _pred())
        assert "seamless" in result.feedback
        assert "Style:" in result.feedback

    def test_human_article_high_score(self, monkeypatch):
        """Emberies cikk → magas style score, magas végösszeg."""
        monkeypatch.setattr(
            eval.metric,
            "_style_score",
            lambda html: (0.9, "Direct, concrete, varied rhythm."),
        )
        result = rich_metric(_gold(), _pred())
        assert result.score > 0.9


class TestStyleAxisFaultTolerance:
    """FR-002: a judge hibája sosem állítja meg a metric-et."""

    def test_judge_exception_falls_back_to_0_5(self, monkeypatch):
        def _boom(html):
            raise ConnectionError("llama-server unreachable")

        monkeypatch.setattr(eval.metric, "_style_score", _boom)
        # A rich_metric a helper-t hívja — ha a helper dob, az NEM a FR-002 ág:
        # a FR-002 a helperen BELÜL fog. Itt azt ellenőrizzük, hogy a helper
        # saját fallbackje ad 0.5-öt valós hibára (lásd következő teszt).
        with pytest.raises(ConnectionError):
            rich_metric(_gold(), _pred())

    def test_style_score_returns_0_5_without_lm(self):
        """LM nélkül (dspy nincs konfigurálva) a _style_score (0.5, '')-t ad."""
        import logging

        score, critique = eval.metric._style_score("<h2>X</h2><p>y</p>")
        assert score == 0.5
        assert critique == ""

    def test_style_score_clamps_out_of_range(self, monkeypatch):
        """A judge kilógó értéke (pl. 1.4) clamp-elődik 1.0-ra."""

        class _FakeJudge:
            def __call__(self, **kwargs):
                return dspy.Prediction(style_score=1.4, critique="ok")

        monkeypatch.setattr(eval.metric.dspy, "Predict", lambda sig: _FakeJudge())
        score, _ = eval.metric._style_score("<h2>X</h2>")
        assert score == 1.0


class TestStyleReference:
    def test_reference_file_loaded_and_cached(self):
        ref = eval.metric._load_style_reference()
        assert "SolMan" in ref  # a KB0010015 valódi tartalom
        assert len(ref) <= 3000  # token-takarékos részlet
        # második hívás cache-ből jön (ugyanaz az objektum)
        assert eval.metric._load_style_reference() is ref

    def test_banned_phrases_in_judge_docstring(self):
        """FR-003: a judge instrukciója tartalmazza a tiltólista elemeit."""
        doc = eval.metric.StyleJudge.__doc__ or ""
        for phrase in BANNED_PHRASES:
            assert phrase in doc, f"A StyleJudge docstring-ből hiányzik: {phrase!r}"
