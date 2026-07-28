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
    # A program Prediction(article=KBArticle)-t ad vissza; a tesztek pred.html-t.
    # Mindkettőt támogatjuk (az article.html az elsődleges).
    actual_html = getattr(pred, "html", None) or ""
    if not actual_html and getattr(pred, "article", None) is not None:
        actual_html = getattr(pred.article, "html", "") or ""

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

    # 3a. Evidence-first ellenőrzések (spec 007):
    # - Direction violation: outbound story + kitöltött Inbound szekció (és fordítva)
    # - Unsupported section: a gold szerint N/A/hiányzó szekció a pred-ben kitöltve
    story_text_for_direction = getattr(gold, "story_text", "") or ""
    direction_violations = _find_direction_violations(story_text_for_direction, actual_html)
    unsupported_sections = _find_unsupported_sections(expected_html, actual_html)
    na_only_sections = _find_na_only_sections(expected_html, actual_html)
    if direction_violations or unsupported_sections or na_only_sections:
        template_adherence = 0.0

    # 3b. Hallucination detection (spec 004): a generált HTML-ben szereplő KB
    # cikkszámoknak a story_text-ben kell lenniük (vagy placeholder-nek).
    story_text = getattr(gold, "story_text", "") or ""
    # Spec 005: a valódi KB keresési találatok (related_articles_context) ismert hivatkozások
    known_refs = story_text + "\n" + (getattr(gold, "related_articles_context", "") or "")
    hallucinated = _find_hallucinated_kb_references(actual_html, known_refs)
    hallucination_score = 0.0 if hallucinated else 1.0

    # Súlyozott összesítés (0.3 structure + 0.3 content + 0.2 template + 0.2 hallucination)
    score = (
        0.3 * structure_match
        + 0.3 * content_accuracy
        + 0.2 * template_adherence
        + 0.2 * hallucination_score
    )

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

    if direction_violations:
        parts.extend(direction_violations)

    if unsupported_sections:
        parts.append(
            "Unsupported section(s): "
            + ", ".join(f"'{h}'" for h in unsupported_sections)
            + ". These sections have content but the story provides no evidence for them — omit them entirely (no evidence, no section)."
        )

    if na_only_sections:
        parts.append(
            "N/A-only section(s): "
            + ", ".join(f"'{h}'" for h in na_only_sections)
            + ". These sections contain only 'N/A' but the gold article omits them — do NOT write N/A placeholders, omit the section entirely."
        )

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


def detect_direction(story_text: str) -> str:
    """Az integráció irányának detektálása a story_text kulcsszavaiból (spec 007).

    Returns: 'inbound' | 'outbound' | 'both' | 'unknown'
    """
    import re

    n_in = len(re.findall(r"\binbound\b", story_text, re.IGNORECASE))
    n_out = len(re.findall(r"\boutbound\b", story_text, re.IGNORECASE))
    if n_in and n_out:
        return "both"
    if n_in:
        return "inbound"
    if n_out:
        return "outbound"
    return "unknown"


_DIRECTION_SECTIONS = {
    "inbound": "Outbound Technical Implementation",
    "outbound": "Inbound Technical Implementation",
}


def _section_text(html: str, heading: str) -> str:
    """Egy <h2> szekció nyers szövege (HTML tag-ek nélkül) a következő <h2>-ig."""
    import re

    m = re.search(
        r"<h2[^>]*>\s*" + re.escape(heading) + r"\s*</h2>(.*?)(?=<h2|$)",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return ""
    return re.sub(r"<[^>]+>", " ", m.group(1)).strip()


def _section_has_content(html: str, heading: str) -> bool:
    """True, ha a szekció létezik és értelmes tartalma van (nem csak 'N/A')."""
    import re

    text = _section_text(html, heading)
    if not text:
        return False
    # Csak 'Content' + N/A variánsok → nincs valódi tartalom
    cleaned = re.sub(r"(?i)\bcontent\b", "", text)
    cleaned = re.sub(r"(?i)N/?A[.;]?", "", cleaned).strip(" -—:;")
    return len(cleaned) > 30


def _find_direction_violations(story_text: str, actual_html: str) -> list[str]:
    """Direction violation-ök listája (spec 007 speciális eset).

    Outbound story esetén az 'Inbound Technical Implementation' szekciónak hiányoznia
    kell (vagy N/A-nak); kitöltve az violation. 'both'/'unknown' iránynál nincs ellenőrzés.
    """
    direction = detect_direction(story_text)
    if direction not in _DIRECTION_SECTIONS:
        return []
    forbidden = _DIRECTION_SECTIONS[direction]
    if _section_has_content(actual_html, forbidden):
        return [
            f"Direction violation: {direction} story but '{forbidden}' section is filled with content. "
            f"Omit this section entirely; shared components belong to the {direction} section."
        ]
    return []


def _find_unsupported_sections(expected_html: str, actual_html: str) -> list[str]:
    """Azon szekciók fejlécei, amik a gold szerint nincsenek támogatva (N/A/hiányzó),
    de a generált cikkben tartalommal szerepelnek (spec 007 általános eset).
    """
    unsupported = []
    # Az irány-szekciókat a direction check kezeli — ne duplikáljuk a feedback-et
    direction_headings = {"Inbound Technical Implementation", "Outbound Technical Implementation"}
    for heading in _extract_headings(actual_html):
        if heading.lower() == "content" or heading in direction_headings:
            continue
        if not _section_has_content(expected_html, heading) and _section_has_content(actual_html, heading):
            unsupported.append(heading)
    return unsupported


def _section_is_na_only(html: str, heading: str) -> bool:
    """True, ha a szekció létezik, de a tartalma csak 'N/A' (placeholder, nem valódi tartalom)."""
    import re

    text = _section_text(html, heading)
    if not text:
        return False
    # Csak akkor N/A-only, ha ténylegesen szerepel 'N/A' jelölés
    if not re.search(r"\bN/?A\b", text, re.IGNORECASE):
        return False
    cleaned = re.sub(r"(?i)\bcontent\b", "", text)
    cleaned = re.sub(r"(?i)\bN/?A\b[.;]?", "", cleaned).strip(" -—:;")
    return len(cleaned) <= 10 and not _section_has_content(html, heading)


def _find_na_only_sections(expected_html: str, actual_html: str) -> list[str]:
    """Azon szekciók fejlécei, amik a pred-ben N/A-only-k, de a goldban hiányoznak.

    Az evidence-first szabály szerint a támogatatlan szekciót KI KELL HAGYNI —
    az 'N/A' placeholder írása ugyanolyan hiba, mintha ki lenne töltve.
    """
    na_only = []
    for heading in _extract_headings(actual_html):
        if heading.lower() == "content":
            continue
        gold_has_section = bool(_section_text(expected_html, heading))
        if not gold_has_section and _section_is_na_only(actual_html, heading):
            na_only.append(heading)
    return na_only


def _find_hallucinated_kb_references(actual_html: str, story_text: str) -> list[str]:
    """Megkeresi a hallucinált KB cikkszámokat a generált HTML-ben.

    Egy KB hivatkozás (KB + >=6 számjegy) hallucinált, ha nem szerepel a
    story_text-ben. A KBXXXXXXX placeholder és az 'N/A' nem számít hallucinációnak.
    """
    import re

    pattern = re.compile(r"\bKB\d{6,}\b")
    actual_refs = set(pattern.findall(actual_html))
    known_refs = set(pattern.findall(story_text))
    return sorted(actual_refs - known_refs)


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
