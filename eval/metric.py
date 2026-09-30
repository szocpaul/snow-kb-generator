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


# ---------------------------------------------------------------------------
# Spec 014 (US1): the instance axis — a NEW axis NEXT TO the existing ones (FR-006)
# ---------------------------------------------------------------------------

# A module-level spot-checker injected in the tests/measurement. By default
# None → the axis is INACTIVE and the score formula is bit-identical to the behaviour
# before spec 014 (backwards compatibility, FR-006).
_INSTANCE_CHECKER = None
_INSTANCE_DECISION_CLIENT = None
_INSTANCE_DECISION_MODEL = ""
_INSTANCE_THRESHOLD = 0.7
_INSTANCE_AXIS_WEIGHT = 0.10  # if active: score = old*(1-w) + w*instance


def configure_instance_axis(checker, *, decision_client=None, decision_model: str = "",
                            confidence_threshold: float = 0.7) -> None:
    """Turns the instance axis on/off (None = inactive).

    The measurement (spec 014 T013) and the tests inject the SpotChecker; the
    production eval path does not configure it by default — then the axis is
    left out and the existing axes are untouched. The decision_client
    is for the calibrated layer (US3) — when None only the deterministic path runs.
    """
    global _INSTANCE_CHECKER, _INSTANCE_DECISION_CLIENT
    global _INSTANCE_DECISION_MODEL, _INSTANCE_THRESHOLD
    _INSTANCE_CHECKER = checker
    _INSTANCE_DECISION_CLIENT = decision_client
    _INSTANCE_DECISION_MODEL = decision_model
    _INSTANCE_THRESHOLD = confidence_threshold


def _instance_axis(html: str, update_set_text: str, story_context: str = "") -> tuple[float, list[str], bool]:
    """The instance axis: (score, non_existent_names, skipped).

    Fail-open (FR-002): on an error or a total dropout (1.0, [], True) —
    the axis is neutral, the pipeline/eval does not stop.
    """
    from snow_kb.verification import verify_component_names

    try:
        result = verify_component_names(
            html, update_set_text,
            spot_checker=_INSTANCE_CHECKER,
            story_context=story_context,
            decision_client=_INSTANCE_DECISION_CLIENT,
            decision_model=_INSTANCE_DECISION_MODEL,
            confidence_threshold=_INSTANCE_THRESHOLD,
        )
    except Exception as exc:  # noqa: BLE001 — deliberately wide net (FR-002)
        import logging

        logging.getLogger(__name__).warning(
            "instance axis error — skipped: %s: %s", type(exc).__name__, exc
        )
        return 1.0, [], True
    if result.skipped:
        return 1.0, [], True
    not_found = result.not_existing_names
    return (0.0 if not_found else 1.0), not_found, False


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

    # 3b. Hallucination detection. NOTE: for historical reasons the name of the axis is
    # "hallucination", but its scope is EXACTLY: (a) the KB article number validation
    # (spec 004, untouched) + (b) the validation of the named component names
    # (spec 011) — it does NOT mean a general "no hallucination" guarantee.
    story_text = getattr(gold, "story_text", "") or ""
    # Spec 005: the real KB search hits (related_articles_context) are known references
    related_context = getattr(gold, "related_articles_context", "") or ""
    known_refs = story_text + "\n" + related_context
    hallucinated = _find_hallucinated_kb_references(actual_html, known_refs)
    # Spec 011 (US1): the fabricated component names. FR-002 (error tolerance): on any
    # internal error a warning + neutral behaviour (the axis must not stop).
    # Spec 011 (US2): the update_set_payloads is also an evidence source — the names from the code analysis
    # (analyze_changes) are NOT hallucinations, because the program has seen them.
    update_set_payloads = getattr(gold, "update_set_payloads", "") or ""
    evidence_context = related_context + (
        "\n" + update_set_payloads if update_set_payloads else ""
    )
    try:
        hallucinated_components = _find_hallucinated_components(
            actual_html, story_text, evidence_context
        )
    except Exception as exc:  # noqa: BLE001 — deliberately wide net (FR-002)
        import logging

        logging.getLogger(__name__).warning(
            "component hallucination check error — skipped: %s: %s", type(exc).__name__, exc
        )
        hallucinated_components = []
    hallucination_score = 0.0 if (hallucinated or hallucinated_components) else 1.0

    # 5. The style axis (spec 010, US2): LLM-as-judge, with error tolerance (FR-002).
    style_score, style_critique = _style_score(actual_html) if actual_html else (0.5, "")

    # 5b. The instance axis (spec 014, US1): do the named component names exist
    # on the instance. A NEW axis NEXT TO the story-based check (FR-006) —
    # inactive by default (configure_instance_axis(None)); in the active state
    # the score is the old formula times (1-w) + w*instance, so when inactive it is
    # bit-identical to the old behaviour.
    instance_score = None
    instance_missing: list[str] = []
    if _INSTANCE_CHECKER is not None and actual_html:
        instance_score, instance_missing, instance_skipped = _instance_axis(
            actual_html, update_set_payloads, story_text
        )
        if instance_skipped:
            instance_score = None  # fail-open: the axis is skipped (neutral)

    # The weighted sum — spec 010: 0.25 structure + 0.25 content + 0.15 template
    # + 0.15 hallucination + 0.20 style (the old one: 0.3/0.3/0.2/0.2, without style).
    score = (
        0.25 * structure_match
        + 0.25 * content_accuracy
        + 0.15 * template_adherence
        + 0.15 * hallucination_score
        + 0.20 * style_score
    )
    if instance_score is not None:
        score = score * (1.0 - _INSTANCE_AXIS_WEIGHT) + _INSTANCE_AXIS_WEIGHT * instance_score

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

    if hallucinated_components:
        parts.append(
            "Hallucinated component name(s): "
            + ", ".join(f"'{c}'" for c in hallucinated_components)
            + ". These component names do not appear in the source Story — remove them, "
            "or refer to the component by its function instead of a fabricated name."
        )

    if instance_missing:
        parts.append(
            "Non-existent component name(s): "
            + ", ".join(f"'{c}'" for c in instance_missing)
            + ". These component names do not exist in the target instance's metadata "
            "(checked via Update Set whitelist + per-name spot-check) — remove them or "
            "correct them to the real component name."
        )

    if style_critique:
        parts.append(f"Style: {style_critique}")

    if not parts:
        parts.append("Correct structure, accurate content, and proper template adherence.")

    feedback = " ".join(parts)

    # T010c / FR-007: we also put the axis values into the Prediction, so that the
    # run_baseline can persist the per-axis statistics into the runs/*.json
    # (this does not break the GEPA contract: the score + feedback are unchanged).
    return dspy.Prediction(
        score=score,
        feedback=feedback,
        axes={
            "structure": structure_match,
            "content": content_accuracy,
            "template": template_adherence,
            "hallucination": hallucination_score,
            "style": style_score,
            # spec 014: the instance axis only appears in an active configuration
            **({"instance": instance_score} if instance_score is not None else {}),
        },
    )


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


