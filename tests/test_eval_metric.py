"""test_eval_metric.py — a rich_metric (GEPA contract) tesztjei."""

from __future__ import annotations

import dspy
import pytest

from eval.metric import rich_metric


class TestRichMetric:
    """A rich_metric függvény (GEPA contract) tesztjei."""

    def test_returns_prediction_with_score_and_feedback(self):
        """A metric dspy.Prediction(score=float, feedback=str) formátumban tér vissza."""
        gold = dspy.Example(
            story_text="Test story about LDAP fix",
            html="<h2>Problem</h2><p>LDAP auth failed.</p><h2>Solution</h2><ol><li>Retry.</li></ol>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>LDAP auth failed.</p><h2>Solution</h2><ol><li>Retry.</li></ol>"
        )

        result = rich_metric(gold, pred)

        assert isinstance(result, dspy.Prediction)
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0
        assert isinstance(result.feedback, str)
        assert len(result.feedback) > 10

    def test_perfect_match_returns_high_score(self):
        """Ha a generált HTML tökéletesen egyezik, a score magas (0.8+)."""
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>Same problem.</p><h2>Solution</h2><ol><li>Step 1.</li></ol>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Same problem.</p><h2>Solution</h2><ol><li>Step 1.</li></ol>"
        )

        result = rich_metric(gold, pred)

        assert result.score > 0.8, f"Perfect match should score > 0.8, got {result.score}"
        assert "Correct" in result.feedback or "perfect" in result.feedback.lower()

    def test_mismatch_returns_low_score(self):
        """Ha a generált HTML eltér a gold-tól (fejléc és tény is), a score alacsony.

        Megjegyzés (spec 010): a content tengely tény-azonosítókat illeszt (stílus-
        semleges), ezért a példa szándékosan azonosító-dús — a pred-ben ezek hiányoznak.
        """
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>LDAP query timeout in LDAP_Retry_Authenticator on u_user table.</p>"
            "<h2>Solution</h2><ol><li>Step 1.</li></ol>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Different</h2><p>Wrong content entirely.</p>"
        )

        result = rich_metric(gold, pred)

        assert result.score < 0.45, f"Mismatch should score < 0.45, got {result.score}"
        assert "mismatch" in result.feedback.lower() or "wrong" in result.feedback.lower()

    def test_feedback_is_natural_language(self):
        """A feedback természetes nyelvű kritika (nem csak "error")."""
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>LDAP timeout in LDAP_Retry_Authenticator.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Different</h2><p>Wrong content.</p>"
        )

        result = rich_metric(gold, pred)

        # A feedback-nek konkrétumot kell tartalmaznia (miért rossz)
        assert len(result.feedback) > 30, f"Feedback too short: {result.feedback}"
        # A feedback tartalmazza a "mismatch" vagy "wrong" szót, vagy konkrétumot
        assert any(word in result.feedback.lower() for word in ["mismatch", "wrong", "expected", "missing", "incorrect"])

    def test_not_a_dict(self):
        """A metric NEM dict-et ad vissza (GEPA contract)."""
        gold = dspy.Example(story_text="Test", html="<h2>A</h2>").with_inputs("story_text")
        pred = dspy.Prediction(html="<h2>A</h2>")

        result = rich_metric(gold, pred)

        assert not isinstance(result, dict), "Metric must return dspy.Prediction, not dict (GEPA contract)"


class TestHallucinationAxis:
    """US2 (spec 004): a rich_metric bünteti a hallucinált KB hivatkozásokat."""

    def _gold(self):
        return dspy.Example(
            story_text="Story about Jira integration. Related article: KB7654321 was updated.",
            html="<h2>Problem</h2><p>Expected problem.</p>",
        ).with_inputs("story_text")

    def test_fictional_kb_number_is_penalized(self):
        """A story_text-ben NEM szereplő KB szám hallucináció: score csökken + feedback."""
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>See also KB0012345.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert "KB0012345" in result.feedback
        assert "Hallucinated" in result.feedback

    def test_real_kb_number_is_not_penalized(self):
        """A story_text-ben szereplő KB szám (KB7654321) nem számít hallucinációnak."""
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>See also KB7654321.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert "Hallucinated" not in result.feedback

    def test_placeholder_is_not_penalized(self):
        """A KBXXXXXXX placeholder és az N/A nem számít hallucinációnak."""
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>Related: KBXXXXXXX or N/A.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert "Hallucinated" not in result.feedback


