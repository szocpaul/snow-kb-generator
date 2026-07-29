"""metric.py — rich_metric (GEPA contract) for evaluating the quality of a KB article.

The rich_metric function compares the generated KB article (pred) with the gold standard
article (gold) and returns a dspy.Prediction(score=float, feedback=str) object.
The feedback is "load-bearing" — the GEPA reflection LM learns the improvements from it.
"""

from __future__ import annotations

import dspy

# Spec 010 (US1): the shared boilerplate prohibition list.
# The same list is used by: the style block of GenerateKbFromTemplate (in sync with the
# check of tests/test_style_guidance.py), the style judge prompt (US2) and the
# SC-001 regex check.
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

    # 3. Template adherence — only the evidence-first checks (spec 007+).
    # The old presence-based N/A check (_check_template_adherence) is REMOVED:
    # since the evidence-first approach the N/A is forbidden everywhere, the layer added noise.
    template_adherence = 1.0

    # 3a. The evidence-first checks (spec 007):
    # - Direction violation: an outbound story + a filled Inbound section (and vice versa)
    # - Unsupported section: a section that is N/A/missing in the gold is filled in the pred
    story_text_for_direction = getattr(gold, "story_text", "") or ""
    direction_violations = _find_direction_violations(story_text_for_direction, actual_html)
    unsupported_sections = _find_unsupported_sections(expected_html, actual_html)
    na_only_sections = _find_na_only_sections(expected_html, actual_html)
    if direction_violations or unsupported_sections or na_only_sections:
        template_adherence = 0.0

    # 3b. Hallucination detection (spec 004): the KB appearing in the generated HTML
    # the article numbers must be in the story_text (or a placeholder).
    story_text = getattr(gold, "story_text", "") or ""
    # Spec 005: the actual KB search results (related_articles_context) known references
    known_refs = story_text + "\n" + (getattr(gold, "related_articles_context", "") or "")
    hallucinated = _find_hallucinated_kb_references(actual_html, known_refs)
    hallucination_score = 0.0 if hallucinated else 1.0

    # 5. The style axis (spec 010, US2): LLM-as-judge, with error tolerance (FR-002).
    style_score, style_critique = _style_score(actual_html) if actual_html else (0.5, "")

    # The weighted sum — spec 010: 0.25 structure + 0.25 content + 0.15 template
    # + 0.15 hallucination + 0.20 style (the old one: 0.3/0.3/0.2/0.2, without style).
    score = (
        0.25 * structure_match
        + 0.25 * content_accuracy
        + 0.15 * template_adherence
        + 0.15 * hallucination_score
        + 0.20 * style_score
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

    return dspy.Prediction(score=score, feedback=feedback)


def _extract_headings(html: str) -> list[str]:
    """Extracts the HTML <h2> headings."""
    import re
    headings = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.DOTALL)
    return [h.strip() for h in headings if h.strip()]


# The internal system names that are still counted as facts.
_DOMAIN_NAMES: set[str] = {"Jira", "Conigma", "Almex", "Solman"}

# The generic words that are NOT counted as facts (template text / general English).
# Without these the content axis would give "free" points, or it would be noisy.
_FACT_STOPLIST: set[str] = {
    # template and section words
    "This", "That", "When", "What", "Who", "How", "Where", "Expected", "Symptoms",
    "Causes", "Steps", "Guide", "Issues", "Overview", "Summary", "Content", "Testing",
    "Known", "Investigation", "Resolution", "Prevention", "Purpose", "Background",
    "Typical", "Usage", "Scenarios", "Results", "Data", "Table", "Dependencies",
    "Authentication", "Method", "Retry", "Error", "Handling", "Technical",
    "Components", "Validation", "Quick", "Escalation", "Root", "Diagnostic",
    # the too generic technical abbreviations (they are in every article → free points)
    "API", "REST", "SOAP", "JSON", "HTML", "URL", "AND", "FOR", "THE", "NOT",
}


