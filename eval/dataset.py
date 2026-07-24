"""dataset.py — Gold dataset loader for GEPA optimization.

Loads the gold_dataset.md file and creates dspy.Example objects in a
separate trainset (3) / valset (2) split.
"""

from __future__ import annotations

import re
from pathlib import Path

import dspy


def load_gold_dataset(path: str | Path) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """Loads the gold_dataset.md file and returns a separate trainset/valset split.

    Args:
        path: The path of the gold_dataset.md file.

    Returns:
        (trainset, valset) tuple — 3 trainset and 2 valset dspy.Example objects.
        Every example contains the story_text (input) and html (expected output) fields.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file format is invalid (fewer than 5 examples, or missing fields).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Gold dataset not found: {path}")

    content = path.read_text(encoding="utf-8")

    # The file structure is split into "## Example N: ..." sections.
    # Because of the special Unicode characters, a plain split does not work,
    # so we split on lines starting with "## " (double hash + space),
    # but only those followed by "Example" (the other headings are skipped).
    examples_raw = re.split(r"^## E", content, flags=re.MULTILINE)
    examples_raw = [e.strip() for e in examples_raw if e.strip() and e.startswith("xample ")]

    examples = []

    for idx, raw in enumerate(examples_raw):
        # Extract the Story (json block)
        # After the "### Story" heading: a new line, then ```json, the content, then ```
        story_match = re.search(r"### Story\s*```json\s*(.+?)```", raw, re.DOTALL)
        if not story_match:
            raise ValueError(f"Example {idx+1} is missing the '### Story' block.")

        story_text = story_match.group(1).strip()

        # Extract the KB article (html block)
        # The "(Gold Article)" suffix is optional — the gold_dataset.md contains it,
        # but the test fixtures and the earlier format only use "### Expected KB Article"
        html_match = re.search(r"### Expected KB Article(?: \(Gold Article\))?\s*```html\s*(.+?)```", raw, re.DOTALL)
        if not html_match:
            raise ValueError(f"Example {idx+1} is missing the '### Expected KB Article (Gold Article)' block.")

        html = html_match.group(1).strip()

        # Validation: story_text and html must not be empty
        if len(story_text) < 50:
            raise ValueError(f"Example {idx+1} has a too short story_text field ({len(story_text)} characters).")
        if "<h2>" not in html:
            raise ValueError(f"Example {idx+1} has no <h2> headings in its html field.")

        # creating the dspy.Example: story_text (input) + html (expected output)
        ex = dspy.Example(story_text=story_text, html=html).with_inputs("story_text")
        examples.append(ex)

    # Separated split: the first 3 are trainset, the last 2 are valset
    if len(examples) < 5:
        raise ValueError(
            f"The gold dataset contains fewer than 5 examples ({len(examples)}). "
            "GEPA optimization needs at least 5 examples."
        )

    trainset = examples[:3]
    valset = examples[3:5]

    return trainset, valset