class TestHallucinationKnownRefs:
    """US3 (spec 005): a metric a related_articles_context-et is ismeri."""

    def test_related_context_kb_number_is_not_penalized(self):
        gold = dspy.Example(
            story_text="Story about Jira.",
            related_articles_context="KB7654321 | Jira API Authentication Setup",
            html="<h2>Problem</h2><p>Expected problem.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>See KB7654321.</p>"
        )
        result = rich_metric(gold, pred)
        assert "Hallucinated" not in result.feedback


class TestDirectionViolation:
    """US1 (spec 007): irány-érzékeny template_adherence."""

    OUTBOUND_STORY = "Implement Outbound REST API for Jira bug creation. The outbound payload is sent to Jira."
    GOLD_OUTBOUND = "<h2>Overview / Summary</h2><p>Outbound integration.</p>"

    def test_outbound_story_with_filled_inbound_is_penalized(self):
        """Outbound story + kitöltött Inbound szekció → Direction violation feedback."""
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>"
            "<h2>Inbound Technical Implementation</h2><h3>Content</h3>"
            "<ul><li>Script Includes: JiraIntegrationUtils parses and validates the incoming payload data.</li></ul>"
        )
        gold = dspy.Example(story_text=self.OUTBOUND_STORY, html=self.GOLD_OUTBOUND).with_inputs("story_text")
        result = rich_metric(gold, pred)
        assert "Direction violation" in result.feedback
        assert "Inbound Technical Implementation" in result.feedback

    def test_outbound_story_without_inbound_is_ok(self):
        """Outbound story + Inbound szekció hiányzik/N/A → nincs büntetés."""
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        gold = dspy.Example(story_text=self.OUTBOUND_STORY, html=self.GOLD_OUTBOUND).with_inputs("story_text")
        result = rich_metric(gold, pred)
        assert "Direction violation" not in result.feedback

    def test_both_directions_skips_check(self):
        """Ha a story mindkét irányt említi, az irány-ellenőrzés kihagyott."""
        gold = dspy.Example(
            story_text="Bidirectional sync: inbound webhook and outbound REST call.",
            html=self.GOLD_OUTBOUND,
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Sync.</p>"
            "<h2>Inbound Technical Implementation</h2><h3>Content</h3>"
            "<ul><li>The inbound webhook listener receives Jira events and maps fields to incidents.</li></ul>"
        )
        result = rich_metric(gold, pred)
        assert "Direction violation" not in result.feedback

    def test_detect_direction_helper(self):
        from eval.metric import detect_direction
        assert detect_direction("Outbound REST API, outbound payload") == "outbound"
        assert detect_direction("Inbound webhook listener") == "inbound"
        assert detect_direction("inbound and outbound sync") == "both"
        assert detect_direction("REST integration") == "unknown"


class TestUnsupportedSection:
    """US1 (spec 007): a gold szerint támogatatlan szekció büntetve van."""

    def test_section_absent_in_gold_but_filled_in_pred(self):
        gold = dspy.Example(
            story_text="Simple story about config change.",
            html="<h2>Overview / Summary</h2><p>Config updated.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Config updated.</p>"
            "<h2>Testing Guide</h2><h3>Content</h3>"
            "<ul><li>Run the full regression test suite and verify all integration points behave correctly.</li></ul>"
        )
        result = rich_metric(gold, pred)
        assert "Unsupported section" in result.feedback
        assert "Testing Guide" in result.feedback


