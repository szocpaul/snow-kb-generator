"""test_audience_decision.py — spec 013 (US1+US2) tesztek, teszt-előbb sorrendben.

Lefedett viselkedések:
  US1: decide_audience típusos döntés (choice + probabilities + confidence),
       mockolt SDK-válaszokkal; egyértelmű eset magasabb confidence,
       mint a határeset; JSONL recording (FR-003); fail-open SDK-hibára
       és séma-eltérésre (FR-001); determinisztikus replay (SC-004).
  US2: resolve_audience küszöb-logika — alacsony confidence → "developer" +
       work_notes-jelzés a mért értékkel; küszöb felett → nincs jelzés;
       pontosan a küszöbön → fallback (T009: a határ a biztonságos irányba dől).
"""

from __future__ import annotations

import json

import pytest

from snow_kb.audience import (
    AUDIENCE_OPTIONS,
    decide_audience,
    resolve_audience,
    replay_client_from_recording,
)
from snow_kb.config import AudienceDecisionConfig, Settings

from typesafe_sdk import SystemOneResponse, TypeSafeError


# ---------------------------------------------------------------------------
# Segédek
# ---------------------------------------------------------------------------

CLEAR_DEVELOPER_STORY = """
# Story: STRY9000001
## Short Description
[Interface Mgmt]: Implement Scripted REST API endpoint for SAP IDOC ingestion
## Description
Created a Scripted REST API (/api/x_sap/idoc) with a Script Include that parses
the XML payload, validates Basic Auth credentials, and maps IDoc segments to
the u_vendor_invoice table. Includes unit tests with Postman collections.
"""

BORDERLINE_STORY = """
# Story: STRY9000002
## Short Description
Update the vendor invoice approval flow notification text
## Description
Adjusted the approval notification wording for finance users, and fixed the
underlying Flow Designer action that queries the vendor table via GlideRecord.
The notification template is user-facing; the flow change is technical.
"""


def make_response(choice: str, confidence: float, probabilities: dict) -> SystemOneResponse:
    """Valódi SDK válaszmodell mockolt payloadból."""
    return SystemOneResponse.model_validate({
        "model": "jev-1.13.0",
        "usage": {"input_tokens": 100, "output_tokens": 10},
        "answers": {
            "audience": {
                "type": "choice",
                "choice": choice,
                "confidence": confidence,
                "probabilities": probabilities,
            }
        },
    })


class FakeClient:
    """Minimális system_one mock: előre gyártott válasz vagy kivétel."""

    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def system_one(self, state, questions, *, model=None, **kwargs):
        self.calls.append({"state": state, "questions": questions, "model": model})
        if self.error is not None:
            raise self.error
        return self.response


def make_settings(tmp_path, *, enabled=True, threshold=0.7) -> Settings:
    return Settings(
        audience_decision=AudienceDecisionConfig(
            enabled=enabled,
            model="jev-1.13.0",
            confidence_threshold=threshold,
            recording_path=str(tmp_path / "audience_decisions.jsonl"),
        )
    )


# ---------------------------------------------------------------------------
# US1 — típusos döntés
# ---------------------------------------------------------------------------

