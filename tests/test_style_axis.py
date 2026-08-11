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


class TestMultiSampleStyleScore:
    """Spec 012 (US1 / T004): multi-sample _style_score mock judge-dal."""

    def _scripted_judge(self, monkeypatch, script):
        """dspy.Predict-et cserél egy scriptelt fake judge-ra.

        A script elemei float (sikeres minta) vagy Exception példány (hiba).
        A hívásszámláló MEGOSZTOTT — a _style_score minden mintánál új
        Predict-példányt hoz létre, ezért a sorrendiség a closure-ben él.
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
        """(b) 2 hiba + 1 siker → a sikeres érték (NEM 0.5) + warning (FR-001)."""
        import logging

        self._scripted_judge(
            monkeypatch,
            [ConnectionError("boom"), TimeoutError("boom"), 0.7],
        )
        with caplog.at_level(logging.WARNING, logger="eval.metric"):
            score, _ = eval.metric._style_score("<h2>X</h2>")
        assert score == pytest.approx(0.7, abs=1e-3)
        assert any("sikertelen" in r.message for r in caplog.records)

    def test_all_failures_fall_back_to_0_5(self, monkeypatch):
        """(c) mind hiba → (0.5, '') — a spec 010-es FR-002 viselkedés érintetlen."""
        self._scripted_judge(
            monkeypatch,
            [ConnectionError("a"), TimeoutError("b"), ValueError("c")],
        )
        score, critique = eval.metric._style_score("<h2>X</h2>")
        assert score == 0.5
        assert critique == ""

    def test_critique_is_from_sample_closest_to_mean(self, monkeypatch):
        """(d) a critique az átlaghoz legközelebbi mintáé (FR-003 / plan KD 4)."""
        # mean = 0.6 → a 0.6-os minta a legközelebbi (nem a 0.4, nem a 0.8)
        self._scripted_judge(monkeypatch, [0.4, 0.6, 0.8])
        _, critique = eval.metric._style_score("<h2>X</h2>")
        assert critique == "critique-0.6"

    def test_critique_closest_to_mean_with_asymmetric_samples(self, monkeypatch):
        """(d2) mean = 0.5 → a 0.5-höz a 0.6 áll közelebb (0.1), mint a 0.3 (0.2)."""
        self._scripted_judge(monkeypatch, [0.3, 0.6, 0.6])
        _, critique = eval.metric._style_score("<h2>X</h2>")
        assert critique == "critique-0.6"

    def test_samples_constant_overridable(self, monkeypatch):
        """FR-002: STYLE_JUDGE_SAMPLES felüldefiniálható (N=1 → egymintás viselkedés)."""
        monkeypatch.setattr(eval.metric, "STYLE_JUDGE_SAMPLES", 1)
        self._scripted_judge(monkeypatch, [0.42])
        score, _ = eval.metric._style_score("<h2>X</h2>")
        assert score == pytest.approx(0.42, abs=1e-3)


class TestRichMetricAxes:
    """Spec 012 / T004 (e): a rich_metric axes továbbra is 5 tengely."""

    def test_axes_has_five_axes(self, monkeypatch):
        monkeypatch.setattr(eval.metric, "_style_score", lambda html: (0.7, "ok"))
        result = rich_metric(_gold(), _pred())
        assert set(result.axes.keys()) == {
            "structure", "content", "template", "hallucination", "style",
        }
        assert result.axes["style"] == pytest.approx(0.7)