class TestNAOnlySections:
    """Spec 007 kiegészítés: az N/A-only szekció büntetése, ha a gold kihagyja."""

    def test_na_only_section_penalized_when_gold_omits(self):
        """Pred-ben 'Known Issues / N/A', goldban nincs ilyen szekció → büntetés + feedback."""
        gold = dspy.Example(
            story_text="Outbound REST integration to Jira, outbound payload.",
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>"
            "<h2>Known Issues</h2><h3>Content</h3><ul><li>N/A</li></ul>"
        )
        result = rich_metric(gold, pred)
        assert "N/A-only section" in result.feedback
        assert "Known Issues" in result.feedback

    def test_na_only_section_ok_when_gold_has_it(self):
        """Ha a goldban is megvan a szekció, az N/A-only pred nem büntetett itt."""
        gold = dspy.Example(
            story_text="Simple story.",
            html="<h2>Overview / Summary</h2><p>X.</p><h2>Known Issues</h2><h3>Content</h3><ul><li>Some real issue documented here.</li></ul>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>X.</p><h2>Known Issues</h2><h3>Content</h3><ul><li>N/A</li></ul>"
        )
        result = rich_metric(gold, pred)
        assert "N/A-only section" not in result.feedback

    def test_omitted_section_is_clean(self):
        """A gold szerint kihagyott szekció tényleges kihagyása → semmilyen feedback."""
        gold = dspy.Example(
            story_text="Outbound integration.",
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        result = rich_metric(gold, pred)
        assert "N/A-only section" not in result.feedback
        assert "Unsupported section" not in result.feedback


class TestComponentHallucination:
    """Spec 011 (US1): a rich_metric bünteti a fabrikált komponensneveket."""

    STORY = (
        "Story: outbound Jira integration. Implemented Script Include "
        "'JiraIntegrationUtils' for payload mapping; the endpoint is "
        "https://aldi.atlassian.net/rest/api/2/issue. State 'Escalated' triggers it."
    )

    def _gold(self):
        return dspy.Example(
            story_text=self.STORY,
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>",
        ).with_inputs("story_text")

    def test_fabricated_component_name_is_penalized(self):
        """SC-001: fabrikált komponensnév → hallucination 0 + a feedback nevesíti."""
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>"
            "<p>The 'ALDI: CHG Scheduled' Business Rule triggers the outbound call.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert result.axes["hallucination"] == 0.0
        assert "Hallucinated component name(s)" in result.feedback
        assert "ALDI: CHG Scheduled" in result.feedback

    def test_real_component_names_are_not_penalized(self):
        """A story-ban szereplő nevek (idézett, CamelCase, dotted) nem büntetettek."""
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>"
            "<p>'JiraIntegrationUtils' maps the payload from aldi.atlassian.net "
            "when the state is 'Escalated'.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert result.axes["hallucination"] == 1.0
        assert "Hallucinated" not in result.feedback

    def test_gold_articles_have_no_false_positives(self):
        """SC-002 / FR-001: mind a 8 gold HTML átmegy a komponens-ellenőrzésen."""
        from eval.dataset import load_gold_dataset
        from eval.metric import _find_hallucinated_components

        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        assert len(trainset) + len(valset) == 9
        for ex in trainset + valset:
            # A related_articles_context MELLÉ az update_set_payloads is evidencia
            # (a rich_metric is így hívja — ld. metric.py spec 011 US2 megjegyzés).
            evidence = (getattr(ex, "related_articles_context", "") or "") + "\n" + (
                getattr(ex, "update_set_payloads", "") or ""
            )
            found = _find_hallucinated_components(ex.html, ex.story_text, evidence)
            assert not found, f"False positive a gold cikkben: {found}"

    def test_whitelist_terms_are_not_flagged(self):
        """FR-003: általános terminusok (Business Rule, Script Include, Incident,
        ServiceNow) nem számítanak komponensnévnek."""
        from eval.metric import _find_hallucinated_components

        html = (
            "<p>The 'Business Rule' and the 'Script Include' handle the Incident "
            "in ServiceNow. A 'Change Request' is created.</p>"
        )
        found = _find_hallucinated_components(html, "Unrelated story text.", "")
        assert found == [], f"Whitelist-elemek jelölve: {found}"

    def test_axes_still_contain_hallucination(self):
        """Az axes-ben a hallucination tengely továbbra is szerepel (FR-004)."""
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        result = rich_metric(self._gold(), pred)
        assert "hallucination" in result.axes
        assert result.axes["hallucination"] == 1.0

    def test_detector_is_fault_tolerant(self, monkeypatch):
        """FR-002: belső hiba esetén a metric nem áll meg, a tengely semleges."""
        import eval.metric as metric_mod

        def _boom(*args, **kwargs):
            raise RuntimeError("beltörés")

        monkeypatch.setattr(metric_mod, "_find_hallucinated_components", _boom)
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        result = rich_metric(self._gold(), pred)
        assert result.axes["hallucination"] == 1.0  # semleges: nem büntet vaktában



# ---------------------------------------------------------------------------
# Spec 014 (US1, T006): instance-tengely — ÚJ tengely a meglévők MELLÉ (FR-006)
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, results):
        self.status_code = 200
        self._results = results

    def json(self):
        return {"result": self._results}


