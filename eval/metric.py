"""metric.py — rich_metric (GEPA contract) a KB cikk minőségének értékeléséhez.

A rich_metric függvény összehasonlítja a generált KB cikket (pred) a gold standard
cikkel (gold), és visszaad egy dspy.Prediction(score=float, feedback=str) objektumot.
A feedback "load-bearing" — a GEPA reflection LM ebből tanulja a javításokat.
"""

from __future__ import annotations

import dspy

# Spec 010 (US1): megosztott boilerplate-tiltólista.
# Ugyanezt a listát használja: a GenerateKbFromTemplate stílus-blokkja (szinkront a
# tests/test_style_guidance.py ellenőriz), a style judge promptja (US2) és az
# SC-001 regex-ellenőrzés.
BANNED_PHRASES: list[str] = [
    "This document describes",
    "This document outlines",
    "This article describes",
    "seamless",
    "seamlessly",
    "leverage",
    "In today's fast-paced world",
    "It is important to note",
    "plays a crucial role",
    "In conclusion",
]


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

    # 3. Template adherence — csak az evidence-first ellenőrzések (spec 007+).
    # A régi N/A-jelenlét-alapú check (_check_template_adherence) KIVEZETVE:
    # az evidence-first óta az N/A mindenhol tiltott, a réteg zajt adott.
    template_adherence = 1.0

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

    # 5. Style axis (spec 010, US2): LLM-as-judge, hibatűrő (FR-002).
    style_score, style_critique = _style_score(actual_html) if actual_html else (0.5, "")

    # Súlyozott összesítés — spec 010: 0.25 structure + 0.25 content + 0.15 template
    # + 0.15 hallucination + 0.20 style (régi: 0.3/0.3/0.2/0.2, style nélkül).
    score = (
        0.25 * structure_match
        + 0.25 * content_accuracy
        + 0.15 * template_adherence
        + 0.15 * hallucination_score
        + 0.20 * style_score
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

    if style_critique:
        parts.append(f"Style: {style_critique}")

    if not parts:
        parts.append("Correct structure, accurate content, and proper template adherence.")

    feedback = " ".join(parts)

    # T010c / FR-007: a tengely-értékeket is a Predictionbe tesszük, hogy a
    # run_baseline per-axis statisztikát perzisztálhasson a runs/*.json-be
    # (a GEPA contractot ez nem sérti: a score + feedback változatlan).
    return dspy.Prediction(
        score=score,
        feedback=feedback,
        axes={
            "structure": structure_match,
            "content": content_accuracy,
            "template": template_adherence,
            "hallucination": hallucination_score,
            "style": style_score,
        },
    )


def _extract_headings(html: str) -> list[str]:
    """Kinyeri a HTML <h2> fejléceket."""
    import re
    headings = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.DOTALL)
    return [h.strip() for h in headings if h.strip()]


# Belső nagybetű nélküli rendszernevek, amiket mégis ténynek számítunk.
_DOMAIN_NAMES: set[str] = {"Jira", "Conigma", "Almex", "Solman"}

# Generikus szavak, amik NEM számítanak ténynek (template-szöveg / általános angol).
# Ezek nélkül a content tengely "ingyen" pontokat adna, illetve zajos lenne.
_FACT_STOPLIST: set[str] = {
    # template- és szekciószavak
    "This", "That", "When", "What", "Who", "How", "Where", "Expected", "Symptoms",
    "Causes", "Steps", "Guide", "Issues", "Overview", "Summary", "Content", "Testing",
    "Known", "Investigation", "Resolution", "Prevention", "Purpose", "Background",
    "Typical", "Usage", "Scenarios", "Results", "Data", "Table", "Dependencies",
    "Authentication", "Method", "Retry", "Error", "Handling", "Technical",
    "Components", "Validation", "Quick", "Escalation", "Root", "Diagnostic",
    # túl generikus technikai rövidítések (minden cikkben ott vannak → ingyen pont)
    "API", "REST", "SOAP", "JSON", "HTML", "URL", "AND", "FOR", "THE", "NOT",
}


