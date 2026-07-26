"""metric.py — rich_metric (GEPA contract) for evaluating the quality of a KB article.

The rich_metric function compares the generated KB article (pred) with the gold standard
article (gold) and returns a dspy.Prediction(score=float, feedback=str) object.
The feedback is "load-bearing" — the GEPA reflection LM learns the improvements from it.
"""

from __future__ import annotations

import dspy


def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    """Evaluates the generated KB article against the gold standard.

    Args:
        gold: A gold standard dspy.Example (story_text + html).
        pred: the generated dspy.Prediction (html).
        trace: A DSPy trace (ha van).
        pred_name: A prediktor neve (ha van).
        pred_trace: A prediktor trace-e (ha van).

    Returns:
        dspy.Prediction(score=0.0..1.0, feedback=str) — a GEPA contract.
    """
    expected_html = gold.html or ""
    # The program returns a Prediction(article=KBArticle); the tests use pred.html.
    # We support both (article.html is the primary one).
    actual_html = getattr(pred, "html", None) or ""
    if not actual_html and getattr(pred, "article", None) is not None:
        actual_html = getattr(pred.article, "html", "") or ""

    # 1. Structure match (the HTML headings match)
    expected_headings = _extract_headings(expected_html)
    actual_headings = _extract_headings(actual_html)

    if not expected_headings:
        structure_match = 1.0  # if there is no expectation we accept it
    else:
        # The score shows how many expected headings appear in the generated one
        matched = sum(1 for h in expected_headings if h in actual_headings)
        structure_match = matched / len(expected_headings)

    # 2. Content accuracy (the facts match)
    # A simple keyword based match (not perfect, but enough for GEPA)
    expected_facts = _extract_facts(expected_html)
    actual_facts = _extract_facts(actual_html)

    if not expected_facts:
        content_accuracy = 1.0
    else:
        matched_facts = sum(1 for f in expected_facts if f in actual_facts)
        content_accuracy = matched_facts / len(expected_facts)

    # 3. Template adherence (template_context compliance)
    # If the template expects N/A, but the generated one is full of content (or vice versa), that is an error
    template_adherence = _check_template_adherence(expected_html, actual_html)

    # 3b. Hallucination detection (spec 004): the KB appearing in the generated HTML
    # the article numbers must be in the story_text (or a placeholder).
    story_text = getattr(gold, "story_text", "") or ""
    # Spec 005: the actual KB search results (related_articles_context) known references
    known_refs = story_text + "\n" + (getattr(gold, "related_articles_context", "") or "")
    hallucinated = _find_hallucinated_kb_references(actual_html, known_refs)
    hallucination_score = 0.0 if hallucinated else 1.0

    # Weighted sum (0.3 structure + 0.3 content + 0.2 template + 0.2 hallucination)
    score = (
        0.3 * structure_match
        + 0.3 * content_accuracy
        + 0.2 * template_adherence
        + 0.2 * hallucination_score
    )

    # 4. The feedback (the critique in natural language)
    parts = []

    if structure_match < 1.0:
        missing = [h for h in expected_headings if h not in actual_headings]
        if missing:
            parts.append(f"Structure mismatch. Missing expected headings: {', '.join(missing)}.")
        else:
            parts.append(f"Structure mismatch. Expected headings: {', '.join(expected_headings)}. Got: {', '.join(actual_headings)}.")

    if content_accuracy < 1.0:
        missing_facts = [f for f in expected_facts if f not in actual_facts]
        if missing_facts:
            parts.append(f"Content mismatch. Missing expected facts: {', '.join(missing_facts)}.")

    if template_adherence < 1.0:
        parts.append(f"Template violation. Expected 'N/A' for irrelevant section, got actual content instead.")

    if hallucinated:
        parts.append(
            "Hallucinated reference(s): "
            + ", ".join(hallucinated)
            + ". These KB article numbers do not appear in the source Story — remove them or use the KBXXXXXXX placeholder / 'N/A'."
        )

    if not parts:
        parts.append("Correct structure, accurate content, and proper template adherence.")

    feedback = " ".join(parts)

    return dspy.Prediction(score=score, feedback=feedback)


def _extract_headings(html: str) -> list[str]:
    """Extracts the HTML <h2> headings."""
    import re
    headings = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.DOTALL)
    return [h.strip() for h in headings if h.strip()]


def _extract_facts(html: str) -> list[str]:
    """Extracts the more important facts from the HTML (e.g. number, short_description, description, p content)."""
    import re
    facts = []

    # number (pl. STRY0010001)
    number_match = re.search(r'"number"\s*:\s*"([^"]+)"', html)
    if number_match:
        facts.append(number_match.group(1))

    # short_description (pl. "[Interface Mgmt]: ...")
    short_desc_match = re.search(r'"short_description"\s*:\s*"([^"]+)"', html)
    if short_desc_match:
        facts.append(short_desc_match.group(1))

    # description (pl. "Implemented an outbound REST integration...")
    desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', html)
    if desc_match:
        facts.append(desc_match.group(1)[:80])  # First 80 characters

    # <p> content (e.g. "Expected problem.")
    p_matches = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    for p in p_matches:
        p_clean = re.sub(r'<[^>]+>', '', p).strip()  # removing the HTML tags
        if p_clean and len(p_clean) > 5:
            facts.append(p_clean[:50])  # First 50 characters

    return facts


def _find_hallucinated_kb_references(actual_html: str, story_text: str) -> list[str]:
    """Finds the hallucinated KB article numbers in the generated HTML.

    A KB reference (KB + >=6 digits) is hallucinated if it does not appear in the
    story_text. The KBXXXXXXX placeholder and the 'N/A' do not count as a hallucination.
    """
    import re

    pattern = re.compile(r"\bKB\d{6,}\b")
    actual_refs = set(pattern.findall(actual_html))
    known_refs = set(pattern.findall(story_text))
    return sorted(actual_refs - known_refs)


def _check_template_adherence(expected_html: str, actual_html: str) -> float:
    """Checks whether the generated HTML complies with the template_context rules.

    If the template expects N/A (e.g. for the Inbound section, which is in an Outbound Story), but the generated
    is full of content (hallucination), that is an error. If the template is full, but the generated
    one writes N/A (underperformance), that is an error too.
    """
    # Simple check: if the template contains the text "N/A", the generated one must contain it too
    expected_na = "N/A" in expected_html
    actual_na = "N/A" in actual_html

    if expected_na and not actual_na:
        # The template expects N/A, but the generated one is full of content (hallucination)
        return 0.5
    if not expected_na and actual_na:
        # The template is full, but the generated one writes N/A (underperformance)
        return 0.5

    return 1.0
