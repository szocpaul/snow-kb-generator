"""dataset.py — Gold dataset loader for GEPA optimization.

Loads the gold_dataset.md file and creates dspy.Example objects in a
separate trainset (3) / valset (2) split.
"""

from __future__ import annotations

import re
from pathlib import Path

import dspy


_TEMPLATE_CACHE: str | None = None


def _load_template_context() -> str:
    """Loads the Integration Team HTML template (cached).

    If the file is missing, an empty string — the program then raises a ValueError
    (spec 009), which is the correct behaviour: no generation without a template.
    """
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        template_path = Path("data/examples/integration_team_template.html")
        _TEMPLATE_CACHE = (
            template_path.read_text(encoding="utf-8") if template_path.exists() else ""
        )
    return _TEMPLATE_CACHE


def load_gold_dataset(path: str | Path) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """Loads the gold_dataset.md file and returns a separate trainset/valset split.

    Args:
        path: The path of the gold_dataset.md file.

    Returns:
        (trainset, valset) tuple — dspy.Example objects (~half-half ratio,
        min. 2 in the valset). Every example contains the story_text, template_context,
        update_set_payloads (input) and html (expected output) fields.

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

        # Spec 011 (US2): optional Update Set payload block. If present, the program's
        # analyze_changes branch runs on it; the old 8 examples stay backwards compatible
        # (empty string → the program skips that branch).
        payloads_match = re.search(r"### Update Set Payloads\s*```xml\s*(.+?)```", raw, re.DOTALL)
        update_set_payloads = payloads_match.group(1).strip() if payloads_match else ""

        # Validation: story_text and html must not be empty
        if len(story_text) < 50:
            raise ValueError(f"Example {idx+1} has a too short story_text field ({len(story_text)} characters).")
        if "<h2>" not in html:
            raise ValueError(f"Example {idx+1} has no <h2> headings in its html field.")

        # Create the dspy.Example: story_text + template_context + update_set_payloads
        # (inputs), html (expected output). Spec 009: template_context is a mandatory
        # input — the gold examples use the Integration Team template (the same one
        # the pipeline downloads from ServiceNow).
        ex = dspy.Example(
            story_text=story_text,
            template_context=_load_template_context(),
            update_set_payloads=update_set_payloads,
            html=html,
        ).with_inputs("story_text", "template_context", "update_set_payloads")
        examples.append(ex)

    # Separate split: half of the examples go to the trainset, half to the valset (min. 2 valset).
    # 6 examples → 3/3; as new (prod) examples arrive, the ratio adjusts automatically.
    if len(examples) < 5:
        raise ValueError(
            f"The gold dataset contains fewer than 5 examples ({len(examples)}). "
            "GEPA optimization needs at least 5 examples."
        )

    n_val = max(2, len(examples) // 2)
    trainset = examples[:-n_val]
    valset = examples[-n_val:]

    return trainset, valset