class _AllKnownSession:
    """Minden név létezik (a gold nevek valódiak — spec Assumptions)."""

    def get(self, url, params=None, timeout=None):
        return _FakeResponse([{"sys_id": "x"}])


class _EmptySession:
    """Semmi sem létezik az instance-ben."""

    def get(self, url, params=None, timeout=None):
        return _FakeResponse([])


class _DownSession:
    def get(self, url, params=None, timeout=None):
        raise ConnectionError("mock instance down")


@pytest.fixture
def instance_axis(tmp_path):
    """Instance-tengely be/ki kapcsolása tesztenként (modul-szintű állapot)."""
    from eval import metric as metric_mod
    from snow_kb.verification import SpotChecker

    def _configure(session):
        metric_mod.configure_instance_axis(
            SpotChecker(cache_path=tmp_path / "spotcheck.json", session=session,
                        base_url="https://mock/api/now/table")
            if session is not None else None
        )

    yield _configure
    metric_mod.configure_instance_axis(None)  # takarítás — a többi teszt semlegessége


class TestInstanceAxis:
    """A metrika instance-tengelye (spec 014, FR-006: a story-alapú tengely érintetlen)."""

    def _gold_pred(self):
        html = ("<h2>Problem</h2><p>A JiraInboundUtils Script Include hibázik.</p>"
                "<h2>Solution</h2><ol><li>Javítás.</li></ol>")
        gold = dspy.Example(
            story_text="A story a JiraInboundUtils Script Include javításáról szól.",
            html=html,
        ).with_inputs("story_text")
        pred = dspy.Prediction(html=html)
        return gold, pred

    def test_axis_inactive_by_default(self):
        """Alapállapotban (checker nélkül) nincs instance-tengely — a régi
        viselkedés bit-azonos (FR-006)."""
        gold, pred = self._gold_pred()
        result = rich_metric(gold, pred)
        axes = result.get("axes") or {}
        assert "instance" not in axes

    def test_all_names_exist_axis_1(self, instance_axis):
        """US1 scenario 2: csak valós nevek → tengely 1.0."""
        instance_axis(_AllKnownSession())
        gold, pred = self._gold_pred()
        result = rich_metric(gold, pred)
        assert result.axes["instance"] == 1.0

    def test_missing_name_axis_0_and_named(self, instance_axis):
        """US1 scenario 1: nem-létező név → tengely 0 ÉS nevesítés a feedbackben."""
        instance_axis(_EmptySession())
        gold, pred = self._gold_pred()
        result = rich_metric(gold, pred)
        assert result.axes["instance"] == 0.0
        assert "JiraInboundUtils" in result.feedback
        # a büntetés a score-ban is megjelenik (nevesítve bünteti — US1)
        from eval import metric as metric_mod
        metric_mod.configure_instance_axis(None)
        clean = rich_metric(gold, pred)
        assert result.score < clean.score

    def test_lookup_failure_fail_open(self, instance_axis):
        """US1 scenario 3 / FR-002: lekérdezési hiba → a tengely kihagyódik
        (semleges), a többi tengely és a score változatlan."""
        instance_axis(_DownSession())
        gold, pred = self._gold_pred()
        result = rich_metric(gold, pred)
        axes = result.axes
        assert axes.get("instance", 1.0) == 1.0  # semleges
        from eval import metric as metric_mod
        metric_mod.configure_instance_axis(None)
        clean = rich_metric(gold, pred)
        assert result.score == clean.score

    def test_gold_articles_zero_false_positive(self, instance_axis, tmp_path):
        """SC-001 (mockkal): a gold cikkeken 0 'nem létezik' jelölés, ha az
        instance-metaadat szerint a nevek léteznek."""
        from eval.dataset import load_gold_dataset

        instance_axis(_AllKnownSession())
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            gold = dspy.Example(story_text=ex.story_text, html=ex.html,
                                update_set_payloads=getattr(ex, "update_set_payloads", "") or ""
                                ).with_inputs("story_text")
            pred = dspy.Prediction(html=ex.html)
            result = rich_metric(gold, pred)
            assert result.axes.get("instance", 1.0) == 1.0, (
                f"false 'nem létezik' jelölés a goldon: {result.feedback[:300]}")
