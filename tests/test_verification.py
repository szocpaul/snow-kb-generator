"""test_verification.py — a verification.py (spec 014) modul tesztjei.

Lefedett területek:
  - T006 (US1): jelölt-kinyerés (011-minta), update-set whitelist, spot-check,
    fail-open, a gold cikkeken 0 false positive (mock checkerrel)
  - T010 (US3): kalibrált réteg — írásvariáns → "létezik (utalás)", ismeretlen →
    "nem létezik", SDK-hiba → fail-open a determinisztikus útra
"""

from __future__ import annotations

import pytest

from snow_kb.verification import (
    SpotChecker,
    extract_component_candidates,
    build_update_set_whitelist,
    verify_component_names,
)


# ---------------------------------------------------------------------------
# Jelölt-kinyerés (011-minta replika)
# ---------------------------------------------------------------------------

class TestExtractCandidates:
    def test_quoted_camelcase_dotted_found(self):
        html = ("<p>A 'JiraInboundUtils' Script Include hívja a JiraIntegrationUtils-t, "
                "és a current.work_notes mezőbe ír.</p>")
        cands = {c.name for c in extract_component_candidates(html)}
        assert "JiraInboundUtils" in cands
        assert "JiraIntegrationUtils" in cands
        assert "current.work_notes" in cands

    def test_generic_whitelist_not_candidate(self):
        """A 011-es általános terminusok NEM jelöltek (spec US1 scenario 4)."""
        html = "<p>Hozz létre egy 'Business Rule'-t az Incident táblára.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "Business Rule" not in cands
        assert "Incident" not in cands

    def test_domain_like_dotted_skipped(self):
        """FQDN-szerű dotted nevek (külső rendszer hostjai) NEM jelöltek —
        a T004 baseline tanulsága (aldi.com false positive)."""
        html = "<p>A sap.aldi.com host felé megy az OData hívás.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "sap.aldi.com" not in cands

    def test_state_terms_not_candidates(self):
        """T005-jóváhagyott szűrés: a workflow-állapotok NEM jelöltek."""
        html = "<p>A Change 'Escalated' állapotba került, majd 'Retry' történt.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "Escalated" not in cands
        assert "Retry" not in cands

    def test_log_message_like_quoted_skipped(self):
        """Naplóüzenet-szerű idézett stringek NEM jelöltek."""
        html = "<p>A 'SnowKbGenerator work_note error' megjelent a logban.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "SnowKbGenerator work_note error" not in cands

    def test_real_br_name_with_spaces_kept(self):
        """A valós, mondatszerű Business Rule-nevek MEGMARADNAK (recall-védelem)."""
        html = "<p>Az 'Abort change of milestone on parent task' Business Rule.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "Abort change of milestone on parent task" in cands

    def test_urls_emails_html_attrs_not_candidates(self):
        html = ('<p><a href="https://aldi.com/x">JiraUtils</a> ír a '
                'admin@aldi.com címre.</p>')
        cands = {c.name for c in extract_component_candidates(html)}
        assert "aldi.com" not in cands
        assert "JiraUtils" in cands


# ---------------------------------------------------------------------------
# Update Set whitelist
# ---------------------------------------------------------------------------

class TestUpdateSetWhitelist:
    def test_names_from_changes_text(self):
        us_text = ("Update Set 'STRY0010001' módosításai:\n"
                   "  - [INSERT_OR_UPDATE] Script Include: JiraInboundUtils\n")
        wl = build_update_set_whitelist(us_text)
        assert "jirainboundutils" in wl

    def test_names_from_payload(self):
        payload = '<?xml version="1.0"?><sys_script_include name="JiraIntegrationUtils"><script>...</script></sys_script_include>'
        wl = build_update_set_whitelist(payload)
        assert "jiraintegrationutils" in wl

    def test_empty_text(self):
        assert build_update_set_whitelist("") == set()


# ---------------------------------------------------------------------------
# SpotChecker (determinisztikus mag)
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, results, status=200):
        self._results = results
        self.status_code = status

    def json(self):
        return {"result": self._results}


class _FakeSession:
    """Mock Table API session: a known_names-ben lévő nevekre ad találatot."""

    def __init__(self, known_names=(), fail=False):
        self.known = {n.casefold() for n in known_names}
        self.fail = fail
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if self.fail:
            raise ConnectionError("mock instance down")
        query = (params or {}).get("sysparm_query", "")
        value = query.split("=", 1)[-1]
        if value.casefold() in self.known:
            return _FakeResponse([{"sys_id": "x"}])
        return _FakeResponse([])


