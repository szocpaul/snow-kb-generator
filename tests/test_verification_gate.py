"""test_verification_gate.py — a production push-gate tesztjei (spec 014, US2, T008).

The gate runs BEFORE servicenow_client._create_kb_article_live (FR-004): the
validates the named component names of the article against the instance, and the config
acts according to the behavior (flag / strip / block). Fail-open is mandatory (FR-002).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import dspy
import pytest

from snow_kb.config import ServiceNowConfig, Settings, VerificationGateConfig
from snow_kb.pipeline import generate_kb_article
from snow_kb.schemas import KBArticle, StoryData
from snow_kb.verification import NameVerdict, VerificationResult


@pytest.fixture
def sample_story() -> StoryData:
    return StoryData(
        number="STRY0012345",
        short_description="Jira integration fix",
        description="The JiraInboundUtils Script Include is failing.",
        state="Closed Complete",
        assignment_group="integration_team",
    )


def _make_client(story: StoryData) -> MagicMock:
    client = MagicMock()
    client.get_story.return_value = story
    client.create_kb_article.return_value = "kb_sys_id_1"
    client.get_update_set_changes.return_value = ("", "")
    client.find_existing_kb_article.return_value = None
    client.get_team_template.return_value = "<p>Mock Template</p>"
    return client


def _make_program(html: str) -> MagicMock:
    program = MagicMock()
    program.return_value = dspy.Prediction(
        article=KBArticle(title="Fixing the Jira integration", html=html,
                          category="General", knowledge_base_id="kb1")
    )
    return program


def _gate_settings(tmp_path, *, enabled=True, behavior="flag") -> Settings:
    return Settings(
        dry_run=False,
        snow=ServiceNowConfig(knowledge_base_id="kb1", default_category="IT"),
        verification_gate=VerificationGateConfig(
            enabled=enabled,
            behavior=behavior,
            model="jev-1.13.0",
            recording_path=str(tmp_path / "verification.jsonl"),
            spotcheck_cache_path=str(tmp_path / "spotcheck.json"),
        ),
    )


class _StubChecker:
    """SpotChecker substitute: exists for the known names, not_exists for the rest."""

    def __init__(self, known=(), unknown=False):
        self.known = {k.casefold() for k in known}
        self.unknown = unknown
        self.calls = []

    def check(self, name, kind="quoted"):
        self.calls.append(name)
        if self.unknown:
            return NameVerdict(name=name, status="unknown", confidence=0.0,
                               evidence="mock outage", layer="spotcheck")
        status = "exists" if name.casefold() in self.known else "not_exists"
        return NameVerdict(name=name, status=status, confidence=1.0,
                           evidence="mock", layer="spotcheck")


class TestVerificationGate:
    def test_disabled_gate_untouched(self, sample_story, tmp_path):
        """enabled=False → the gate is inactive, the checker is not even called."""
        settings = _gate_settings(tmp_path, enabled=False)
        checker = _StubChecker()
        html = "<h2>Solution</h2><p>The 'FabricatedUtils' Script Include.</p>"
        result = generate_kb_article(
            "STRY0012345", _make_client(sample_story), settings,
            program=_make_program(html), push=True, spot_checker=checker,
        )
        assert checker.calls == []
        assert getattr(result, "verification_note", "") in ("", None)

    def test_flag_behavior_adds_work_note(self, sample_story, tmp_path):
        """US2 scenario 1 (default flag): the non-existent name gets a work_notes flag,
        the article goes out (create_kb_article is called)."""
        settings = _gate_settings(tmp_path, behavior="flag")
        checker = _StubChecker(known=["RealUtils"])
        html = ("<h2>Solution</h2><p>The 'RealUtils' and the 'FabricatedUtils' "
                "Script Include.</p>")
        result = generate_kb_article(
            "STRY0012345", _make_client(sample_story), settings,
            program=_make_program(html), push=True, spot_checker=checker,
        )
        client_note = getattr(result, "verification_note", "")
        assert "FabricatedUtils" in client_note
        assert "RealUtils" not in client_note
        # the html of the article is unchanged (flag does NOT strip)
        assert "FabricatedUtils" in result.html

    def test_real_names_pass_unchanged(self, sample_story, tmp_path):
        """US2 scenario 2: only real names → no signal, the article is unchanged."""
        settings = _gate_settings(tmp_path)
        checker = _StubChecker(known=["RealUtils"])
        html = "<h2>Solution</h2><p>The 'RealUtils' Script Include.</p>"
        result = generate_kb_article(
            "STRY0012345", _make_client(sample_story), settings,
            program=_make_program(html), push=True, spot_checker=checker,
        )
        assert getattr(result, "verification_note", "") in ("", None)

    def test_instance_unreachable_fail_open(self, sample_story, tmp_path):
        """US2 scenario 3 / FR-002: the instance is unreachable → the article goes out
        warninggal, a push NEM akad el."""
        settings = _gate_settings(tmp_path)
        checker = _StubChecker(unknown=True)
        html = "<h2>Solution</h2><p>The 'ValamiUtils' Script Include.</p>"
        client = _make_client(sample_story)
        result = generate_kb_article(
            "STRY0012345", client, settings,
            program=_make_program(html), push=True, spot_checker=checker,
        )
        client.create_kb_article.assert_called_once()
        # there is no block and no false "does not exist" signal either
        assert getattr(result, "verification_note", "") in ("", None)

    def test_block_behavior_raises(self, sample_story, tmp_path):
        """behavior=block (only with config): the push is blocked, create is NOT called."""
        settings = _gate_settings(tmp_path, behavior="block")
        checker = _StubChecker()  # semmit sem ismer
        html = "<h2>Solution</h2><p>The 'FabricatedUtils' Script Include.</p>"
        client = _make_client(sample_story)
        with pytest.raises(Exception, match="(?i)verif"):
            generate_kb_article(
                "STRY0012345", client, settings,
                program=_make_program(html), push=True, spot_checker=checker,
            )
        client.create_kb_article.assert_not_called()

    def test_strip_behavior_removes_names(self, sample_story, tmp_path):
        """behavior=strip (only with the config): the suspicious name is dropped from the html."""
        settings = _gate_settings(tmp_path, behavior="strip")
        checker = _StubChecker(known=["RealUtils"])
        html = ("<h2>Solution</h2><p>The 'RealUtils' and the 'FabricatedUtils' "
                "Script Include.</p>")
        result = generate_kb_article(
            "STRY0012345", _make_client(sample_story), settings,
            program=_make_program(html), push=True, spot_checker=checker,
        )
        assert "FabricatedUtils" not in result.html
        assert "RealUtils" in result.html

    def test_recording_written(self, sample_story, tmp_path):
        """FR-003: the decision is logged to a replay-compatible JSONL."""
        settings = _gate_settings(tmp_path)
        checker = _StubChecker()
        html = "<h2>Solution</h2><p>The 'FabricatedUtils' Script Include.</p>"
        generate_kb_article(
            "STRY0012345", _make_client(sample_story), settings,
            program=_make_program(html), push=True, spot_checker=checker,
        )
        rec = tmp_path / "verification.jsonl"
        assert rec.exists()
        row = json.loads(rec.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert row["story"] == "STRY0012345"
        assert row["behavior"] == "flag"
        names = {v["name"]: v["status"] for v in row["verdicts"]}
        assert names.get("FabricatedUtils") == "not_exists"
