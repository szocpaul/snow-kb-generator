"""tests/test_verification_gate_client.py — spec 015 T010 (US3): a gate az
ÍRÁST VÉGZŐ komponensben (servicenow_client._create_kb_article_live) él.

Követelmények (spec US3 + FR-004/FR-005):
  1. a KÖZVETLEN _create_kb_article_live hívás is gated (a pipeline megkerülve);
  2. normál pipeline-futásban PONTOSAN 1 gate-döntés + 1 recording-bejegyzés
     (nincs dupla védelem — a pipeline-rétegű hívás megszűnt);
  3. fail-open a kliens-beli gate-ben is (instance-kiesés → a cikk kimegy);
  4. a régi pipeline-szintű _apply_verification_gate megszűnt.

FAIL implementáció előtt (T010 → T011 teszt-előbb sorrend).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import dspy
import pytest

import snow_kb.pipeline as pipeline_mod
from snow_kb.config import ServiceNowConfig, Settings, VerificationGateConfig
from snow_kb.errors import VerificationBlocked
from snow_kb.pipeline import generate_kb_article
from snow_kb.schemas import KBArticle
from snow_kb.servicenow_client import ServiceNowClient
from snow_kb.verification import NameVerdict


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
    """SpotChecker-helyettesítő (a 014-es tesztminta szerint)."""

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


class _StubJevClient:
    """A kalibrált réteg helyettesítője: minden homályos névre 'no' (fabrikált)."""

    def system_one(self, state=None, questions=None, model=None):
        answer = MagicMock()
        answer.confidence = 0.99
        answer.choice = "no"
        response = MagicMock()
        response.answers = {"refers": answer}
        return response


def _live_client(settings: Settings, *, story_record: dict | None = None) -> ServiceNowClient:
    """VALÓDI ServiceNowClient, stubolt HTTP-vel (a gate a kliensben fut)."""
    client = ServiceNowClient(settings)
    calls: list[tuple[str, str]] = []
    story_record = story_record or {
        "number": "STRY0012345",
        "short_description": "Webhook integration",
        "description": "A FabricatedUtils Script Include hibázik.",
        "state": "Closed Complete",
        "assignment_group": "integration_team",
        "sys_id": "story_sys_1",
    }

    def fake_request(method, url, *, params=None, json=None):
        calls.append((method, url))
        resp = MagicMock()
        tail = url.rstrip("/").split("/")[-1]
        # a story-tábla neve instance-függő ("story" alapértelmezés / "rm_story")
        if method == "GET" and tail in ("story", "rm_story"):
            resp.json.return_value = {"result": [story_record]}
        elif method == "GET" and "/sys_update_set" in url:
            resp.json.return_value = {"result": []}
        elif method == "GET" and "/kb_knowledge_base" in url:
            resp.json.return_value = {"result": []}
        elif method == "GET" and "/kb_knowledge" in url:
            resp.json.return_value = {"result": []}
        elif method == "POST" and url.rstrip("/").endswith("/kb_knowledge"):
            resp.json.return_value = {"result": {"sys_id": "kb_new_1"}}
        else:
            resp.json.return_value = {"result": {}}
        return resp

    client._request = fake_request  # type: ignore[method-assign]
    client._http_calls = calls  # type: ignore[attr-defined]
    return client


def _article(html: str) -> KBArticle:
    return KBArticle(title="Webhook integration fix", html=html,
                     category="General", knowledge_base_id="kb1")


class TestDirectClientCallIsGated:
    """US3 scenario 1: a pipeline-t megkerülő KÖZVETLEN kliens-hívás is gated."""

    def test_direct_live_call_flags_fabricated_name(self, tmp_path):
        settings = _gate_settings(tmp_path, behavior="flag")
        client = _live_client(settings)
        checker = _StubChecker()  # semmit sem ismer → minden jelölt not_exists
        article = _article("<h2>Megoldás</h2><p>A 'FabricatedUtils' Script Include.</p>")
        sys_id = client._create_kb_article_live(
            article, story_sys_id="story_sys_1",
            story_text="A FabricatedUtils Script Include hibázik.",
            spot_checker=checker, decision_client=_StubJevClient(),
        )
        assert sys_id == "kb_new_1"  # a cikk kimegy (flag NEM blokkol)
        assert "FabricatedUtils" in getattr(article, "verification_note", "")
        assert checker.calls  # a gate TÉNYLEG lefutott a kliensben

    def test_direct_live_call_block_behavior(self, tmp_path):
        settings = _gate_settings(tmp_path, behavior="block")
        client = _live_client(settings)
        article = _article("<h2>Megoldás</h2><p>A 'FabricatedUtils' Script Include.</p>")
        with pytest.raises(VerificationBlocked):
            client._create_kb_article_live(
                article, story_text="ctx",
                spot_checker=_StubChecker(), decision_client=_StubJevClient(),
            )
        # a POST NEM futott le
        assert not any(m == "POST" and u.endswith("/kb_knowledge")
                       for m, u in client._http_calls)

    def test_client_gate_fail_open_on_outage(self, tmp_path):
        """FR-005: instance-kiesés → fail-open, a cikk kimegy warninggal."""
        settings = _gate_settings(tmp_path, behavior="block")  # még block módban is!
        client = _live_client(settings)
        article = _article("<h2>Megoldás</h2><p>A 'ValamiUtils' Script Include.</p>")
        sys_id = client._create_kb_article_live(
            article, story_text="ctx",
            spot_checker=_StubChecker(unknown=True),
        )
        assert sys_id == "kb_new_1"
        assert getattr(article, "verification_note", "") in ("", None)


class TestPipelineSingleGate:
    """US3 scenario 2: normál pipeline-futásban PONTOSAN 1 döntés + 1 recording."""

    def test_exactly_one_decision_and_one_recording(self, tmp_path):
        settings = _gate_settings(tmp_path, behavior="flag")
        client = _live_client(settings)
        checker = _StubChecker(known=["RealUtils"])
        html = ("<h2>Megoldás</h2><p>A 'RealUtils' és a 'FabricatedUtils' "
                "Script Include.</p>")
        program = MagicMock()
        program.return_value = dspy.Prediction(article=_article(html))
        result = generate_kb_article(
            "STRY0012345", client, settings,
            program=program, push=True,
            spot_checker=checker, decision_client=_StubJevClient(),
        )
        # 1 recording-sor
        rec = tmp_path / "verification.jsonl"
        lines = rec.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1, f"dupla recording: {len(lines)} sor"
        row = json.loads(lines[0])
        assert row["story"] == "STRY0012345"
        # 1 gate-döntés: a checker egyszeri gate-futáshoz tartozó hívásai
        flagged = {v["name"] for v in row["verdicts"] if v["status"] == "not_exists"}
        assert "FabricatedUtils" in flagged
        assert "FabricatedUtils" in getattr(result, "verification_note", "")

    def test_pipeline_level_gate_removed(self):
        """A régi pipeline-rétegű gate-függvény megszűnt (nincs dupla védelem)."""
        assert not hasattr(pipeline_mod, "_apply_verification_gate")