class TestSpotChecker:
    def test_existing_name(self, tmp_path):
        checker = SpotChecker(cache_path=tmp_path / "c.json",
                              session=_FakeSession(known_names=["incident"]),
                              base_url="https://x/api/now/table")
        v = checker.check("incident")
        assert v.status == "exists"

    def test_missing_name(self, tmp_path):
        checker = SpotChecker(cache_path=tmp_path / "c.json",
                              session=_FakeSession(), base_url="https://x")
        v = checker.check("NincsIlyenScript")
        assert v.status == "not_exists"

    def test_error_is_unknown_fail_open(self, tmp_path):
        """FR-002: lekérdezési hiba → unknown (a hívó warninggal kihagyja)."""
        checker = SpotChecker(cache_path=tmp_path / "c.json",
                              session=_FakeSession(fail=True), base_url="https://x")
        v = checker.check("bármi")
        assert v.status == "unknown"

    def test_cache_roundtrip_and_no_session_replay(self, tmp_path):
        """A cache a recording része: második futás session NÉLKÜL is ugyanazt adja (SC-004)."""
        cache = tmp_path / "c.json"
        live = SpotChecker(cache_path=cache, session=_FakeSession(known_names=["incident"]),
                           base_url="https://x")
        assert live.check("incident").status == "exists"
        assert cache.exists()
        replay = SpotChecker(cache_path=cache, session=None)  # cache-only mód
        assert replay.check("incident").status == "exists"
        # cache-miss session nélkül → unknown (fail-open, NEM not_exists)
        assert replay.check("ismeretlen").status == "unknown"


# ---------------------------------------------------------------------------
# verify_component_names — a teljes determinisztikus út
# ---------------------------------------------------------------------------

class TestVerifyComponentNames:
    def test_known_and_unknown_names(self, tmp_path):
        """US1 scenario 1-2: nem-létező név nevesítve; valós nevek érintetlenek."""
        checker = SpotChecker(cache_path=tmp_path / "c.json",
                              session=_FakeSession(known_names=["JiraIntegrationUtils"]),
                              base_url="https://x")
        html = "<p>A 'JiraIntegrationUtils' és a 'FabricatedUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=checker)
        by_name = {v.name: v for v in result.verdicts}
        assert by_name["JiraIntegrationUtils"].status == "exists"
        assert by_name["FabricatedUtils"].status == "not_exists"
        assert not result.skipped

    def test_update_set_whitelist_shortcircuits_spotcheck(self, tmp_path):
        """KD3: ami az update setben van, arra NEM megy spot-check."""
        session = _FakeSession()  # semmit sem ismer
        checker = SpotChecker(cache_path=tmp_path / "c.json", session=session, base_url="https://x")
        html = "<p>A 'JiraInboundUtils' Script Include.</p>"
        us = "Update Set 'S' módosításai:\n  - [INSERT_OR_UPDATE] Script Include: JiraInboundUtils"
        result = verify_component_names(html, us, spot_checker=checker)
        v = result.verdicts[0]
        assert v.status == "exists"
        assert v.layer == "update_set"
        assert session.calls == []

    def test_instance_unreachable_fail_open(self, tmp_path):
        """US1 scenario 3 / FR-002: minden lekérdezés hibázik → skipped + warning."""
        checker = SpotChecker(cache_path=tmp_path / "c.json",
                              session=_FakeSession(fail=True), base_url="https://x")
        html = "<p>A 'ValamiUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=checker)
        assert result.skipped is True
        assert result.warning

    def test_gold_articles_zero_false_positive(self, tmp_path):
        """SC-001 (teszt-szinten, mockkal): a gold cikkek nevei a mock instance-ben
        létezők → 0 'nem létezik' jelölés."""
        from eval.dataset import load_gold_dataset

        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        all_html = [ex.html for ex in trainset + valset]
        # Mock: minden jelölt létezik (a gold nevek valódiak feltételezése — spec Assumptions)
        class _AllKnown:
            def get(self, url, params=None, timeout=None):
                return _FakeResponse([{"sys_id": "x"}])
        checker = SpotChecker(cache_path=tmp_path / "c.json", session=_AllKnown(), base_url="https://x")
        for ex, html in zip(trainset + valset, all_html):
            result = verify_component_names(html, getattr(ex, "update_set_payloads", "") or "",
                                            spot_checker=checker)
            not_found = [v.name for v in result.verdicts if v.status == "not_exists"]
            assert not_found == []


