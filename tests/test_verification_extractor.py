"""test_verification_extractor.py — kinyerő-finomítás tesztek (Agent.md §46, fix/extractor-refinement).

A §46-os hibaosztály: a kinyerő nem-komponensekből csinál jelöltet
(SnowKbGenerator projektnév, ChTask/FrameWork CamelCase-fragmentumok).
A javítás: brand/projekt-blacklist + fragment-kontextus-szabály (011-minta)
+ naplóüzenet-szuffix bővítés. RECALL-VÉDELEM: a valódi nevek megmaradnak.
"""

from __future__ import annotations

import pytest

from eval.dataset import load_gold_dataset
from snow_kb.verification import extract_component_candidates


def _names(html: str) -> set[str]:
    return {c.name for c in extract_component_candidates(html)}


# ---------------------------------------------------------------------------
# Brand/projekt-blacklist (§46: SnowKbGenerator false candidate)
# ---------------------------------------------------------------------------

class TestBrandBlacklist:
    @pytest.mark.parametrize("bad", [
        "SnowKbGenerator",       # projektnév (§46 éles FP)
        "snow_kb",               # projektnév snake_case
        "snow-kb-generator",     # projektnév kötőjeles
        "ALDI",                  # cégnév
    ])
    def test_brand_not_candidate(self, bad: str):
        html = f"<p>A {bad} felé irányuló hívás készült el.</p>"
        assert bad not in _names(html)

    def test_quoted_brand_not_candidate(self):
        assert "ALDI" not in _names("<p>Az 'ALDI' rendszer felé megy az OData hívás.</p>")

    def test_spaced_project_name_not_candidate(self):
        assert "Snow Kb Generator" not in _names("<p>A 'Snow Kb Generator' projekt.</p>")

    def test_external_system_name_stays_candidate(self):
        """A 014-es Out-of-Scope design: a külső rendszer neve (SolMan) jelölt MARAD —
        a kalibrált réteg 'external'-nek ismeri fel (not_applicable, nem flag)."""
        html = "<p>A 'SolMan' rendszer felé megy az adat.</p>"
        assert "SolMan" in _names(html)

    def test_brand_prefixed_real_name_stays(self):
        """RECALL: a brandet TARTALMAZÓ valódi név NEM esik ki (exact-match blacklist)."""
        html = "<p>A Script Include 'ALDIS4ProjectInterface' építi a payloadot.</p>"
        assert "ALDIS4ProjectInterface" in _names(html)


# ---------------------------------------------------------------------------
# CamelCase-fragmentumok (§46 / 014 gold-7: ChTask, FrameWork)
# ---------------------------------------------------------------------------

class TestCamelCaseFragments:
    def test_chtask_fragment_not_candidate(self):
        html = "<p>ALDI SolMan async CD or ChTask State upd: Updates the parent request.</p>"
        assert "ChTask" not in _names(html)

    def test_framework_fragment_not_candidate(self):
        html = "<p>REST Message: ALDI SolMan Interface FrameWork, using the function.</p>"
        assert "FrameWork" not in _names(html)


# ---------------------------------------------------------------------------
# Naplóüzenet-szuffix bővítés (meglévő szabály folytatása)
# ---------------------------------------------------------------------------

class TestLogMessageSuffix:
    def test_does_not_exist_message_not_candidate(self):
        html = "<p>Hiba: 'Tax code I2 does not exist' jelent meg a válaszban.</p>"
        assert "Tax code I2 does not exist" not in _names(html)


# ---------------------------------------------------------------------------
# RECALL-VÉDELEM — ezeknek MOST ÉS UTÁNA is zöldnek kell lenniük
# ---------------------------------------------------------------------------

class TestRecall:
    @pytest.mark.parametrize("html,expected", [
        # komponens-típus szó melletti CamelCase (a kontextus-szabály NEM szűrheti ki)
        ("<p>A JiraIntegrationUtils Script Include hívja a JiraIntegrationUtils-t.</p>", "JiraIntegrationUtils"),
        ("<p>Script Include JiraInboundUtils parses the payload.</p>", "JiraInboundUtils"),
        # HTML-entitás-idézőjel közötti SOAP-operációk
        ("<p>SOAP operations &#34; GetReturns&#34; and &#34; ConfirmReturns&#34;.</p>", "GetReturns"),
        ("<p>SOAP operations &#34; GetReturns&#34; and &#34; ConfirmReturns&#34;.</p>", "ConfirmReturns"),
        # idézett REST-függvény és URL-végi OData-entitás
        ("<p>function 'UpdateProjectDates'. Authentication: OAuth 2.0.</p>", "UpdateProjectDates"),
        ("<p>ProjectMilestone endpoint. Retry logic: 3 attempts.</p>", "ProjectMilestone"),
        # branddel kezdődő dotted azonosítók (a blacklist exact-match!)
        ("<p>Az aldi.integration.almex.config property beállítása.</p>", "aldi.integration.almex.config"),
        ("<p>Az aldi.solman és interface.solman property-k.</p>", "aldi.solman"),
        ("<p>Az aldi.solman és interface.solman property-k.</p>", "interface.solman"),
        # idézett, brandet tartalmazó hosszú nevek
        ("<p>REST Message 'ALDI S4 OData Outbound' hívása.</p>", "ALDI S4 OData Outbound"),
        # valós BR-név szóközökkel
        ("<p>Az 'Abort change of milestone on parent task' Business Rule.</p>", "Abort change of milestone on parent task"),
    ])
    def test_real_name_stays(self, html: str, expected: str):
        assert expected in _names(html)

    # A 9 gold cikk valódi jelöltjei (extractor_baseline.json keep-lista, 21 név)
    GOLD_KEEP = {
        "JiraInboundUtils", "JiraIntegrationUtils",
        "Create KB Article", "current.work_notes", "current.number",
        "SolMan: Sync CD State to CTASK Closure Readiness",
        "SolMan: Fix CD State Inconsistencies",
        "interface.solman", "aldi.solman", "SolMan",
        "aldi.integration.almex.config", "aldi.almex.config.list",
        "aldi.integration.almex.config.matrix", "interface.almex.user",
        "GetReturns", "ConfirmReturns",
        "ALDI S4 OData Outbound", "ALDI: CHG Scheduled - Push Dates to S4",
        "ALDIS4ProjectInterface", "UpdateProjectDates", "ProjectMilestone",
    }

    def test_gold_articles_recall_no_loss(self):
        """A 9 gold cikk valódi jelöltjei a javítás után is MIND kinyerődnek."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        found: set[str] = set()
        for ex in trainset + valset:
            found |= _names(ex.html)
        missing = self.GOLD_KEEP - found
        assert not missing, f"recall-veszteség a gold cikkeken: {sorted(missing)}"

    def test_gold_articles_false_candidates_gone(self):
        """A baseline 6 false candidate-e a javítás után EGYIK SEM jelölt."""
        false_names = {
            "SnowKbGenerator", "ChTask", "FrameWork",
            "Tax code I2 does not exist",
        }
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        found: set[str] = set()
        for ex in trainset + valset:
            found |= _names(ex.html)
        leaked = false_names & found
        assert not leaked, f"a false candidate-ek még mindig jelöltek: {sorted(leaked)}"
