"""metric.py — rich_metric (GEPA contract) a KB cikk minőségének értékeléséhez.

A rich_metric függvény összehasonlítja a generált KB cikket (pred) a gold standard
cikkel (gold), és visszaad egy dspy.Prediction(score=float, feedback=str) objektumot.
A feedback "load-bearing" — a GEPA reflection LM ebből tanulja a javításokat.
"""

from __future__ import annotations

import dspy


def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    """Értékeli a generált KB cikket a gold standard ellen.

    Args:
        gold: A gold standard dspy.Example (story_text + html).
        pred: A generált dspy.Prediction (html).
        trace: A DSPy trace (ha van).
        pred_name: A prediktor neve (ha van).
        pred_trace: A prediktor trace-e (ha van).

    Returns:
        dspy.Prediction(score=0.0..1.0, feedback=str) — a GEPA contract.
    """
    expected_html = gold.html or ""
    actual_html = pred.html or ""

    # 1. Structure match (HTML fejlécek egyezése)
    expected_headings = _extract_headings(expected_html)
    actual_headings = _extract_headings(actual_html)

    if not expected_headings:
        structure_match = 1.0  # Ha nincs elvárás, elfogadjuk
    else:
        # A score azt mutatja, hogy hány elvart fejléc jelenik meg a generáltben
        matched = sum(1 for h in expected_headings if h in actual_headings)
        structure_match = matched / len(expected_headings)

    # 2. Content accuracy (tények egyezése)
    # Egyszerű kulcsszavas egyezés (nem tökéletes, de a GEPA számára elég)
    expected_facts = _extract_facts(expected_html)
    actual_facts = _extract_facts(actual_html)

    if not expected_facts:
        content_accuracy = 1.0
    else:
        matched_facts = sum(1 for f in expected_facts if f in actual_facts)
        content_accuracy = matched_facts / len(expected_facts)

    # 3. Template adherence (template_context betartása)
    # Ha a template N/A-t vár, de a generált tele van tartalommal (vagy fordítva), az hiba
    template_adherence = _check_template_adherence(expected_html, actual_html)

    # Súlyozott összesítés (0.4 structure + 0.4 content + 0.2 template)
    score = 0.4 * structure_match + 0.4 * content_accuracy + 0.2 * template_adherence

    # 4. Feedback (természetes nyelvű kritika)
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

    if not parts:
        parts.append("Correct structure, accurate content, and proper template adherence.")

    feedback = " ".join(parts)

    return dspy.Prediction(score=score, feedback=feedback)


def _extract_headings(html: str) -> list[str]:
    """Kinyeri a HTML <h2> fejléceket."""
    import re
    headings = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.DOTALL)
    return [h.strip() for h in headings if h.strip()]


def _extract_facts(html: str) -> list[str]:
    """Kinyeri a fontosabb tényeket a HTML-ből (pl. number, short_description, description, p tartalom)."""
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
        facts.append(desc_match.group(1)[:80])  # Első 80 karakter

    # <p> tartalom (pl. "Expected problem.")
    p_matches = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    for p in p_matches:
        p_clean = re.sub(r'<[^>]+>', '', p).strip()  # HTML tag-ek eltávolítása
        if p_clean and len(p_clean) > 5:
            facts.append(p_clean[:50])  # Első 50 karakter

    return facts


def _check_template_adherence(expected_html: str, actual_html: str) -> float:
    """Ellenőrzi, hogy a generált HTML betartja-e a template_context szabályait.

    Ha a template N/A-t vár (pl. Inbound fejezetre, ami Outbound Story-ban), de a generált
    tele van tartalommal (hallucination), az hiba. Ha a template tele van, de a generált
    N/A-t ír (alulteljesítés), az is hiba.
    """
    # Egyszerű ellenőrzés: ha a template "N/A" szöveget tartalmaz, a generáltnek is kell tartalmaznia
    expected_na = "N/A" in expected_html
    actual_na = "N/A" in actual_html

    if expected_na and not actual_na:
        # A template N/A-t vár, de a generált tele van tartalommal (hallucination)
        return 0.5
    if not expected_na and actual_na:
        # A template tele van, de a generált N/A-t ír (alulteljesítés)
        return 0.5

    return 1.0