def _extract_facts(html: str) -> list[str]:
    """Extracts the fact identifiers from the HTML (NOT the sentence prefixes!).

    The lesson of spec 010: the earlier version matched the first 50 characters of the gold <p>
    sentences — that rewarded imitating the wording of the gold, which collided head-on
    with the style axis (the GEPA coded the "This document describes..." pattern in as
    mandatory because it brought the content point). Therefore the content axis
    is now STYLE-AGNOSTIC: it matches field names, component names, endpoints,
    article numbers and values — it rewards the FACTS, not the wording.
    """
    import re

    text = re.sub(r'<[^>]+>', ' ', html)  # removing the HTML tags
    facts: set[str] = set()

    # The quoted names: 'the name of the Business Rule', "Script Include" — typical component references
    for m in re.findall(r"['\u2018\u2019]([^'\u2018\u2019]{3,80})['\u2018\u2019]", text):
        facts.add(m.strip())

    # Record/article numbers (STRY0010005, STYLE-REF, CHG0001234)
    facts.update(re.findall(r'\b(?:KB\d{6,}|STRY\d{6,}|CHG\d{6,}|CTASK\d{6,})\b', text))

    # URL-ek / endpointok
    facts.update(u.rstrip('.,;') for u in re.findall(r'https?://[^\s<)&]+', text))

    # The snake_case and dot-separated identifiers (u_cd_state, change_task, auth.config)
    facts.update(re.findall(r'\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b', text))
    facts.update(re.findall(r'\b[a-z]+(?:\.[a-z0-9]+){1,}\b', text))

    # The camelCase identifiers (uCdState, acmeIntegrationFramework)
    facts.update(re.findall(r'\b[a-z]+[A-Z][A-Za-z0-9]+\b', text))

    # The ALLCAPS abbreviations (LDAP, IDOC, WBS, SSO, ACME)
    facts.update(re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', text))

    # The internal capitalised system/component names (ServiceNow, SolMan, OData,
    # ScriptedWebService) — the plain TitleCase words ("Change", "Business")
    # would be too noisy, so we only match the internal capitalised ones.
    facts.update(re.findall(r'\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b', text))
    facts.update(re.findall(r'\b[A-Z]{2,}[a-z]+[A-Z][A-Za-z0-9]*\b', text))  # VendorService-like

    # The domain whitelist: the internal system names without an internal capital letter
    facts.update(w for w in re.findall(r'\b[A-Z][a-z]{3,}\b', text) if w in _DOMAIN_NAMES)

    # Filtering: the stop list, too short, empty
    return sorted(
        f for f in facts
        if f and len(f) >= 3 and f not in _FACT_STOPLIST
    )


def detect_direction(story_text: str) -> str:
    """Detects the direction of the integration from the keywords of the story_text (spec 007).

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
    """The raw text of a <h2> section (without the HTML tags) up to the next <h2>."""
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
    """True, if the section exists and has meaningful content (not only 'N/A')."""
    import re

    text = _section_text(html, heading)
    if not text:
        return False
    # Only 'Content' + the N/A variants → there is no real content
    cleaned = re.sub(r"(?i)\bcontent\b", "", text)
    cleaned = re.sub(r"(?i)N/?A[.;]?", "", cleaned).strip(" -—:;")
    return len(cleaned) > 30


def _find_direction_violations(story_text: str, actual_html: str) -> list[str]:
    """The list of the direction violations (the special case of spec 007).

    For an outbound story the 'Inbound Technical Implementation' section must be missing
    (or N/A); if it is filled in that is a violation. With the 'both'/'unknown' direction there is no check.
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
    """The headings of the sections that are not supported according to the gold (N/A/missing),
    but appear with content in the generated article (the general case of spec 007).
    """
    unsupported = []
    # The direction sections are handled by the direction check — do not duplicate the feedback
    direction_headings = {"Inbound Technical Implementation", "Outbound Technical Implementation"}
    for heading in _extract_headings(actual_html):
        if heading.lower() == "content" or heading in direction_headings:
            continue
        if not _section_has_content(expected_html, heading) and _section_has_content(actual_html, heading):
            unsupported.append(heading)
    return unsupported


def _section_is_na_only(html: str, heading: str) -> bool:
    """True, if the section exists, but its content is only 'N/A' (a placeholder, not real content)."""
    import re

    text = _section_text(html, heading)
    if not text:
        return False
    # It is only N/A-only if it really contains the 'N/A' marker
    if not re.search(r"\bN/?A\b", text, re.IGNORECASE):
        return False
    cleaned = re.sub(r"(?i)\bcontent\b", "", text)
    cleaned = re.sub(r"(?i)\bN/?A\b[.;]?", "", cleaned).strip(" -—:;")
    return len(cleaned) <= 10 and not _section_has_content(html, heading)


def _find_na_only_sections(expected_html: str, actual_html: str) -> list[str]:
    """The headings of the sections that are N/A-only in the pred, but missing in the gold.

    According to the evidence-first rule the unsupported section MUST BE LEFT OUT —
    writing the 'N/A' placeholder is just as much an error as if it were filled in.
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
    """Finds the hallucinated KB article numbers in the generated HTML.

    A KB reference (KB + >=6 digits) is hallucinated if it does not appear in the
    story_text. The KBXXXXXXX placeholder and the 'N/A' do not count as a hallucination.
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
    engineer (STYLE-REF). Judge ONLY the writing style, not factual accuracy.

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
    """Loads the STYLE-REF style reference excerpt (cached).

    Instead of the full HTML we take a representative excerpt from the beginning
    (token saving — the judge prompt is sent on every metric call).
    In case of a missing file an empty string: the judge can work without a reference.
    """
    global _STYLE_REFERENCE_CACHE
    if _STYLE_REFERENCE_CACHE is None:
        from pathlib import Path

        ref_path = Path("data/examples/style_reference.html")
        _STYLE_REFERENCE_CACHE = (
            ref_path.read_text(encoding="utf-8")[:3000] if ref_path.exists() else ""
        )
    return _STYLE_REFERENCE_CACHE


def _style_score(html: str) -> tuple[float, str]:
    """Runs the style judge on the generated HTML.

    Returns:
        (score, critique) — score 0.0..1.0.

    FR-002 (error tolerance): any judge error (the LM is not configured, the local
    server is not available, parse error) case (0.5, "") — a neutral point, and the
    the metric never stops because of it. The error is logged at WARNING level.
    """
    import logging

    try:
        judge = dspy.Predict(StyleJudge)
        result = judge(article_html=html[:8000], style_reference=_load_style_reference())
        score = float(result.style_score)
        score = max(0.0, min(1.0, score))  # clamp: the model sometimes goes out of the scale
        return score, str(result.critique or "")
    except Exception as exc:  # noqa: BLE001 — deliberately wide net (FR-002)
        logging.getLogger(__name__).warning(
            "style judge error — neutral 0.5 point: %s: %s", type(exc).__name__, exc
        )
        return 0.5, ""