class TestDecideAudience:
    def test_clear_developer_story_high_confidence(self, tmp_path):
        """Egyértelmű developer-story → developer, confidence ≥ 0.8 (US1 AS1)."""
        client = FakeClient(response=make_response(
            "developer", 0.96,
            {"developer": 0.96, "helpdesk": 0.03, "end-user": 0.01},
        ))
        decision = decide_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path), client=client)
        assert decision is not None
        assert decision.choice == "developer"
        assert decision.confidence >= 0.8
        assert set(decision.probabilities) == set(AUDIENCE_OPTIONS)
        assert decision.model == "jev-1.13.0"
        # a kérdés mindhárom opciót tartalmazza
        question = client.calls[0]["questions"]["audience"]
        criteria = question["criteria"] if isinstance(question, dict) else question.criteria
        assert set(criteria) == set(AUDIENCE_OPTIONS)

    def test_borderline_story_lower_confidence(self, tmp_path):
        """Határeset → mérhetően alacsonyabb confidence (US1 AS2)."""
        clear_client = FakeClient(response=make_response(
            "developer", 0.96,
            {"developer": 0.96, "helpdesk": 0.03, "end-user": 0.01},
        ))
        borderline_client = FakeClient(response=make_response(
            "developer", 0.55,
            {"developer": 0.55, "helpdesk": 0.30, "end-user": 0.15},
        ))
        clear = decide_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path), client=clear_client)
        borderline = decide_audience(BORDERLINE_STORY, make_settings(tmp_path), client=borderline_client)
        assert borderline is not None and borderline.confidence < 0.8
        assert borderline.confidence < clear.confidence

    def test_fail_open_on_sdk_error(self, tmp_path):
        """SDK-hiba (timeout/5xx/auth) → None + warning (FR-001, SC-003)."""
        client = FakeClient(error=TypeSafeError("simulated API outage"))
        decision = decide_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path), client=client)
        assert decision is None

    def test_fail_open_on_unexpected_schema(self, tmp_path):
        """Séma-eltérés (SDK-verzió) → ugyanaz a fail-open út (spec Edge Cases)."""

        class WeirdResponse:
            model = "jev-1.13.0"
            answers = {}  # hiányzik az 'audience' answer

        client = FakeClient(response=WeirdResponse())
        decision = decide_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path), client=client)
        assert decision is None

    def test_fail_open_when_api_key_missing(self, tmp_path, monkeypatch):
        """Nincs TYPESAFE_API_KEY → fail-open, nem kivétel."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        decision = decide_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path))
        assert decision is None


class TestRecording:
    def test_jsonl_recording_written(self, tmp_path):
        """FR-003: request hash + response + latency + modell, replay-kompatibilis JSONL."""
        settings = make_settings(tmp_path)
        client = FakeClient(response=make_response(
            "developer", 0.96,
            {"developer": 0.96, "helpdesk": 0.03, "end-user": 0.01},
        ))
        decide_audience(CLEAR_DEVELOPER_STORY, settings, client=client)

        path = tmp_path / "audience_decisions.jsonl"
        assert path.exists()
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        assert len(rows) == 1
        row = rows[0]
        assert isinstance(row["request_hash"], str) and len(row["request_hash"]) == 64
        assert row["model"] == "jev-1.13.0"
        assert "latency_ms" in row["response"]
        assert row["response"]["answers"]["audience"]["choice"] == "developer"

    def test_replay_is_deterministic(self, tmp_path):
        """SC-004: rögzített válasz replay-je ugyanazt a döntést adja, élő hívás nélkül."""
        settings = make_settings(tmp_path)
        client = FakeClient(response=make_response(
            "helpdesk", 0.81,
            {"developer": 0.15, "helpdesk": 0.81, "end-user": 0.04},
        ))
        live = decide_audience(CLEAR_DEVELOPER_STORY, settings, client=client)

        replay_client = replay_client_from_recording(tmp_path / "audience_decisions.jsonl")
        replayed = decide_audience(CLEAR_DEVELOPER_STORY, settings, client=replay_client)
        assert replayed == live  # frozen dataclass: teljes egyenlőség

        # Harmadik futtatás: ugyanaz a rögzített válasz → byte-identikus sor
        replay_client2 = replay_client_from_recording(tmp_path / "audience_decisions.jsonl")
        replayed2 = decide_audience(CLEAR_DEVELOPER_STORY, settings, client=replay_client2)
        assert replayed2 == live


# ---------------------------------------------------------------------------
# US2 — küszöb-logika (T009)
# ---------------------------------------------------------------------------

class TestResolveAudience:
    def test_low_confidence_falls_back_to_developer_with_note(self, tmp_path):
        """confidence < küszöb → developer + work_notes-jelzés a mért értékkel (US2 AS1)."""
        client = FakeClient(response=make_response(
            "end-user", 0.55,
            {"developer": 0.30, "helpdesk": 0.15, "end-user": 0.55},
        ))
        audience, note = resolve_audience(BORDERLINE_STORY, make_settings(tmp_path, threshold=0.7), client=client)
        assert audience == "developer"
        assert "0.55" in note  # a mért confidence a jelzésben

    def test_high_confidence_no_fallback(self, tmp_path):
        """confidence ≥ küszöb → a típusos döntés érvényes, nincs jelzés (US2 AS2)."""
        client = FakeClient(response=make_response(
            "helpdesk", 0.83,
            {"developer": 0.10, "helpdesk": 0.83, "end-user": 0.07},
        ))
        audience, note = resolve_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path), client=client)
        assert audience == "helpdesk"
        assert note == ""

    def test_exactly_at_threshold_falls_back(self, tmp_path):
        """T009: pontosan a küszöbön → fallback (a határ a biztonságos irányba dől)."""
        client = FakeClient(response=make_response(
            "helpdesk", 0.7,
            {"developer": 0.20, "helpdesk": 0.70, "end-user": 0.10},
        ))
        audience, note = resolve_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path, threshold=0.7), client=client)
        assert audience == "developer"
        assert note != ""

    def test_disabled_returns_none_and_never_calls_client(self, tmp_path):
        """FR-004: enabled=false → generatív út (None), az SDK-t meg sem hívja."""
        client = FakeClient(response=make_response(
            "developer", 0.96, {"developer": 0.96, "helpdesk": 0.03, "end-user": 0.01}
        ))
        audience, note = resolve_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path, enabled=False), client=client)
        assert audience is None
        assert note == ""
        assert client.calls == []

    def test_fail_open_returns_none(self, tmp_path):
        """SDK-kiesés → (None, "") — a pipeline a generatív audience-re esik vissza."""
        client = FakeClient(error=TypeSafeError("simulated outage"))
        audience, note = resolve_audience(CLEAR_DEVELOPER_STORY, make_settings(tmp_path), client=client)
        assert audience is None
        assert note == ""
