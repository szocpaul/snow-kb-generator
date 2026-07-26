"""test_eval_dataset.py — tests for the gold dataset loader."""

from __future__ import annotations

import dspy
import pytest

from eval.dataset import load_gold_dataset


class TestGoldDataset:
    """Tests for loading and validating the gold_dataset.md file."""

    def test_loads_5_examples(self):
        """Loads 5 gold example pairs from the file."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        assert len(trainset) == 3, f"Expected 3 trainset examples, got {len(trainset)}"
        assert len(valset) == 2, f"Expected 2 valset examples, got {len(valset)}"
        assert len(trainset) + len(valset) == 5

    def test_examples_have_story_text(self):
        """Every example contains the story_text field."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            assert hasattr(ex, "story_text"), f"Example missing story_text: {ex}"
            assert isinstance(ex.story_text, str)
            assert len(ex.story_text) > 50, "story_text is too short"

    def test_examples_have_expected_html(self):
        """Every example contains the expected_html field."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            assert hasattr(ex, "html"), f"Example missing html: {ex}"
            assert isinstance(ex.html, str)
            assert "<h2>" in ex.html, "expected_html does not contain <h2> headings"

    def test_examples_are_dspy_examples(self):
        """The examples are dspy.Example objects."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            assert isinstance(ex, dspy.Example)
            # with_inputs("story_text") is needed so that only story_text is an input
            assert "story_text" in ex.inputs()

    def test_trainset_valset_disjoint(self):
        """The trainset and valset are separate (no overlap)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        train_ids = {ex.story_text[:100] for ex in trainset}
        val_ids = {ex.story_text[:100] for ex in valset}
        assert train_ids.isdisjoint(val_ids), "Trainset and valset overlap!"


class TestGoldDatasetValidation:
    """Tests for validating the gold dataset (Story fields + KBA1-KBA11 structure)."""

    def test_dataset_has_complete_story_fields(self):
        """Every example contains the full Story fields (number, description, acceptance_criteria, technical_specification, work_notes, comments, state, assignment_group)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            story = ex.story_text
            assert '"number"' in story, "Story missing 'number' field"
            assert '"description"' in story, "Story missing 'description' field"
            assert '"acceptance_criteria"' in story, "Story missing 'acceptance_criteria' field"
            assert '"u_technical_specification"' in story, "Story missing 'u_technical_specification' field"
            assert '"work_notes"' in story, "Story missing 'work_notes' field"
            assert '"comments"' in story, "Story missing 'comments' field"
            assert '"state"' in story, "Story missing 'state' field"
            assert '"assignment_group"' in story, "Story missing 'assignment_group' field"

    def test_dataset_has_kba1_kba11_structure(self):
        """Every example contains the KBA1-KBA11 structure (Overview, Inbound, Outbound, Usage, Testing, Known Issues, Investigation)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            html = ex.html
            assert "<h2>Overview / Summary</h2>" in html, "Missing KBA1 (Overview / Summary)"
            assert "<h2>Inbound Technical Implementation</h2>" in html, "Missing KBA2 (Inbound Technical Implementation)"
            assert "<h2>Outbound Technical Implementation</h2>" in html, "Missing KBA3 (Outbound Technical Implementation)"
            assert "<h2>How to Use the Interface</h2>" in html, "Missing KBA4 (How to Use the Interface)"
            assert "<h2>Testing Guide</h2>" in html, "Missing KBA5 (Testing Guide)"
            assert "<h2>Known Issues</h2>" in html, "Missing KBA6-KBA10 (Known Issues)"
            assert "<h2>Investigation Steps</h2>" in html, "Missing KBA11 (Investigation Steps)"


class TestGoldDatasetErrorHandling:
    """Tests for the gold dataset error handling (malformed/incomplete data)."""

    def test_malformed_story_raises_error(self, tmp_path):
        """If the Story block is missing, a ValueError is raised."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("## Example 1\n### Expected KB Article\n```html\n<h2>A</h2>\n```")
        with pytest.raises(ValueError, match="missing the '### Story' block"):
            load_gold_dataset(bad_file)

    def test_missing_html_raises_error(self, tmp_path):
        """If the KB article block is missing, a ValueError is raised."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("## Example 1\n### Story\n```json\n{}\n```")
        with pytest.raises(ValueError, match="missing the '### Expected KB Article"):
            load_gold_dataset(bad_file)

    def test_short_story_raises_error(self, tmp_path):
        """If the story_text is too short (<50 characters), a ValueError is raised."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("## Example 1\n### Story\n```json\n{\"number\": \"A\"}\n```\n### Expected KB Article\n```html\n<h2>A</h2>\n```")
        with pytest.raises(ValueError, match="too short story_text field"):
            load_gold_dataset(bad_file)

    def test_no_h2_raises_error(self, tmp_path):
        """If the html has no <h2> heading, a ValueError is raised."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("## Example 1\n### Story\n```json\n{\"number\": \"A\", \"description\": \"This is a long enough description to pass the 50 char check.\"}\n```\n### Expected KB Article\n```html\n<p>No headings here</p>\n```")
        with pytest.raises(ValueError, match="no <h2> headings"):
            load_gold_dataset(bad_file)


class TestGoldDatasetNoFictionalReferences:
    """US1 (spec 004): the gold dataset must not contain fictional KB article numbers."""

    def test_no_fictional_kb_numbers_in_gold_articles(self):
        """No example article may contain a KB number disguised as real.

        Allowed: the KBXXXXXXX placeholder. Forbidden: a KB + digits pattern.
        """
        import re

        from eval.dataset import load_gold_dataset

        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        pattern = re.compile(r"\bKB\d{6,}\b")
        for example in trainset + valset:
            found = pattern.findall(example.html)
            assert not found, f"Fictional KB number in the gold article: {found}"