def _extract_facts(html: str) -> list[str]:
    """Tény-azonosítókat nyer ki a HTML-ből (NEM mondat-prefixeket!).

    Spec 010 tanulsága: a korábbi verzió a gold <p> mondatok első 50 karakterét
    illesztette — ez a gold megfogalmazásának utánzását jutalmazta, ami frontálisan
    ütközött a style tengellyel (a GEPA a "This document describes..." sémát
    kódolta be kötelezőnek, mert az content-pontot hozott). Ezért a content tengely
    mostantól STÍLUS-SEMLEGES: mezőneveket, komponensneveket, endpointokat,
    cikkszámokat és értékeket illeszt — a TÉNYEKET jutalmazza, nem a fogalmazást.
    """
    import re

    text = re.sub(r'<[^>]+>', ' ', html)  # HTML tag-ek eltávolítása
    facts: set[str] = set()

    # Idézett nevek: 'Business Rule neve', "Script Include" — tipikus komponenshivatkozások
    for m in re.findall(r"['\u2018\u2019]([^'\u2018\u2019]{3,80})['\u2018\u2019]", text):
        facts.add(m.strip())

    # Rekord-/cikkszámok (STRY0010005, KB0010015, CHG0001234)
    facts.update(re.findall(r'\b(?:KB\d{6,}|STRY\d{6,}|CHG\d{6,}|CTASK\d{6,})\b', text))

    # URL-ek / endpointok
    facts.update(u.rstrip('.,;') for u in re.findall(r'https?://[^\s<)&]+', text))

    # snake_case és pont-tagolt azonosítók (u_cd_state, change_task, auth.config)
    facts.update(re.findall(r'\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b', text))
    facts.update(re.findall(r'\b[a-z]+(?:\.[a-z0-9]+){1,}\b', text))

    # camelCase azonosítók (uCdState, aldiIntegrationFramework)
    facts.update(re.findall(r'\b[a-z]+[A-Z][A-Za-z0-9]+\b', text))

    # ALLCAPS rövidítések (LDAP, IDOC, WBS, SSO, ALDI)
    facts.update(re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', text))

    # Belső nagybetűs rendszer-/komponensnevek (ServiceNow, SolMan, OData,
    # ScriptedWebService) — a sima TitleCase szavak ("Change", "Business")
    # túl zajosak lennének, ezért csak belső nagybetűst illesztünk.
    facts.update(re.findall(r'\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b', text))
    facts.update(re.findall(r'\b[A-Z]{2,}[a-z]+[A-Z][A-Za-z0-9]*\b', text))  # ALDIAlmex-jellegű

    # Domain whitelist: belső nagybetű nélküli rendszernevek
    facts.update(w for w in re.findall(r'\b[A-Z][a-z]{3,}\b', text) if w in _DOMAIN_NAMES)

    # Szűrés: stoplist, túl rövid, üres
    return sorted(
        f for f in facts
        if f and len(f) >= 3 and f not in _FACT_STOPLIST
    )


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


# ---------------------------------------------------------------------------
# Spec 010 (US2): Style axis — LLM-as-judge
# ---------------------------------------------------------------------------


class StyleJudge(dspy.Signature):
    """You are a strict writing-style reviewer for ServiceNow KB articles.

    You receive an article (article_html) and a positive style reference
    (style_reference) — an excerpt from a hand-written KB article by a senior
    engineer (KB0010015). Judge ONLY the writing style, not factual accuracy.

    Score the article from 0.0 to 1.0:
    - 1.0: reads like the reference — direct facts, concrete identifiers
      (field names, endpoints, script names, values), varied sentence rhythm,
      active voice.
    - 0.0: machine-generated boilerplate — generic filler, vague claims,
      uniform sentence length.

    AUTOMATIC deductions for boilerplate phrases such as: "This document describes",
    "This document outlines", "This article describes", "seamless", "seamlessly",
    "leverage", "In today's fast-paced world", "It is important to note",
    "plays a crucial role", "In conclusion".

    In the critique, ALWAYS name the concrete phrase or sentence you penalized
    and explain briefly why it sounds machine-generated.
    """

    article_html: str = dspy.InputField(desc="The generated KB article HTML to judge.")
    style_reference: str = dspy.InputField(
        desc="Excerpt from a hand-written senior-engineer KB article (positive style example)."
    )
    style_score: float = dspy.OutputField(desc="Style score between 0.0 and 1.0.")
    critique: str = dspy.OutputField(
        desc="Concrete critique: which phrase/sentence sounds machine-generated and why."
    )


_STYLE_REFERENCE_CACHE: str | None = None


def _load_style_reference() -> str:
    """A KB0010015 stílus-referencia részlet betöltése (cache-elve).

    A teljes HTML helyett az elejéből veszünk egy reprezentatív részletet
    (token-takarékosság — a judge prompt minden metric call-ban kimegy).
    Hiányzó fájl esetén üres string: a judge referencia nélkül is dolgozhat.
    """
    global _STYLE_REFERENCE_CACHE
    if _STYLE_REFERENCE_CACHE is None:
        from pathlib import Path

        ref_path = Path("data/examples/kb0010015_style_reference.html")
        _STYLE_REFERENCE_CACHE = (
            ref_path.read_text(encoding="utf-8")[:3000] if ref_path.exists() else ""
        )
    return _STYLE_REFERENCE_CACHE


def _style_score(html: str) -> tuple[float, str]:
    """Lefuttatja a style judge-t a generált HTML-en.

    Returns:
        (score, critique) — score 0.0..1.0.

    FR-002 (hibatűrés): bármilyen judge-hiba (LM nincs konfigurálva, a lokális
    szerver nem elérhető, parse-hiba) esetén (0.5, "") — semleges pont, és a
    metric sosem áll meg miatta. A hiba WARNING szinten naplózva.
    """
    import logging

    try:
        judge = dspy.Predict(StyleJudge)
        result = judge(article_html=html[:8000], style_reference=_load_style_reference())
        score = float(result.style_score)
        score = max(0.0, min(1.0, score))  # clamp: a model néha kilóg a skáláról
        return score, str(result.critique or "")
    except Exception as exc:  # noqa: BLE001 — szándékosan széles háló (FR-002)
        logging.getLogger(__name__).warning(
            "style judge hiba — semleges 0.5 pont: %s: %s", type(exc).__name__, exc
        )
        return 0.5, ""
