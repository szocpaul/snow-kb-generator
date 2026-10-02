"""test_verification_extractor.py — the extractor refinement tests (Agent.md §46, fix/extractor-refinement).

The error class of §46: the extractor makes a candidate out of non-components
(the SnowKbGenerator project name, the ChTask/FrameWork CamelCase fragments).
The fix: the brand/project blacklist + the fragment context rule (011 pattern)
+ the log message suffix extension. RECALL PROTECTION: the real names remain.
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
        "SnowKbGenerator",       # the project name (§46 production FP)
        "snow_kb",               # the project name in snake_case
        "snow-kb-generator",     # the project name with hyphens
        "ALDI",                  # the company name
    ])
    def test_brand_not_candidate(self, bad: str):
        html = f"<p>A call towards {bad} was made.</p>"
        assert bad not in _names(html)

    def test_quoted_brand_not_candidate(self):
        assert "ALDI" not in _names("<p>The OData call goes towards the 'ALDI' system.</p>")

    def test_spaced_project_name_not_candidate(self):
        assert "Snow Kb Generator" not in _names("<p>A 'Snow Kb Generator' projekt.</p>")

    def test_external_system_name_stays_candidate(self):
        """The 014 Out-of-Scope design: the name of the external system (SolMan) REMAINS a candidate —
        the calibrated layer recognizes it as 'external' (not_applicable, not flagged)."""
        html = "<p>The data goes towards the 'SolMan' system.</p>"
        assert "SolMan" in _names(html)

    def test_brand_prefixed_real_name_stays(self):
        """RECALL: a real name CONTAINING the brand does not drop out (the exact-match blacklist)."""
        html = "<p>The Script Include 'S4ProjectInterface' builds the payload.</p>"
        assert "S4ProjectInterface" in _names(html)


# ---------------------------------------------------------------------------
# CamelCase-fragmentumok (§46 / 014 gold-7: ChTask, FrameWork)
# ---------------------------------------------------------------------------

class TestCamelCaseFragments:
    def test_chtask_fragment_not_candidate(self):
        html = "<p>SolMan async CD or ChTask State upd: Updates the parent request.</p>"
        assert "ChTask" not in _names(html)

    def test_framework_fragment_not_candidate(self):
        html = "<p>REST Message: SolMan Interface FrameWork, using the function.</p>"
        assert "FrameWork" not in _names(html)


# ---------------------------------------------------------------------------
# The log message suffix extension (the continuation of the existing rule)
# ---------------------------------------------------------------------------

class TestLogMessageSuffix:
    def test_does_not_exist_message_not_candidate(self):
        html = "<p>Error: 'Tax code I2 does not exist' appeared in the response.</p>"
        assert "Tax code I2 does not exist" not in _names(html)


# ---------------------------------------------------------------------------
# RECALL PROTECTION — these have to be green NOW and AFTER as well
# ---------------------------------------------------------------------------

class TestRecall:
    @pytest.mark.parametrize("html,expected", [
        # the CamelCase next to a component type word (the context rule must not filter it out)
        ("<p>The JiraIntegrationUtils Script Include calls the JiraIntegrationUtils.</p>", "JiraIntegrationUtils"),
        ("<p>Script Include JiraInboundUtils parses the payload.</p>", "JiraInboundUtils"),
        # the SOAP operations between the HTML entity quotes
        ("<p>SOAP operations &#34; GetReturns&#34; and &#34; ConfirmReturns&#34;.</p>", "GetReturns"),
        ("<p>SOAP operations &#34; GetReturns&#34; and &#34; ConfirmReturns&#34;.</p>", "ConfirmReturns"),
        # the quoted REST function and the OData entity at the end of a URL
        ("<p>function 'UpdateProjectDates'. Authentication: OAuth 2.0.</p>", "UpdateProjectDates"),
        ("<p>ProjectMilestone endpoint. Retry logic: 3 attempts.</p>", "ProjectMilestone"),
        # the dotted identifiers starting with a brand (the blacklist is exact-match!)
        ("<p>The setting of the integration.vendor.config property.</p>", "integration.vendor.config"),
        ("<p>The integration.solman and interface.solman properties.</p>", "integration.solman"),
        ("<p>The integration.solman and interface.solman properties.</p>", "interface.solman"),
        # the quoted long names containing a brand
        ("<p>The call of the REST Message 'ERP OData Outbound'.</p>", "ERP OData Outbound"),
        # a real BR name with spaces
        ("<p>Az 'Abort change of milestone on parent task' Business Rule.</p>", "Abort change of milestone on parent task"),
    ])
    def test_real_name_stays(self, html: str, expected: str):
        assert expected in _names(html)

    # The real candidates of the 9 gold articles (the keep list of extractor_baseline.json, 21 names)
    GOLD_KEEP = {
        "JiraInboundUtils", "JiraIntegrationUtils",
        "Create KB Article", "current.work_notes", "current.number",
        "SolMan: Sync CD State to CTASK Closure Readiness",
        "SolMan: Fix CD State Inconsistencies",
        "interface.solman", "integration.solman", "SolMan",
        "integration.vendor.config", "vendor.config.list",
        "integration.vendor.config.matrix", "interface.vendor.service",
        "GetReturns", "ConfirmReturns",
        "ERP OData Outbound", "Milestone Dates Push to ERP",
        "S4ProjectInterface", "UpdateProjectDates", "ProjectMilestone",
    }

    def test_gold_articles_recall_no_loss(self):
        """The real candidates of the 9 gold articles are ALL extracted even after the fix."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        found: set[str] = set()
        for ex in trainset + valset:
            found |= _names(ex.html)
        missing = self.GOLD_KEEP - found
        assert not missing, f"recall loss on the gold articles: {sorted(missing)}"

    def test_gold_articles_false_candidates_gone(self):
        """None of the 6 false candidates of the baseline is a candidate after the fix."""
        false_names = {
            "SnowKbGenerator", "ChTask", "FrameWork",
            "Tax code I2 does not exist",
        }
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        found: set[str] = set()
        for ex in trainset + valset:
            found |= _names(ex.html)
        leaked = false_names & found
        assert not leaked, f"the false candidates are still candidates: {sorted(leaked)}"
