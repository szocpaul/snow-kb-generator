"""test_verification.py — the tests of the verification.py (spec 014) module.

The covered areas:
  - T006 (US1): the candidate extraction (011 pattern), the update-set whitelist, the spot-check,
    fail-open, a gold cikkeken 0 false positive (mock checkerrel)
  - T010 (US3): the calibrated layer — a spelling variant → "exists (a reference)", an unknown →
    "does not exist", an SDK error → fail-open to the deterministic path
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
# The candidate extraction (an 011 pattern replica)
# ---------------------------------------------------------------------------

class TestExtractCandidates:
    def test_quoted_camelcase_dotted_found(self):
        html = ("<p>The 'JiraInboundUtils' Script Include calls the JiraIntegrationUtils, "
                "and writes it into the current.work_notes field.</p>")
        cands = {c.name for c in extract_component_candidates(html)}
        assert "JiraInboundUtils" in cands
        assert "JiraIntegrationUtils" in cands
        assert "current.work_notes" in cands

    def test_generic_whitelist_not_candidate(self):
        """The general terms of 011 are NOT candidates (spec US1 scenario 4)."""
        html = "<p>Create a 'Business Rule' on the Incident table.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "Business Rule" not in cands
        assert "Incident" not in cands

    def test_domain_like_dotted_skipped(self):
        """The FQDN-like dotted names (the hosts of external systems) are NOT candidates —
        the lesson of the T004 baseline (the example-service.com false positive)."""
        html = "<p>The OData call goes towards the sap.example-service.com host.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "sap.example-service.com" not in cands

    def test_state_terms_not_candidates(self):
        """The filtering approved by T005: the workflow states are NOT candidates."""
        html = "<p>The Change went into the 'Escalated' state, then a 'Retry' happened.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "Escalated" not in cands
        assert "Retry" not in cands

    def test_log_message_like_quoted_skipped(self):
        """The log-message-like quoted strings are NOT candidates."""
        html = "<p>A 'SnowKbGenerator work_note error' megjelent a logban.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "SnowKbGenerator work_note error" not in cands

    def test_real_br_name_with_spaces_kept(self):
        """The real, sentence-like Business Rule names REMAIN (recall protection)."""
        html = "<p>Az 'Abort change of milestone on parent task' Business Rule.</p>"
        cands = {c.name for c in extract_component_candidates(html)}
        assert "Abort change of milestone on parent task" in cands

    def test_urls_emails_html_attrs_not_candidates(self):
        html = ('<p><a href="https://example-service.com/x">JiraUtils</a> writes to the '
                'admin@example-service.com address.</p>')
        cands = {c.name for c in extract_component_candidates(html)}
        assert "example-service.com" not in cands
        assert "JiraUtils" in cands


# ---------------------------------------------------------------------------
# Update Set whitelist
# ---------------------------------------------------------------------------

class TestUpdateSetWhitelist:
    def test_names_from_changes_text(self):
        us_text = ("Update Set 'STRY0010001' modifications:\n"
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
    """A mock Table API session: it returns a hit for the names in known_names."""

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
        """FR-002: a query error → unknown (the caller skips it with a warning)."""
        checker = SpotChecker(cache_path=tmp_path / "c.json",
                              session=_FakeSession(fail=True), base_url="https://x")
        v = checker.check("anything")
        assert v.status == "unknown"

    def test_cache_roundtrip_and_no_session_replay(self, tmp_path):
        """The cache is part of the recording: the second run gives the same result even without a session (SC-004)."""
        cache = tmp_path / "c.json"
        live = SpotChecker(cache_path=cache, session=_FakeSession(known_names=["incident"]),
                           base_url="https://x")
        assert live.check("incident").status == "exists"
        assert cache.exists()
        replay = SpotChecker(cache_path=cache, session=None)  # cache-only mode
        assert replay.check("incident").status == "exists"
        # a cache miss without a session → unknown (fail-open, NOT not_exists)
        assert replay.check("unknown").status == "unknown"


# ---------------------------------------------------------------------------
# verify_component_names — the complete deterministic path
# ---------------------------------------------------------------------------

class TestVerifyComponentNames:
    def test_known_and_unknown_names(self, tmp_path):
        """US1 scenario 1-2: a non-existent name is named; the real names are untouched."""
        checker = SpotChecker(cache_path=tmp_path / "c.json",
                              session=_FakeSession(known_names=["JiraIntegrationUtils"]),
                              base_url="https://x")
        html = "<p>The 'JiraIntegrationUtils' and the 'FabricatedUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=checker)
        by_name = {v.name: v for v in result.verdicts}
        assert by_name["JiraIntegrationUtils"].status == "exists"
        assert by_name["FabricatedUtils"].status == "not_exists"
        assert not result.skipped

    def test_update_set_whitelist_shortcircuits_spotcheck(self, tmp_path):
        """KD3: what is in the update set does NOT get a spot-check."""
        session = _FakeSession()  # semmit sem ismer
        checker = SpotChecker(cache_path=tmp_path / "c.json", session=session, base_url="https://x")
        html = "<p>A 'JiraInboundUtils' Script Include.</p>"
        us = "Update Set 'S' modifications:\n  - [INSERT_OR_UPDATE] Script Include: JiraInboundUtils"
        result = verify_component_names(html, us, spot_checker=checker)
        v = result.verdicts[0]
        assert v.status == "exists"
        assert v.layer == "update_set"
        assert session.calls == []

    def test_instance_unreachable_fail_open(self, tmp_path):
        """US1 scenario 3 / FR-002: every query fails → skipped + a warning."""
        checker = SpotChecker(cache_path=tmp_path / "c.json",
                              session=_FakeSession(fail=True), base_url="https://x")
        html = "<p>A 'ValamiUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=checker)
        assert result.skipped is True
        assert result.warning

    def test_gold_articles_zero_false_positive(self, tmp_path):
        """SC-001 (at the test level, with mocks): the names of the gold articles in the mock instance
        the existing ones → 0 'does not exist' labels."""
        from eval.dataset import load_gold_dataset

        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        all_html = [ex.html for ex in trainset + valset]
        # Mock: every candidate exists (the assumption that the gold names are real — spec Assumptions)
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
# T010 (US3): the calibrated layer for the ambiguous cases
# ---------------------------------------------------------------------------

class _FakeJevAnswer:
    def __init__(self, choice, confidence):
        self.choice = choice
        self.confidence = confidence


class _FakeJevResponse:
    def __init__(self, choice, confidence):
        self.answers = {"refers": _FakeJevAnswer(choice, confidence)}


class _FakeJevClient:
    """A system_one-compatible mock for the calibrated layer."""

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
        """US3 scenario 1: a spelling variant of a real component → 'exists (a reference)'."""
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
        """US3 scenario 2: an unknown name → low confidence → 'does not exist'."""
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
        """The threshold operator is '<' (not '<='): exactly the boundary value leans to the safe
        direction — confidence == threshold → NOT a reference → not_exists."""
        client = _FakeJevClient(choice="yes", confidence=0.7)
        html = "<p>A 'KetegoriaUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=self._checker(tmp_path),
                                        decision_client=client,
                                        decision_model="jev-1.13.0",
                                        confidence_threshold=0.7)
        assert result.verdicts[0].status == "not_exists"

    def test_external_system_name_not_flagged(self, tmp_path):
        """Spec Out of Scope: the object of an external system does NOT get a 'does not exist'
        signal (the calibrated layer recognizes it as 'external')."""
        client = _FakeJevClient(choice="external", confidence=0.95)
        html = "<p>The data goes towards the 'SolMan' system.</p>"
        result = verify_component_names(html, "", spot_checker=self._checker(tmp_path),
                                        decision_client=client,
                                        decision_model="jev-1.13.0",
                                        confidence_threshold=0.7)
        v = result.verdicts[0]
        assert v.status == "not_applicable"
        assert result.not_existing_names == []

    def test_sdk_failure_fails_open_to_deterministic(self, tmp_path):
        """US3 scenario 3 / FR-002: an SDK error → the result of the deterministic path stays."""
        client = _FakeJevClient(fail=True)
        html = "<p>A 'FabricatedUtils' Script Include.</p>"
        result = verify_component_names(html, "", spot_checker=self._checker(tmp_path),
                                        decision_client=client,
                                        decision_model="jev-1.13.0",
                                        confidence_threshold=0.7)
        v = result.verdicts[0]
        assert v.status == "not_exists"  # the result of the deterministic spot-check
        assert v.layer == "spotcheck"
