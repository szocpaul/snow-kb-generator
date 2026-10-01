"""test_verification_gate.py — the behaviour tests of the production push gate.

Originally spec 014 (US2, T008); since spec 015 (US3, T010/T011) the gate runs
INSIDE the write path of servicenow_client — these tests keep the
behaviour specification alive on the new architecture (a real
ServiceNowClient + a stubbed HTTP layer; the helpers come from
tests/test_verification_gate_client.py).

The behavior (flag / strip / block) and the fail-open are unchanged (FR-005).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import dspy
import pytest

from snow_kb.errors import VerificationBlocked
from snow_kb.pipeline import generate_kb_article
from snow_kb.schemas import KBArticle

from tests.test_verification_gate_client import (
    _StubChecker,
    _StubJevClient,
    _article,
    _gate_settings,
    _live_client,
)


def _make_program(html: str) -> MagicMock:
    program = MagicMock()
    program.return_value = dspy.Prediction(article=_article(html))
    return program


def _run_pipeline(tmp_path, html, *, behavior="flag", enabled=True, checker=None):
    settings = _gate_settings(tmp_path, enabled=enabled, behavior=behavior)
    client = _live_client(settings)
    result = generate_kb_article(
        "STRY0012345", client, settings,
        program=_make_program(html), push=True,
        spot_checker=checker if checker is not None else _StubChecker(),
        decision_client=_StubJevClient(),
    )
    return result, client


class TestVerificationGate:
    def test_disabled_gate_untouched(self, tmp_path):
        """enabled=False → the gate is inactive, the checker is not even called."""
        checker = _StubChecker()
        html = "<h2>Solution</h2><p>The 'FabricatedUtils' Script Include.</p>"
        result, _ = _run_pipeline(tmp_path, html, enabled=False, checker=checker)
        assert checker.calls == []
        assert getattr(result, "verification_note", "") in ("", None)

    def test_flag_behavior_adds_work_note(self, tmp_path):
        """US2 scenario 1 (the default flag): the non-existent name gets a work_notes signal,
        the article goes through."""
        checker = _StubChecker(known=["RealUtils"])
        html = ("<h2>Solution</h2><p>The 'RealUtils' and the 'FabricatedUtils' "
                "Script Include.</p>")
        result, client = _run_pipeline(tmp_path, html, checker=checker)
        client_note = getattr(result, "verification_note", "")
        assert "FabricatedUtils" in client_note
        assert "RealUtils" not in client_note
        # the html of the article is unchanged (flag does NOT strip)
        assert "FabricatedUtils" in result.html
        # the article was really written (POST kb_knowledge)
        assert any(m == "POST" and u.endswith("/kb_knowledge")
                   for m, u in client._http_calls)

    def test_real_names_pass_unchanged(self, tmp_path):
        """US2 scenario 2: only real names → no signal, the article is unchanged."""
        checker = _StubChecker(known=["RealUtils"])
        html = "<h2>Solution</h2><p>The 'RealUtils' Script Include.</p>"
        result, _ = _run_pipeline(tmp_path, html, checker=checker)
        assert getattr(result, "verification_note", "") in ("", None)

    def test_instance_unreachable_fail_open(self, tmp_path):
        """US2 scenario 3 / FR-005: the instance is unreachable → the article goes out
        with a warning, the push is NOT blocked."""
        checker = _StubChecker(unknown=True)
        html = "<h2>Solution</h2><p>The 'ValamiUtils' Script Include.</p>"
        result, client = _run_pipeline(tmp_path, html, checker=checker)
        assert any(m == "POST" and u.endswith("/kb_knowledge")
                   for m, u in client._http_calls)
        # there is no block and no false "does not exist" signal either
        assert getattr(result, "verification_note", "") in ("", None)

    def test_block_behavior_raises(self, tmp_path):
        """behavior=block (only with the config): the push is blocked, the POST does not run."""
        checker = _StubChecker()  # semmit sem ismer
        html = "<h2>Solution</h2><p>The 'FabricatedUtils' Script Include.</p>"
        with pytest.raises(VerificationBlocked):
            _run_pipeline(tmp_path, html, behavior="block", checker=checker)

    def test_strip_behavior_removes_names(self, tmp_path):
        """behavior=strip (only with the config): the suspicious name is dropped from the html."""
        checker = _StubChecker(known=["RealUtils"])
        html = ("<h2>Solution</h2><p>The 'RealUtils' and the 'FabricatedUtils' "
                "Script Include.</p>")
        result, _ = _run_pipeline(tmp_path, html, behavior="strip", checker=checker)
        assert "FabricatedUtils" not in result.html
        assert "RealUtils" in result.html

    def test_recording_written(self, tmp_path):
        """FR-003: the decision is logged to a replay-compatible JSONL."""
        checker = _StubChecker()
        html = "<h2>Solution</h2><p>The 'FabricatedUtils' Script Include.</p>"
        _run_pipeline(tmp_path, html, checker=checker)
        rec = tmp_path / "verification.jsonl"
        assert rec.exists()
        row = json.loads(rec.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert row["story"] == "STRY0012345"
        assert row["behavior"] == "flag"
        names = {v["name"]: v["status"] for v in row["verdicts"]}
        assert names.get("FabricatedUtils") == "not_exists"
