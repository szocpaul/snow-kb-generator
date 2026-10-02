"""test_context_selection.py — spec 016 T004/T006: a válogató modul tesztjei (teszt-előbb).

Lefedett viselkedések (tasks.md T004):
  - nyilvánvaló zaj → hide/summarize
  - releváns darab → show
  - alacsony confidence → show (recall-védelem, '<' operátor — a határérték a
    biztonságos irányba dől)
  - SDK-hiba → minden darab show (fail-open)
  - story-főtörzs sosem hide (FR-004)
  - recording-bejegyzés séma (FR-003)
  - summarize a lokális Qwen endpointon, endpoint-hiba → fail-open show
  - pipeline-bekötés: enabled flag (FR-006), a gate az EREDETI kontextust kapja
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from snow_kb.config import ContextSelectionConfig, Settings, ServiceNowConfig

from snow_kb.context_selection import (  # noqa: E402,F401  # T004: FAIL, amíg a T005 modul nincs meg
    ContextPiece,
    apply_decisions,
    classify_pieces,
    select_context,
    split_context_into_pieces,
    split_story_into_pieces,
    split_update_set_into_pieces,
)


# ---------------------------------------------------------------------------
# Fake system_one client és fixture-ök
# ---------------------------------------------------------------------------

def _score_response(score: float, confidence: float) -> SimpleNamespace:
    """Score system_one válasz namespace-alakja (a jev payload_to_namespace mintára)."""
    legend = {0: "noise", 1: "supporting", 2: "essential"}
    # Egyszerű pontsúly: a teljes tömeg a kerekített szinten
    level = min(2, max(0, round(score)))
    probs = {i: (1.0 if i == level else 0.0) for i in range(3)}
    return SimpleNamespace(
        model="jev-1.13.0",
        answers={
            "relevance": SimpleNamespace(
                type="score",
                score=score,
                confidence=confidence,
                legend=legend,
                probabilities=probs,
            )
        },
    )


class FakeScoreClient:
    """Scriptelt system_one client: sorrendben adja a válaszokat."""

    def __init__(self, responses: list[SimpleNamespace] | None = None,
                 error: Exception | None = None) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.calls: list[dict] = []

    def system_one(self, state, questions, *, model=None, **kwargs):
        self.calls.append({"state": state, "questions": questions, "model": model})
        if self.error is not None:
            raise self.error
        if not self.responses:
            raise AssertionError("Nincs több scriptelt válasz — váratlan hívás")
        return self.responses.pop(0)


def _settings(tmp_path, **overrides) -> Settings:
    cfg_kwargs = {
        "enabled": True,
        "model": "jev-1.13.0",
        "hide_below": 0.25,
        "summarize_below": 0.60,
        "min_confidence": 0.6,
        "recording_path": str(tmp_path / "recording.jsonl"),
        "summarizer_endpoint": "http://127.0.0.1:9/v1",  # szándékosan elérhetetlen
    }
    cfg_kwargs.update(overrides)
    return Settings(
        dry_run=False,
        snow=ServiceNowConfig(knowledge_base_id="kb1"),
        context_selection=ContextSelectionConfig(**cfg_kwargs),
    )


JSON_STORY = json.dumps({
    "number": "STRY0010099",
    "short_description": "[Interface Mgmt]: Jira webhook inbound integration",
    "description": "Implemented inbound webhook creating Incidents from Jira payloads.",
    "acceptance_criteria": "1. Endpoint accepts POST. 2. Incident created.",
    "u_technical_specification": "Scripted REST API JiraInboundWebhook + Script Include JiraInboundUtils.",
    "work_notes": "2024-07-16 10:00: Dev - Created Scripted REST API endpoint.",
    "state": "In Progress",
    "assigned_to": "John Doe",
}, ensure_ascii=False)

MARKDOWN_STORY = (
    "# Story: STRY0010099\n\n"
    "## Short Description\nJira webhook inbound integration\n\n"
    "## Description\nImplemented inbound webhook creating Incidents.\n\n"
    "## Work Notes\n2024-07-16 10:00: Dev - Created endpoint.\n\n"
    "## State\nIn Progress"
)

US_PAYLOAD = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<record_update table="sys_script_include">'
    '<sys_script_include action="INSERT_OR_UPDATE">'
    '<name>SnowKbGenerator</name><script><![CDATA[var x = 1;]]></script>'
    '</sys_script_include></record_update>'
    '<record_update table="sys_ui_action">'
    '<sys_ui_action action="INSERT_OR_UPDATE">'
    '<name>GenerateKB</name><script><![CDATA[var y = 2;]]></script>'
    '</sys_ui_action></record_update>'
)

RELATED = "KB0010001 | Jira integration guide\nKB0010002 | Webhook troubleshooting"


# ---------------------------------------------------------------------------
# Darabolás
# ---------------------------------------------------------------------------

class TestSplitStory:
    def test_json_story_split_per_field(self):
        pieces = split_story_into_pieces(JSON_STORY)
        by_id = {p.piece_id: p for p in pieces}
        assert "story:short_description" in by_id
        assert "story:state" in by_id
        assert "story:assigned_to" in by_id
        # FR-004: a főtörzs-mezők story_core, a meta-mezők story_meta
        assert by_id["story:short_description"].source_type == "story_core"
        assert by_id["story:description"].source_type == "story_core"
        assert by_id["story:acceptance_criteria"].source_type == "story_core"
        assert by_id["story:u_technical_specification"].source_type == "story_core"
        assert by_id["story:state"].source_type == "story_meta"
        assert by_id["story:assigned_to"].source_type == "story_meta"
        assert by_id["story:work_notes"].source_type == "story_meta"

    def test_markdown_story_split_per_section(self):
        pieces = split_story_into_pieces(MARKDOWN_STORY)
        by_id = {p.piece_id: p for p in pieces}
        assert by_id["story:short_description"].source_type == "story_core"
        assert by_id["story:description"].source_type == "story_core"
        assert by_id["story:work_notes"].source_type == "story_meta"
        assert by_id["story:state"].source_type == "story_meta"

    def test_story_roundtrip(self):
        """A darabokból újraépített story tartalmazza az összes mezőt."""
        pieces = split_story_into_pieces(JSON_STORY)
        joined = "\n".join(p.text for p in pieces)
        for field in ("short_description", "description", "state", "assigned_to"):
            assert field in joined


class TestSplitUpdateSet:
    def test_records_split(self):
        pieces = split_update_set_into_pieces(US_PAYLOAD)
        assert len(pieces) == 2
        assert all(p.source_type == "update_set_record" for p in pieces)
        names = [p.label for p in pieces]
        assert any("SnowKbGenerator" in n for n in names)
        assert any("GenerateKB" in n for n in names)

    def test_unparseable_is_single_piece(self):
        pieces = split_update_set_into_pieces("<<<not xml at all>>>")
        assert len(pieces) == 1
        assert pieces[0].source_type == "update_set_record"

    def test_empty_payload_no_pieces(self):
        assert split_update_set_into_pieces("") == []
        assert split_update_set_into_pieces("   ") == []


class TestSplitContext:
    def test_combined(self):
        pieces = split_context_into_pieces(
            story_text=JSON_STORY,
            update_set_payloads=US_PAYLOAD,
            related_articles_context=RELATED,
        )
        types = {p.source_type for p in pieces}
        assert types == {"story_core", "story_meta", "update_set_record", "related_article"}
        related = [p for p in pieces if p.source_type == "related_article"]
        assert len(related) == 2


# ---------------------------------------------------------------------------
# Policy: küszöbök, fail-open, FR-004
# ---------------------------------------------------------------------------

class TestClassification:
    def test_obvious_noise_hidden(self, tmp_path):
        s = _settings(tmp_path)
        pieces = [ContextPiece("story:state", "story_meta", "State", "State: Closed")]
        client = FakeScoreClient([_score_response(0.0, 0.99)])  # relevance 0.0
        decisions = classify_pieces(pieces, settings=s, client=client)
        assert decisions[0].verdict == "hide"
        assert decisions[0].relevance == pytest.approx(0.0)
        assert decisions[0].reason == "score"

    def test_supporting_summarized(self, tmp_path):
        s = _settings(tmp_path)
        pieces = [ContextPiece("story:work_notes", "story_meta", "Work Notes", "Dev notes text " * 10)]
        client = FakeScoreClient([_score_response(1.0, 0.99)])  # relevance 0.5
        decisions = classify_pieces(pieces, settings=s, client=client)
        assert decisions[0].verdict == "summarize"

    def test_relevant_shown(self, tmp_path):
        s = _settings(tmp_path)
        pieces = [ContextPiece("update_set:0", "update_set_record", "rec", "script content " * 20)]
        client = FakeScoreClient([_score_response(2.0, 0.99)])  # relevance 1.0
        decisions = classify_pieces(pieces, settings=s, client=client)
        assert decisions[0].verdict == "show"

    def test_low_confidence_shows(self, tmp_path):
        """FR-002: confidence < min_confidence → show (recall-védelem)."""
        s = _settings(tmp_path)
        pieces = [ContextPiece("story:state", "story_meta", "State", "State: Closed")]
        client = FakeScoreClient([_score_response(0.0, 0.50)])  # conf 0.5 < 0.6
        decisions = classify_pieces(pieces, settings=s, client=client)
        assert decisions[0].verdict == "show"
        assert decisions[0].reason == "low-confidence"

    def test_boundary_hide_falls_safer(self, tmp_path):
        """'<' operátor: relevance == hide_below → NEM hide (a biztonságos irányba dől)."""
        s = _settings(tmp_path)
        pieces = [ContextPiece("story:state", "story_meta", "State", "State: Closed")]
        client = FakeScoreClient([_score_response(0.5, 0.99)])  # relevance 0.25 == hide_below
        decisions = classify_pieces(pieces, settings=s, client=client)
        assert decisions[0].verdict == "summarize"  # nem hide

    def test_boundary_summarize_falls_show(self, tmp_path):
        s = _settings(tmp_path)
        pieces = [ContextPiece("story:state", "story_meta", "State", "State: Closed")]
        client = FakeScoreClient([_score_response(1.2, 0.99)])  # relevance 0.6 == summarize_below
        decisions = classify_pieces(pieces, settings=s, client=client)
        assert decisions[0].verdict == "show"  # nem summarize

    def test_sdk_error_fail_open_all_show(self, tmp_path):
        """SC-004 minta: SDK-hiba esetén MINDEN darab show, a feldolgozás nem áll meg."""
        s = _settings(tmp_path)
        pieces = [
            ContextPiece("story:state", "story_meta", "State", "State: Closed"),
            ContextPiece("update_set:0", "update_set_record", "rec", "payload " * 30),
            ContextPiece("story:description", "story_core", "Description", "real content"),
        ]
        client = FakeScoreClient(error=RuntimeError("service down"))
        decisions = classify_pieces(pieces, settings=s, client=client)
        assert all(d.verdict == "show" for d in decisions)
        err = [d for d in decisions if d.source_type != "story_core"]
        assert all(d.reason == "fail-open" for d in err)

    def test_story_core_never_hidden(self, tmp_path):
        """FR-004: a story-főtörzs sosem hide — még 0-s score és teljes
        confidence mellett sem; a hívás el sem indul rá."""
        s = _settings(tmp_path)
        pieces = [
            ContextPiece("story:short_description", "story_core", "Short Description", "x"),
            ContextPiece("story:description", "story_core", "Description", "y"),
            ContextPiece("story:acceptance_criteria", "story_core", "AC", "z"),
            ContextPiece("story:u_technical_specification", "story_core", "TS", "w"),
        ]
        client = FakeScoreClient([_score_response(0.0, 1.0)] * 4)
        decisions = classify_pieces(pieces, settings=s, client=client)
        assert all(d.verdict == "show" for d in decisions)
        assert all(d.reason == "story-core" for d in decisions)
        assert client.calls == []  # a főtörzsre nincs LLM-hívás


class TestStateFix:
    """T012 döntés 2. pont: a `_score_piece` state-ből a story_context kivéve
    (a kalibrációs finding: a story_context FELFÚJTA a Score-t — a zaj 0.86-0.99
    volt vele vs 0.00-0.03 nélküle)."""

    def test_state_excludes_story_core_text(self, tmp_path):
        s = _settings(tmp_path)
        core_text = "THE SECRET CORE BODY 9f8e7d"
        pieces = [
            ContextPiece("story:description", "story_core", "Description", core_text),
            ContextPiece("story:state", "story_meta", "State", "State: Closed"),
        ]
        client = FakeScoreClient([_score_response(0.0, 0.99)])
        classify_pieces(pieces, settings=s, client=client)
        assert len(client.calls) == 1
        state = client.calls[0]["state"]
        assert "story_context" not in state
        assert core_text not in json.dumps(state, ensure_ascii=False)
        assert state["piece_type"] == "story_meta"
        assert "piece" in state


class TestRecording:
    def test_recording_schema(self, tmp_path):
        """FR-003: a JSONL sor a jev-formátum (request_hash, source, model, response)."""
        s = _settings(tmp_path)
        pieces = [ContextPiece("story:state", "story_meta", "State", "State: Closed")]
        client = FakeScoreClient([_score_response(0.0, 0.99)])
        classify_pieces(pieces, settings=s, client=client)
        path = tmp_path / "recording.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        assert len(rows) == 1
        row = rows[0]
        assert set(row) == {"request_hash", "source", "model", "response"}
        assert row["source"] == "recorded"
        assert row["model"] == "jev-1.13.0"
        assert isinstance(row["request_hash"], str) and len(row["request_hash"]) == 64
        answers = row["response"]["answers"]
        assert "relevance" in answers
        assert "score" in answers["relevance"]
        assert "latency_ms" in row["response"]

    def test_recording_deduplicates(self, tmp_path):
        """A már rögzített request hash nem kerül be újra (replay-index minta)."""
        s = _settings(tmp_path)
        pieces = [ContextPiece("story:state", "story_meta", "State", "State: Closed")]
        classify_pieces(pieces, settings=s, client=FakeScoreClient([_score_response(0.0, 0.99)]))
        classify_pieces(pieces, settings=s, client=FakeScoreClient([_score_response(0.0, 0.99)]))
        rows = (tmp_path / "recording.jsonl").read_text().strip().splitlines()
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# apply_decisions / select_context
# ---------------------------------------------------------------------------

class TestApply:
    def test_hidden_piece_removed_shown_kept(self, tmp_path):
        s = _settings(tmp_path)
        pieces = [
            ContextPiece("story:description", "story_core", "Description", "THE BODY"),
            ContextPiece("story:state", "story_meta", "State", "NOISE STATE"),
        ]
        client = FakeScoreClient([_score_response(0.0, 0.99)])
        result = select_context(
            story_text="## Description\nTHE BODY\n\n## State\nNOISE STATE",
            update_set_payloads="",
            related_articles_context="",
            settings=s,
            client=client,
            pieces=pieces,
        )
        assert "THE BODY" in result.story_text
        assert "NOISE STATE" not in result.story_text

    def test_disabled_is_identity(self, tmp_path):
        """FR-006: enabled=False → a kontextus bit-azonosan változatlan."""
        s = _settings(tmp_path, enabled=False)
        result = select_context(
            story_text=MARKDOWN_STORY,
            update_set_payloads=US_PAYLOAD,
            related_articles_context=RELATED,
            settings=s,
            client=FakeScoreClient(error=AssertionError("nem szabad hívni")),
        )
        assert result.story_text == MARKDOWN_STORY
        assert result.update_set_payloads == US_PAYLOAD
        assert result.related_articles_context == RELATED
        assert result.decisions == []

    def test_summarize_endpoint_down_fails_open(self, tmp_path):
        """A summarize a lokális endpointot használja; ha az nem érhető el,
        a darab az EREDETI szöveggel kerül be (fail-open, KD3)."""
        s = _settings(tmp_path)  # 127.0.0.1:9 — elérhetetlen
        pieces = [ContextPiece("story:work_notes", "story_meta", "Work Notes",
                               "LONG NOTES " * 50)]
        client = FakeScoreClient([_score_response(1.0, 0.99)])  # → summarize
        result = select_context(
            story_text="## Work Notes\n" + "LONG NOTES " * 50,
            update_set_payloads="",
            related_articles_context="",
            settings=s,
            client=client,
            pieces=pieces,
        )
        assert result.decisions[0].verdict == "summarize"
        # a summarize hibázott → az eredeti szöveg maradt
        assert "LONG NOTES" in result.story_text
        assert result.decisions[0].summarized is False


# ---------------------------------------------------------------------------
# T006: pipeline-bekötés
# ---------------------------------------------------------------------------

class TestPipelineWiring:
    def _mock_client(self):
        from snow_kb.schemas import StoryData

        class MockSNOW:
            def get_story(self, ident):
                return StoryData(
                    sys_id="abc", number="STRY0010099",
                    short_description="Jira webhook integration",
                    description="Implemented inbound webhook.",
                    acceptance_criteria="Endpoint accepts POST.",
                    u_technical_specification="Scripted REST API.",
                    work_notes="",
                    comments="",
                    state="In Progress",
                    assigned_to="John Doe",
                    assignment_group="Integration Team",
                )

            def get_team_template(self, group):
                return ""

            def get_update_set_changes(self, ident):
                return ("", "")

            def search_kb_articles(self, query, limit=5):
                return []

            def find_existing_kb_article(self, ident):
                return None

            def create_kb_article(self, article, **kwargs):
                self.gate_story_text = kwargs.get("story_text", "")
                return "kb_sys_id"

        return MockSNOW()

    def test_selected_context_to_program_original_to_gate(self, tmp_path):
        """A program a VÁLOGATOTT kontextust kapja; a gate/strip az EREDETIT."""
        from unittest.mock import patch

        from snow_kb.pipeline import generate_kb_article
        from snow_kb.schemas import KBArticle

        s = _settings(tmp_path)
        mock_snow = self._mock_client()

        captured = {}

        class CaptureProgram:
            def __call__(self, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(article=KBArticle(
                    title="Test KB Article",
                    html="<h2>Problem</h2><p>test body</p>",
                    category="c", knowledge_base_id="kb1"))

        # Az összes meta-darab hide (state/assigned_to), a core megmarad.
        score_client = FakeScoreClient([_score_response(0.0, 0.99)] * 20)
        with patch("snow_kb.pipeline.load_settings", return_value=s):
            generate_kb_article(
                "STRY0010099", mock_snow, settings=s,
                program=CaptureProgram(), push=True,
                context_decision_client=score_client,
            )

        # a program a válogatott story-t kapta: az assigned_to meta kiesett
        assert "John Doe" not in captured["story_text"]
        assert "Implemented inbound webhook." in captured["story_text"]
        # a gate az EREDETI story_text-et kapta (014/015 érintetlen)
        assert "John Doe" in mock_snow.gate_story_text

    def test_disabled_leaves_pipeline_unchanged(self, tmp_path):
        """FR-006: enabled=False → a program az eredeti kontextust kapja."""
        from snow_kb.pipeline import generate_kb_article
        from snow_kb.schemas import KBArticle

        s = _settings(tmp_path, enabled=False)
        mock_snow = self._mock_client()
        captured = {}

        class CaptureProgram:
            def __call__(self, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(article=KBArticle(
                    title="Test KB Article",
                    html="<h2>Problem</h2><p>test body</p>",
                    category="c", knowledge_base_id="kb1"))

        generate_kb_article(
            "STRY0010099", mock_snow, settings=s,
            program=CaptureProgram(), push=False,
            context_decision_client=FakeScoreClient(
                error=AssertionError("disabled módban nem szabad hívni")),
        )
        assert "John Doe" in captured["story_text"]