# Spec 011 (US1): the general terms/product names that are NOT component names.
# It lives in one place together with the BANNED_PHRASES pattern; the _find_hallucinated_components
# uses this to filter the candidates (FR-003). False positive-first: we rather extend it,
# like giving noise to the GEPA (plan Key Decision 2).
COMPONENT_NAME_WHITELIST: list[str] = [
    # the general ServiceNow component TYPES (in quotes they denote a type, not a name)
    "Business Rule", "Script Include", "Client Script", "UI Action", "UI Policy",
    "Scripted REST API", "REST Message", "Flow Designer", "Update Set",
    "Access Control", "Data Policy", "Scheduled Job", "Email Notification",
    # the record/table types
    "Incident", "Change Request", "Change Task", "Problem",
    "Service Catalog", "Catalog Item", "Knowledge Base",
    # the product names
    "ServiceNow",
]

# The casefolded view for the fast lookup.
_COMPONENT_WHITELIST_CF: set[str] = {w.casefold() for w in COMPONENT_NAME_WHITELIST}


def _candidate_parts(candidate: str) -> list[str]:
    """Splits the candidate into evaluable parts (CamelCase humps + along the separators).

    Only the parts of >= 3 characters count ("Ch", "e", "g" are too short to
    denote an identifier — the 'e.g'/'i.e' abbreviations drop out this way as well).
    """
    import re

    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", candidate)
    return [w.lower() for w in words if len(w) >= 3]


def _component_verified(candidate: str, haystack: str) -> bool:
    """True, if the candidate can be verified in the source text (false positive-first).

    Three increasingly lenient tries (FR-001 / plan Key Decision 2-3):
      1. an exact (case-sensitive) occurrence,
      2. an alphanumerically normalized substring ('FrameWork' ~ '...FrameworkUtil'),
      3. every part of >= 3 characters (CamelCase hump / dotted segment) individually
         is in the normalized text — the gold articles often refer in a fragment-like way
         hivatkoznak ('ChTask' ~ 'Change Tasks', 'interface.solman' ~ user-id).
    """
    import re

    if candidate in haystack:
        return True
    norm_hay = re.sub(r"[^a-z0-9]", "", haystack.lower())
    norm_cand = re.sub(r"[^a-z0-9]", "", candidate.lower())
    if norm_cand and norm_cand in norm_hay:
        return True
    parts = _candidate_parts(candidate)
    return bool(parts) and all(p in norm_hay for p in parts)


