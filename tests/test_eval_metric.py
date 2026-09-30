"""test_eval_metric.py — a rich_metric (GEPA contract) tesztjei."""

from __future__ import annotations

import dspy
import pytest

from eval.metric import rich_metric


class TestRichMetric:
    """The tests of the rich_metric function (the GEPA contract)."""

    def test_returns_prediction_with_score_and_feedback(self):
        """The metric returns in the dspy.Prediction(score=float, feedback=str) format."""
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
        """If the generated HTML matches perfectly, the score is high (0.8+)."""
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
        """If the generated HTML differs from the gold (both the heading and a fact), the score is low.

        Note (spec 010): the content axis matches the fact identifiers (it is style-
        agnostic), therefore the example is intentionally identifier-rich — they are missing in the pred.
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
        """The feedback is a critique in natural language (not just "error")."""
        gold = dspy.Example(
            story_text="Test story",
            html="<h2>Problem</h2><p>LDAP timeout in LDAP_Retry_Authenticator.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(
            html="<h2>Different</h2><p>Wrong content.</p>"
        )

        result = rich_metric(gold, pred)

        # The feedback has to contain a concrete detail (why it is bad)
        assert len(result.feedback) > 30, f"Feedback too short: {result.feedback}"
        # The feedback contains the word "mismatch" or "wrong", or a concrete detail
        assert any(word in result.feedback.lower() for word in ["mismatch", "wrong", "expected", "missing", "incorrect"])

    def test_not_a_dict(self):
        """The metric does NOT return a dict (GEPA contract)."""
        gold = dspy.Example(story_text="Test", html="<h2>A</h2>").with_inputs("story_text")
        pred = dspy.Prediction(html="<h2>A</h2>")

        result = rich_metric(gold, pred)

        assert not isinstance(result, dict), "Metric must return dspy.Prediction, not dict (GEPA contract)"


class TestHallucinationAxis:
    """US2 (spec 004): the rich_metric penalizes the hallucinated KB references."""

    def _gold(self):
        return dspy.Example(
            story_text="Story about Jira integration. Related article: KB7654321 was updated.",
            html="<h2>Problem</h2><p>Expected problem.</p>",
        ).with_inputs("story_text")

    def test_fictional_kb_number_is_penalized(self):
        """A KB number that is NOT in the story_text is a hallucination: the score drops + a feedback."""
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>See also KB0012345.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert "KB0012345" in result.feedback
        assert "Hallucinated" in result.feedback

    def test_real_kb_number_is_not_penalized(self):
        """A KB number that is in the story_text (KB7654321) does not count as a hallucination."""
        pred = dspy.Prediction(
            html="<h2>Problem</h2><p>Expected problem.</p><p>See also KB7654321.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert "Hallucinated" not in result.feedback

    def test_placeholder_is_not_penalized(self):
        """The KBXXXXXXX placeholder and the N/A do not count as a hallucination."""
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
    """US1 (spec 007): the direction-sensitive template_adherence."""

    OUTBOUND_STORY = "Implement Outbound REST API for Jira bug creation. The outbound payload is sent to Jira."
    GOLD_OUTBOUND = "<h2>Overview / Summary</h2><p>Outbound integration.</p>"

    def test_outbound_story_with_filled_inbound_is_penalized(self):
        """An outbound story + a filled Inbound section → a Direction violation feedback."""
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
        """An outbound story + a missing/N/A Inbound section → no penalty."""
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        gold = dspy.Example(story_text=self.OUTBOUND_STORY, html=self.GOLD_OUTBOUND).with_inputs("story_text")
        result = rich_metric(gold, pred)
        assert "Direction violation" not in result.feedback

    def test_both_directions_skips_check(self):
        """If the story mentions both directions, the direction check is skipped."""
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
    """US1 (spec 007): a section that is unsupported according to the gold is penalized."""

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
    """Spec 007 addition: the penalty of an N/A-only section if the gold omits it."""

    def test_na_only_section_penalized_when_gold_omits(self):
        """In the pred 'Known Issues / N/A', there is no such section in the gold → a penalty + a feedback."""
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
        """If the gold also has the section, the N/A-only pred is not penalized here."""
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
        """Actually omitting a section that the gold omits → no feedback at all."""
        gold = dspy.Example(
            story_text="Outbound integration.",
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>",
        ).with_inputs("story_text")
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        result = rich_metric(gold, pred)
        assert "N/A-only section" not in result.feedback
        assert "Unsupported section" not in result.feedback


class TestComponentHallucination:
    """Spec 011 (US1): the rich_metric penalizes the fabricated component names."""

    STORY = (
        "Story: outbound Jira integration. Implemented Script Include "
        "'JiraIntegrationUtils' for payload mapping; the endpoint is "
        "https://example.atlassian.net/rest/api/2/issue. State 'Escalated' triggers it."
    )

    def _gold(self):
        return dspy.Example(
            story_text=self.STORY,
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>",
        ).with_inputs("story_text")

    def test_fabricated_component_name_is_penalized(self):
        """SC-001: a fabricated component name → hallucination 0 + the feedback names it."""
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>"
            "<p>The 'CHG Scheduled' Business Rule triggers the outbound call.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert result.axes["hallucination"] == 0.0
        assert "Hallucinated component name(s)" in result.feedback
        assert "CHG Scheduled" in result.feedback

    def test_real_component_names_are_not_penalized(self):
        """The names that appear in the story (quoted, CamelCase, dotted) are not penalized."""
        pred = dspy.Prediction(
            html="<h2>Overview / Summary</h2><p>Outbound integration.</p>"
            "<p>'JiraIntegrationUtils' maps the payload from example.atlassian.net "
            "when the state is 'Escalated'.</p>"
        )
        result = rich_metric(self._gold(), pred)
        assert result.axes["hallucination"] == 1.0
        assert "Hallucinated" not in result.feedback

    def test_gold_articles_have_no_false_positives(self):
        """SC-002 / FR-001: all the 8 gold HTMLs pass the component check."""
        from eval.dataset import load_gold_dataset
        from eval.metric import _find_hallucinated_components

        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        assert len(trainset) + len(valset) == 9
        for ex in trainset + valset:
            # Next to the related_articles_context the update_set_payloads is also evidence
            # (the rich_metric calls it this way — see the spec 011 US2 note in metric.py).
            evidence = (getattr(ex, "related_articles_context", "") or "") + "\n" + (
                getattr(ex, "update_set_payloads", "") or ""
            )
            found = _find_hallucinated_components(ex.html, ex.story_text, evidence)
            assert not found, f"False positive a gold cikkben: {found}"

    def test_whitelist_terms_are_not_flagged(self):
        """FR-003: the general terms (Business Rule, Script Include, Incident,
        ServiceNow) do not count as a component name."""
        from eval.metric import _find_hallucinated_components

        html = (
            "<p>The 'Business Rule' and the 'Script Include' handle the Incident "
            "in ServiceNow. A 'Change Request' is created.</p>"
        )
        found = _find_hallucinated_components(html, "Unrelated story text.", "")
        assert found == [], f"Whitelist elements marked as candidates: {found}"

    def test_axes_still_contain_hallucination(self):
        """The hallucination axis is still in the axes (FR-004)."""
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        result = rich_metric(self._gold(), pred)
        assert "hallucination" in result.axes
        assert result.axes["hallucination"] == 1.0

    def test_detector_is_fault_tolerant(self, monkeypatch):
        """FR-002: on an internal error the metric does not stop, the axis is neutral."""
        import eval.metric as metric_mod

        def _boom(*args, **kwargs):
            raise RuntimeError("a break")

        monkeypatch.setattr(metric_mod, "_find_hallucinated_components", _boom)
        pred = dspy.Prediction(html="<h2>Overview / Summary</h2><p>Outbound integration.</p>")
        result = rich_metric(self._gold(), pred)
        assert result.axes["hallucination"] == 1.0  # neutral: it does not penalize blindly



# ---------------------------------------------------------------------------
# Spec 014 (US1, T006): the instance axis — a NEW axis NEXT TO the existing ones (FR-006)
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, results):
        self.status_code = 200
        self._results = results

    def json(self):
        return {"result": self._results}


class _AllKnownSession:
    """Every name exists (the gold names are real — spec Assumptions)."""

    def get(self, url, params=None, timeout=None):
        return _FakeResponse([{"sys_id": "x"}])


class _EmptySession:
    """Nothing exists on the instance."""

    def get(self, url, params=None, timeout=None):
        return _FakeResponse([])


class _DownSession:
    def get(self, url, params=None, timeout=None):
        raise ConnectionError("mock instance down")


@pytest.fixture
def instance_axis(tmp_path):
    """Turning the instance axis on/off per test (a module-level state)."""
    from eval import metric as metric_mod
    from snow_kb.verification import SpotChecker

    def _configure(session):
        metric_mod.configure_instance_axis(
            SpotChecker(cache_path=tmp_path / "spotcheck.json", session=session,
                        base_url="https://mock/api/now/table")
            if session is not None else None
        )

    yield _configure
    metric_mod.configure_instance_axis(None)  # cleanup — the neutrality of the other tests


class TestInstanceAxis:
    """The instance axis of the metric (spec 014, FR-006: the story-based axis is untouched)."""

    def _gold_pred(self):
        html = ("<h2>Problem</h2><p>The Script Include JiraInboundUtils fails.</p>"
                "<h2>Solution</h2><ol><li>The fix.</li></ol>")
        gold = dspy.Example(
            story_text="A story about the fix of the JiraInboundUtils Script Include.",
            html=html,
        ).with_inputs("story_text")
        pred = dspy.Prediction(html=html)
        return gold, pred

    def test_axis_inactive_by_default(self):
        """In the base state (without a checker) there is no instance axis — the old
        behaviour is bit-identical (FR-006)."""
        gold, pred = self._gold_pred()
        result = rich_metric(gold, pred)
        axes = result.get("axes") or {}
        assert "instance" not in axes

    def test_all_names_exist_axis_1(self, instance_axis):
        """US1 scenario 2: only real names → the axis is 1.0."""
        instance_axis(_AllKnownSession())
        gold, pred = self._gold_pred()
        result = rich_metric(gold, pred)
        assert result.axes["instance"] == 1.0

    def test_missing_name_axis_0_and_named(self, instance_axis):
        """US1 scenario 1: a non-existent name → the axis is 0 AND it is named in the feedback."""
        instance_axis(_EmptySession())
        gold, pred = self._gold_pred()
        result = rich_metric(gold, pred)
        assert result.axes["instance"] == 0.0
        assert "JiraInboundUtils" in result.feedback
        # the penalty also shows up in the score (it penalizes by naming — US1)
        from eval import metric as metric_mod
        metric_mod.configure_instance_axis(None)
        clean = rich_metric(gold, pred)
        assert result.score < clean.score

    def test_lookup_failure_fail_open(self, instance_axis):
        """US1 scenario 3 / FR-002: a query error → the axis is skipped
        (neutral), the other axes and the score are unchanged."""
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
        """SC-001 (with a mock): 0 'does not exist' labels on the gold articles if the
        names exist according to the instance metadata."""
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
                f"a false 'does not exist' label on the gold: {result.feedback[:300]}")
