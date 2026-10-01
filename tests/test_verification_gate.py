"""test_verification_gate.py — a production push-gate viselkedési tesztjei.

Spec 014 (US2, T008) eredetileg; spec 015 (US3, T010/T011) óta a gate a
servicenow_client írási útjának BELSÉJÉBEN fut — ezek a tesztek a
viselkedés-specifikációt tartják életben az új architektúrán (valódi
ServiceNowClient + stubolt HTTP réteg; a segédek a
tests/test_verification_gate_client.py-ból).

A behavior (flag / strip / block) és a fail-open változatlan (FR-005).
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
        """enabled=False → a gate inaktív, a checker meg sem hívódik."""
        checker = _StubChecker()
        html = "<h2>Megoldás</h2><p>A 'FabricatedUtils' Script Include.</p>"
        result, _ = _run_pipeline(tmp_path, html, enabled=False, checker=checker)
        assert checker.calls == []
        assert getattr(result, "verification_note", "") in ("", None)

    def test_flag_behavior_adds_work_note(self, tmp_path):
        """US2 scenario 1 (default flag): a nem-létező név work_notes-jelzést kap,
        a cikk kimegy."""
        checker = _StubChecker(known=["RealUtils"])
        html = ("<h2>Megoldás</h2><p>A 'RealUtils' és a 'FabricatedUtils' "
                "Script Include.</p>")
        result, client = _run_pipeline(tmp_path, html, checker=checker)
        client_note = getattr(result, "verification_note", "")
        assert "FabricatedUtils" in client_note
        assert "RealUtils" not in client_note
        # a cikk html-je változatlan (flag NEM strip)
        assert "FabricatedUtils" in result.html
        # a cikk ténylegesen kiíródott (POST kb_knowledge)
        assert any(m == "POST" and u.endswith("/kb_knowledge")
                   for m, u in client._http_calls)

    def test_real_names_pass_unchanged(self, tmp_path):
        """US2 scenario 2: csak valós nevek → nincs jelzés, cikk változatlan."""
        checker = _StubChecker(known=["RealUtils"])
        html = "<h2>Megoldás</h2><p>A 'RealUtils' Script Include.</p>"
        result, _ = _run_pipeline(tmp_path, html, checker=checker)
        assert getattr(result, "verification_note", "") in ("", None)

    def test_instance_unreachable_fail_open(self, tmp_path):
        """US2 scenario 3 / FR-005: az instance elérhetetlen → a cikk kimegy
        warninggal, a push NEM akad el."""
        checker = _StubChecker(unknown=True)
        html = "<h2>Megoldás</h2><p>A 'ValamiUtils' Script Include.</p>"
        result, client = _run_pipeline(tmp_path, html, checker=checker)
        assert any(m == "POST" and u.endswith("/kb_knowledge")
                   for m, u in client._http_calls)
        # nincs blokk és nincs téves "nem létezik" jelzés sem
        assert getattr(result, "verification_note", "") in ("", None)

    def test_block_behavior_raises(self, tmp_path):
        """behavior=block (csak konfiggal): a push blokkolódik, POST NEM fut."""
        checker = _StubChecker()  # semmit sem ismer
        html = "<h2>Megoldás</h2><p>A 'FabricatedUtils' Script Include.</p>"
        with pytest.raises(VerificationBlocked):
            _run_pipeline(tmp_path, html, behavior="block", checker=checker)

    def test_strip_behavior_removes_names(self, tmp_path):
        """behavior=strip (csak konfiggal): a gyanús név kikerül a html-ből."""
        checker = _StubChecker(known=["RealUtils"])
        html = ("<h2>Megoldás</h2><p>A 'RealUtils' és a 'FabricatedUtils' "
                "Script Include.</p>")
        result, _ = _run_pipeline(tmp_path, html, behavior="strip", checker=checker)
        assert "FabricatedUtils" not in result.html
        assert "RealUtils" in result.html

    def test_recording_written(self, tmp_path):
        """FR-003: a döntés replay-kompatibilis JSONL-be naplózódik."""
        checker = _StubChecker()
        html = "<h2>Megoldás</h2><p>A 'FabricatedUtils' Script Include.</p>"
        _run_pipeline(tmp_path, html, checker=checker)
        rec = tmp_path / "verification.jsonl"
        assert rec.exists()
        row = json.loads(rec.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert row["story"] == "STRY0012345"
        assert row["behavior"] == "flag"
        names = {v["name"]: v["status"] for v in row["verdicts"]}
        assert names.get("FabricatedUtils") == "not_exists"
