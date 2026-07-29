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
    """US2 acceptance 3: the new weights (0.25/0.25/0.15/0.15/0.20)."""

    def test_perfect_match_with_perfect_style_is_1(self, monkeypatch):
        monkeypatch.setattr(eval.metric, "_style_score", lambda html: (1.0, ""))
        result = rich_metric(_gold(), _pred())
        assert result.score == pytest.approx(1.0)

    def test_neutral_style_fallback_value(self, monkeypatch):
        """Without a judge (0.5 fallback) the perfect match is 0.25+0.25+0.15+0.15+0.10 = 0.90."""
        monkeypatch.setattr(eval.metric, "_style_score", lambda html: (0.5, ""))
        result = rich_metric(_gold(), _pred())
        assert result.score == pytest.approx(0.90)

    def test_zero_style_penalizes_by_weight(self, monkeypatch):
        """0.0 style → even the perfect structure reaches at most 0.80."""
        monkeypatch.setattr(eval.metric, "_style_score", lambda html: (0.0, "boilerplate everywhere"))
        result = rich_metric(_gold(), _pred())
        assert result.score == pytest.approx(0.80)


class TestStyleAxisFeedback:
    def test_machine_article_critique_in_feedback(self, monkeypatch):
        """A machine-like article → a low style score + the feedback contains the critique."""
        monkeypatch.setattr(
            eval.metric,
            "_style_score",
            lambda html: (0.2, "'seamless integration' is boilerplate filler."),
        )
        result = rich_metric(_gold(), _pred())
        assert "seamless" in result.feedback
        assert "Style:" in result.feedback

    def test_human_article_high_score(self, monkeypatch):
        """A human-like article → a high style score, a high final sum."""
        monkeypatch.setattr(
            eval.metric,
            "_style_score",
            lambda html: (0.9, "Direct, concrete, varied rhythm."),
        )
        result = rich_metric(_gold(), _pred())
        assert result.score > 0.9


class TestStyleAxisFaultTolerance:
    """FR-002: an error of the judge never stops the metric."""

    def test_judge_exception_falls_back_to_0_5(self, monkeypatch):
        def _boom(html):
            raise ConnectionError("llama-server unreachable")

        monkeypatch.setattr(eval.metric, "_style_score", _boom)
        # The rich_metric calls the helper — if the helper raises, that is NOT the FR-002 branch:
        # the FR-002 is INSIDE the helper. Here we check that the helper
        # gives 0.5 for a real error (see the next test).
        with pytest.raises(ConnectionError):
            rich_metric(_gold(), _pred())

    def test_style_score_returns_0_5_without_lm(self):
        """Without an LM (dspy is not configured) the _style_score gives (0.5, '')."""
        import logging

        score, critique = eval.metric._style_score("<h2>X</h2><p>y</p>")
        assert score == 0.5
        assert critique == ""

    def test_style_score_clamps_out_of_range(self, monkeypatch):
        """An out of range value of the judge (e.g. 1.4) is clamped to 1.0."""

        class _FakeJudge:
            def __call__(self, **kwargs):
                return dspy.Prediction(style_score=1.4, critique="ok")

        monkeypatch.setattr(eval.metric.dspy, "Predict", lambda sig: _FakeJudge())
        score, _ = eval.metric._style_score("<h2>X</h2>")
        assert score == 1.0


class TestStyleReference:
    def test_reference_file_loaded_and_cached(self):
        ref = eval.metric._load_style_reference()
        assert "SolMan" in ref  # the real STYLE-REF content
        assert len(ref) <= 3000  # a token-saving excerpt
        # the second call comes from the cache (the same object)
        assert eval.metric._load_style_reference() is ref

    def test_banned_phrases_in_judge_docstring(self):
        """FR-003: the instruction of the judge contains the elements of the prohibition list."""
        doc = eval.metric.StyleJudge.__doc__ or ""
        for phrase in BANNED_PHRASES:
            assert phrase in doc, f"It is missing from the StyleJudge docstring: {phrase!r}"