# ---------------------------------------------------------------------------
# T010 (US3): kalibrált réteg a homályos esetekre
# ---------------------------------------------------------------------------

class _FakeJevAnswer:
    def __init__(self, choice, confidence):
        self.choice = choice
        self.confidence = confidence


class _FakeJevResponse:
    def __init__(self, choice, confidence):
        self.answers = {"refers": _FakeJevAnswer(choice, confidence)}


class _FakeJevClient:
    """system_one-kompatibilis mock a kalibrált réteghez."""

    def __init__(self, choice="yes", confidence=0.95, fail=False):
        self.choice = choice
        self.confidence = confidence
        self.fail = fail
        self.calls = []

    def system_one(self, state=None, questions=None, model=None):
        self.calls.append({"state": state, "questions": questions, "model": model})
        if self.fail:
            raise RuntimeError("mock SDK down")
        return _FakeJevResponse(self.choice, self.confidence)


class TestCalibratedLayer:
    def _checker(self, tmp_path):
        return SpotChecker(cache_path=tmp_path / "c.json", session=_FakeSession(),
                           base_url="https://x")

    def test_variant_refers_high_confidence(self, tmp_path):
        """US3 scenario 1: írásvariáns valós komponensre → 'létezik (utalás)'."""
        client = _FakeJevClient(choice="yes", confidence=0.95)
        html = "<p>A 'Jira Integration Utils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=self._checker(tmp_path),
                                        decision_client=client,
                                        decision_model="jev-1.13.0",
                                        confidence_threshold=0.7)
        v = result.verdicts[0]
        assert v.status == "exists"
        assert v.layer == "calibrated"
        assert v.confidence >= 0.7

    def test_unknown_name_low_confidence_flagged(self, tmp_path):
        """US3 scenario 2: ismeretlen név → alacsony confidence → 'nem létezik'."""
        client = _FakeJevClient(choice="no", confidence=0.9)
        html = "<p>A 'FabricatedUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=self._checker(tmp_path),
                                        decision_client=client,
                                        decision_model="jev-1.13.0",
                                        confidence_threshold=0.7)
        v = result.verdicts[0]
        assert v.status == "not_exists"
        assert v.layer == "calibrated"

    def test_threshold_boundary_is_safe_direction(self, tmp_path):
        """A küszöb-operátor '<' (nem '<='): a pontos határérték a biztonságos
        irányba dől — confidence == threshold → NEM utalás → not_exists."""
        client = _FakeJevClient(choice="yes", confidence=0.7)
        html = "<p>A 'KetegoriaUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=self._checker(tmp_path),
                                        decision_client=client,
                                        decision_model="jev-1.13.0",
                                        confidence_threshold=0.7)
        assert result.verdicts[0].status == "not_exists"

    def test_external_system_name_not_flagged(self, tmp_path):
        """Spec Out of Scope: a külső rendszer objektuma NEM kap 'nem létezik'
        jelzést (a kalibrált réteg 'external'-nek ismeri fel)."""
        client = _FakeJevClient(choice="external", confidence=0.95)
        html = "<p>A 'SolMan' rendszer felé megy az adat.</p>"
        result = verify_component_names(html, "", spot_checker=self._checker(tmp_path),
                                        decision_client=client,
                                        decision_model="jev-1.13.0",
                                        confidence_threshold=0.7)
        v = result.verdicts[0]
        assert v.status == "not_applicable"
        assert result.not_existing_names == []

    def test_sdk_failure_fails_open_to_deterministic(self, tmp_path):
        """US3 scenario 3 / FR-002: SDK-hiba → a determinisztikus út eredménye marad."""
        client = _FakeJevClient(fail=True)
        html = "<p>A 'FabricatedUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=self._checker(tmp_path),
                                        decision_client=client,
                                        decision_model="jev-1.13.0",
                                        confidence_threshold=0.7)
        v = result.verdicts[0]
        assert v.status == "not_exists"  # a determinisztikus spot-check eredménye
        assert v.layer == "spotcheck"