def _find_hallucinated_components(
    html: str, story_text: str, related_articles_context: str = ""
) -> list[str]:
    """Finds the fabricated component names in the generated HTML (spec 011, US1).

    It is added next to the spec 004 KB number check: it extends the hallucination
    detection to the named components (the blind spot of the T013 review on 2026-08-09:
    'CHG Scheduled' a fabricated Business Rule name, with hallucination: 1.000).

    The candidates (conservative extraction, plan Key Decision 3 — from the prototype in
    the 30th section of Agent.md, tuned to be false-positive free on the 8 gold articles):
      - the 'quoted names' (starting with a capital, between simple quotes),
      - the dotted identifiers (a segment of at least 2 characters is needed — 'e.g' drops out),
      - the CamelCase identifiers.
    The URLs, the email addresses and the HTML attributes are NOT candidates (we remove them first).

    A candidate is fabricated if it cannot be verified in the concatenated story_text +
    related_articles_context (see _component_verified) AND it is not in the
    COMPONENT_NAME_WHITELIST-en.
    """
    import re

    text = re.sub(r"<[^>]+>", " ", html)  # drop the tags + the attribute URLs
    text = re.sub(r"https?://\S+", " ", text)  # the visible URLs (e.g. the link text)
    text = re.sub(r"\b\S+@\S+\b", " ", text)  # the email addresses

    candidates = re.findall(r"'([A-Z][A-Za-z0-9 _.:/-]{2,50})'", text)  # the quoted names
    candidates += [
        d
        for d in re.findall(r"\b([a-z]+[a-z0-9]*(?:\.[a-z0-9_]+)+)\b", text)
        if any(len(seg) >= 2 for seg in d.split("."))  # 'e.g'/'i.e' kiesik
    ]
    candidates += re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", text)  # CamelCase

    haystack = story_text + "\n" + related_articles_context
    hallucinated = []
    for cand in candidates:
        cand = cand.strip()
        if not cand or cand in hallucinated:
            continue
        if cand.casefold() in _COMPONENT_WHITELIST_CF:
            continue
        if not _component_verified(cand, haystack):
            hallucinated.append(cand)
    return hallucinated


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


# Spec 012 (US1): multi-sample style scoring — the number of the judge calls.
# The tests can override it (FR-002). The standard deviation of the average of the samples is ≈ σ/√n,
# so N=3 reduces the between-run standard deviation of 0.188 to ~0.11 (plan Key Decision 2).
STYLE_JUDGE_SAMPLES: int = 3


def _style_score(html: str) -> tuple[float, str]:
    """Runs the style judge on the generated HTML with N samples (spec 012).

    Returns:
        (score, critique) — the score is the average of the clamped points of the SUCCESSFUL samples
        (0.0..1.0); the critique comes from the sample closest to the average (FR-003 — the GEPA
        reflection needs a concrete, representative text).

    Error tolerance:
      - 1..N-1 failed calls (FR-001): mean(the remaining successful samples) + warning —
        NOT a neutral 0.5 (the error tolerance must not be a noise source);
      - every call failed (spec 010 FR-002, untouched): (0.5, "") — a neutral
        point, the metric never stops because of it, a warning is logged.
    """
    import logging

    logger = logging.getLogger(__name__)
    n = max(1, int(STYLE_JUDGE_SAMPLES))
    samples: list[tuple[float, str]] = []
    failures = 0
    for i in range(n):
        try:
            judge = dspy.Predict(StyleJudge)
            result = judge(
                article_html=html[:8000], style_reference=_load_style_reference()
            )
            score = float(result.style_score)
            score = max(0.0, min(1.0, score))  # clamp: the model sometimes goes out of the scale
            samples.append((score, str(result.critique or "")))
        except Exception as exc:  # noqa: BLE001 — a deliberately wide net (FR-001)
            failures += 1
            logger.warning(
                "style judge sample %d/%d error: %s: %s",
                i + 1, n, type(exc).__name__, exc,
            )

    if not samples:
        logger.warning(
            "style judge: all %d calls failed — a neutral 0.5 point", n
        )
        return 0.5, ""

    if failures:
        logger.warning(
            "style judge: %d/%d calls failed — the average of the remaining %d samples",
            failures, n, len(samples),
        )

    mean_score = sum(s for s, _ in samples) / len(samples)
    # The critique comes from the sample closest to the mean (FR-003 / plan Key Decision 4).
    closest = min(samples, key=lambda sc: abs(sc[0] - mean_score))
    return mean_score, closest[1]
