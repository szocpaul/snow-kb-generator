"""test_eval_dataset.py — a gold dataset loader tesztjei."""

from __future__ import annotations

import dspy
import pytest

from eval.dataset import load_gold_dataset


class TestGoldDataset:
    """A gold_dataset.md fájl betöltésének és validálásának tesztjei."""

    def test_loads_5_examples(self):
        """5 arany példapárt tölt be a fájlból."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        assert len(trainset) == 3, f"Expected 3 trainset examples, got {len(trainset)}"
        assert len(valset) == 2, f"Expected 2 valset examples, got {len(valset)}"
        assert len(trainset) + len(valset) == 5

    def test_examples_have_story_text(self):
        """Minden példa tartalmazza a story_text mezőt."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            assert hasattr(ex, "story_text"), f"Example missing story_text: {ex}"
            assert isinstance(ex.story_text, str)
            assert len(ex.story_text) > 50, "story_text is too short"

    def test_examples_have_expected_html(self):
        """Minden példa tartalmazza a expected_html mezőt."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            assert hasattr(ex, "html"), f"Example missing html: {ex}"
            assert isinstance(ex.html, str)
            assert "<h2>" in ex.html, "expected_html does not contain <h2> headings"

    def test_examples_are_dspy_examples(self):
        """A példák dspy.Example objektumok."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        for ex in trainset + valset:
            assert isinstance(ex, dspy.Example)
            # with_inputs("story_text") kell, hogy csak a story_text legyen input
            assert "story_text" in ex.inputs()

    def test_trainset_valset_disjoint(self):
        """A trainset és valset szeparált (nincs átfedés)."""
        trainset, valset = load_gold_dataset("data/examples/gold_dataset.md")
        train_ids = {ex.story_text[:100] for ex in trainset}
        val_ids = {ex.story_text[:100] for ex in valset}
        assert train_ids.isdisjoint(val_ids), "Trainset and valset overlap!"


class TestGoldDatasetValidation:
    """A gold dataset validálásának tesztjei (Story mezők + KBA1-KBA11 struktúra)."""

    def test_dataset_has_complete_story_fields(self):
        """Minden példa tartalmazza a teljes Story mezőket (number, description, acceptance_criteria, technical_specification, work_notes, comments, state, assignment_group)."""
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
        """Minden példa tartalmazza a KBA1-KBA11 struktúrát (Overview, Inbound, Outbound, Usage, Testing, Known Issues, Investigation)."""
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
    """A gold dataset hibakezelésének tesztjei (malformed/incomplete data)."""

    def test_malformed_story_raises_error(self, tmp_path):
        """Ha a Story blokk hiányzik, ValueError-t dob."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("## Példa 1\n### Várt KB Cikk\n```html\n<h2>A</h2>\n```")
        with pytest.raises(ValueError, match="hiányzik a '### Story' blokk"):
            load_gold_dataset(bad_file)

    def test_missing_html_raises_error(self, tmp_path):
        """Ha a KB cikk blokk hiányzik, ValueError-t dob."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("## Példa 1\n### Story\n```json\n{}\n```")
        with pytest.raises(ValueError, match="hiányzik a '### Várt KB Cikk"):
            load_gold_dataset(bad_file)

    def test_short_story_raises_error(self, tmp_path):
        """Ha a story_text túl rövid (<50 karakter), ValueError-t dob."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("## Példa 1\n### Story\n```json\n{\"number\": \"A\"}\n```\n### Várt KB Cikk\n```html\n<h2>A</h2>\n```")
        with pytest.raises(ValueError, match="story_text mezője túl rövid"):
            load_gold_dataset(bad_file)

    def test_no_h2_raises_error(self, tmp_path):
        """Ha a html nincs <h2> fejléc, ValueError-t dob."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("## Példa 1\n### Story\n```json\n{\"number\": \"A\", \"description\": \"This is a long enough description to pass the 50 char check.\"}\n```\n### Várt KB Cikk\n```html\n<p>No headings here</p>\n```")
        with pytest.raises(ValueError, match="nem tartalmaz <h2> fejléceket"):
            load_gold_dataset(bad_file)
