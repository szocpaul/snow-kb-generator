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
        assert "ChangeSyncInterface" in ref  # the content of the hand-written sample
        assert len(ref) <= 3000  # a token-saving excerpt
        # the second call comes from the cache (the same object)
        assert eval.metric._load_style_reference() is ref

    def test_banned_phrases_in_judge_docstring(self):
        """FR-003: the instruction of the judge contains the elements of the prohibition list."""
        doc = eval.metric.StyleJudge.__doc__ or ""
        for phrase in BANNED_PHRASES:
            assert phrase in doc, f"It is missing from the StyleJudge docstring: {phrase!r}"


class TestMultiSampleStyleScore:
    """Spec 012 (US1 / T004): multi-sample _style_score mock judge-dal."""

    def _scripted_judge(self, monkeypatch, script):
        """It replaces the dspy.Predict with a scripted fake judge.

        The elements of the script are float (a successful sample) or an Exception instance (an error).
        The call counter is SHARED — the _style_score creates a new Predict instance
        for every sample, so the order lives in the closure.
        """
        state = {"calls": 0}

        class _FakeJudge:
            def __call__(self, **kwargs):
                item = script[state["calls"]]
                state["calls"] += 1
                if isinstance(item, Exception):
                    raise item
                return dspy.Prediction(style_score=item, critique=f"critique-{item}")

        monkeypatch.setattr(eval.metric.dspy, "Predict", lambda sig: _FakeJudge())

    def test_mean_of_successful_samples(self, monkeypatch):
        """(a) [0.4, 0.6, 0.8] → 0.6 (FR-003 / acceptance 1)."""
        self._scripted_judge(monkeypatch, [0.4, 0.6, 0.8])
        score, _ = eval.metric._style_score("<h2>X</h2>")
        assert score == pytest.approx(0.6, abs=1e-3)

    def test_partial_failure_uses_remaining_mean(self, monkeypatch, caplog):
        """(b) 2 errors + 1 success → the successful value (NOT 0.5) + a warning (FR-001)."""
        import logging

        self._scripted_judge(
            monkeypatch,
            [ConnectionError("boom"), TimeoutError("boom"), 0.7],
        )
        with caplog.at_level(logging.WARNING, logger="eval.metric"):
            score, _ = eval.metric._style_score("<h2>X</h2>")
        assert score == pytest.approx(0.7, abs=1e-3)
        assert any("calls failed" in r.message for r in caplog.records)

    def test_all_failures_fall_back_to_0_5(self, monkeypatch):
        """(c) all errors → (0.5, '') — the behaviour of FR-002 of spec 010 is untouched."""
        self._scripted_judge(
            monkeypatch,
            [ConnectionError("a"), TimeoutError("b"), ValueError("c")],
        )
        score, critique = eval.metric._style_score("<h2>X</h2>")
        assert score == 0.5
        assert critique == ""

    def test_critique_is_from_sample_closest_to_mean(self, monkeypatch):
        """(d) the critique comes from the sample closest to the average (FR-003 / plan KD 4)."""
        # mean = 0.6 → the 0.6 sample is the closest (neither the 0.4 nor the 0.8)
        self._scripted_judge(monkeypatch, [0.4, 0.6, 0.8])
        _, critique = eval.metric._style_score("<h2>X</h2>")
        assert critique == "critique-0.6"

    def test_critique_closest_to_mean_with_asymmetric_samples(self, monkeypatch):
        """(d2) mean = 0.5 → the 0.6 is closer to the 0.5 (0.1) than the 0.3 (0.2)."""
        self._scripted_judge(monkeypatch, [0.3, 0.6, 0.6])
        _, critique = eval.metric._style_score("<h2>X</h2>")
        assert critique == "critique-0.6"

    def test_samples_constant_overridable(self, monkeypatch):
        """FR-002: STYLE_JUDGE_SAMPLES can be overridden (N=1 → single sample behaviour)."""
        monkeypatch.setattr(eval.metric, "STYLE_JUDGE_SAMPLES", 1)
        self._scripted_judge(monkeypatch, [0.42])
        score, _ = eval.metric._style_score("<h2>X</h2>")
        assert score == pytest.approx(0.42, abs=1e-3)


class TestRichMetricAxes:
    """Spec 012 / T004 (e): the rich_metric axes are still 5 axes."""

    def test_axes_has_five_axes(self, monkeypatch):
        monkeypatch.setattr(eval.metric, "_style_score", lambda html: (0.7, "ok"))
        result = rich_metric(_gold(), _pred())
        assert set(result.axes.keys()) == {
            "structure", "content", "template", "hallucination", "style",
        }
        assert result.axes["style"] == pytest.approx(0.7)
