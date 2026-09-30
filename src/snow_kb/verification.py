"""verification.py — component name verification against the instance (spec 014).

Before writing to ServiceNow it validates the named component names of the
generated KB article against the instance metadata:

  1. Candidate extraction (011 pattern: quoted names, CamelCase, dotted identifiers;
     the generic terms are dropped by the 011 whitelist; FQDN-like dotted
     names — the hosts of external systems — are dropped as well: T004 baseline lesson).
  2. Determinisztikus mag (plan KD2/KD3):
     a. Update Set whitelist (the content of the story's update set — primary);
     b. what is not in it: a per-name spot-check in the instance metadata
        (sys_db_object / sys_dictionary / sys_script / sys_script_include),
        JSON-cached (the cache is part of the recording → the replay is byte-identical,
        SC-004).
  3. The ambiguous cases (deterministically "not_exists") go to the calibrated
     layer (TypeSafe Noul, pinned model — FR-005): "this name is a real
     komponensre utal-e?" (plan KD2, US3).

Fail-open is mandatory (FR-002): on any query/SDK error the layer is skipped
with a warning and the pipeline continues on the existing path.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# The shared source of the 011 generic-term whitelist is the eval metric
# (per the tests/test_style_guidance.py pattern, the list lives in one place).
from eval.metric import COMPONENT_NAME_WHITELIST

logger = logging.getLogger(__name__)

_WHITELIST_CF: set[str] = {w.casefold() for w in COMPONENT_NAME_WHITELIST}

# Single-word workflow states / UI terms: NOT component names (the T004
# baseline lesson: false positives like 'Escalated', 'Retry', 'Scheduled').
# The T005 human gate approved the more SNOW-specific filtering.
_STATE_TERMS = {
    "escalated", "withdrawn", "confirmed", "retry", "scheduled", "closed",
    "open", "new", "resolved", "cancelled", "canceled", "pending", "draft",
    "approved", "rejected", "deferred", "completed", "failed",
}

# Log message suffixes: such quoted strings are error messages, not names
# (T004: samples like 'SnowKbGenerator work_note error', 'User Not Found').
_LOG_MESSAGE_SUFFIXES = (" error", " failed", " failure", " not found", " timeout")

# Public TLDs: the dotted names ending with these are external hosts/domains
# (the T004 baseline lesson: example-service.com, interface.solman-like false positives).
_TLD_SUFFIXES = {
    "com", "net", "org", "io", "de", "hu", "eu", "at", "ch", "co", "ai", "dev",
    "local", "internal", "corp", "lan",
}

# The ServiceNow metadata tables in which the spot-check searches (deploy/README.md).
_SPOTCHECK_TABLES = ("sys_db_object", "sys_script", "sys_script_include", "sys_dictionary")


# ---------------------------------------------------------------------------
# Adatmodell
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComponentCandidate:
    """A named entity extracted from the article + the extraction mode (Key Entities)."""

    name: str
    kind: str  # "quoted" | "dotted" | "camelcase"


@dataclass(frozen=True)
class NameVerdict:
    """The validation decision for a component name (Key Entities: validation decision)."""

    name: str
    status: Literal["exists", "not_exists", "not_applicable", "unknown"]
    confidence: float          # deterministic layer: 1.0
    evidence: str              # the logged evidence (table/field, whitelist, etc.)
    layer: str                 # "update_set" | "spotcheck" | "calibrated"


@dataclass
class VerificationResult:
    """A verify_component_names kimenete."""

    verdicts: list[NameVerdict] = field(default_factory=list)
    skipped: bool = False      # True if the check was skipped because of fail-open
    warning: str = ""

    @property
    def not_existing_names(self) -> list[str]:
        return [v.name for v in self.verdicts if v.status == "not_exists"]


# ---------------------------------------------------------------------------
# Candidate extraction (011 pattern, identical to the eval/metric.py regexes)
# ---------------------------------------------------------------------------

def extract_component_candidates(html: str) -> list[ComponentCandidate]:
    """Extracts the component name candidates with the 011 pattern.

    The extraction is IDENTICAL to the regular expressions of eval/metric.py's
    _find_hallucinated_components; the difference is in the filtering: here the
    story verification is replaced by the instance verification as the next step,
    so apart from the whitelist and the FQDN filtering every candidate goes on.
    """
    text = re.sub(r"<[^>]+>", " ", html)  # drop the tags + the attribute URLs
    text = re.sub(r"https?://\S+", " ", text)  # the visible URLs
    text = re.sub(r"\b\S+@\S+\b", " ", text)  # the email addresses

    candidates: list[ComponentCandidate] = []

    def _add(name: str, kind: str) -> None:
        name = name.strip()
        if not name or name.casefold() in _WHITELIST_CF:
            return
        # State words and log-message-like quoted strings are NOT component names
        if " " not in name and name.casefold() in _STATE_TERMS:
            return
        if kind == "quoted" and name.casefold().endswith(_LOG_MESSAGE_SUFFIXES):
            return
        if any(c.name == name for c in candidates):
            return
        candidates.append(ComponentCandidate(name=name, kind=kind))

    for m in re.findall(r"'([A-Z][A-Za-z0-9 _.:/-]{2,50})'", text):  # the quoted names
        _add(m, "quoted")
    for d in re.findall(r"\b([a-z]+[a-z0-9]*(?:\.[a-z0-9_]+)+)\b", text):  # dotted
        if not any(len(seg) >= 2 for seg in d.split(".")):  # 'e.g'/'i.e' kiesik
            continue
        if d.rsplit(".", 1)[-1].casefold() in _TLD_SUFFIXES:  # FQDN → external host
            continue
        _add(d, "dotted")
    for m in re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", text):  # CamelCase
        _add(m, "camelcase")

    return candidates


# ---------------------------------------------------------------------------
# Update Set whitelist (KD3: the primary ground truth)
# ---------------------------------------------------------------------------

def build_update_set_whitelist(update_set_text: str) -> set[str]:
    """The component names (casefold) from the output of get_update_set_changes.

    Two sources: the lines of the formatted change list ("- [ACTION] Type: Name")
    and the name attributes of the raw payload XMLs.
    """
    whitelist: set[str] = set()
    if not update_set_text:
        return whitelist
    for m in re.findall(r"^\s*-\s*\[[^\]]+\]\s*[^:]+:\s*(.+)$", update_set_text, re.M):
        name = m.strip()
        if name and name != "unknown":
            whitelist.add(name.casefold())
    for m in re.findall(r'\bname="([^"]+)"', update_set_text):
        whitelist.add(m.strip().casefold())
    return whitelist


# ---------------------------------------------------------------------------
# SpotChecker — per-name spot-check, cached (KD3)
# ---------------------------------------------------------------------------

class SpotChecker:
    """A per-name exists/does-not-exist query in the instance metadata.

    The cache (spotcheck_cache_path) is part of the recording: in cache-only mode
    (session=None) the earlier responses can be replayed byte-identically (SC-004),
    on a cache miss the answer is "unknown" (fail-open — in replay mode we do
    NOT manufacture a new "does not exist" decision).
    """

    def __init__(
        self,
        cache_path: str | Path,
        session: Any = None,
        base_url: str = "",
    ) -> None:
        self.cache_path = Path(cache_path)
        self.session = session
        self.base_url = base_url.rstrip("/")
        self._cache: dict[str, dict] = {}
        if self.cache_path.exists():
            try:
                self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001 — a broken cache must not stop it
                logger.warning("Spot-check cache read error (%s): %s — empty cache",
                               self.cache_path, exc)
                self._cache = {}

    # -- internal ----------------------------------------------------------

    _OBJECT_PREFIXES = ("current", "parent", "gs", "g")

    def _probes(self, name: str, kind: str) -> list[tuple[str, str, str]]:
        """The query list: (table, field, value) triples, by extraction mode.

        Semantics of a dotted name:
          - with an object prefix (current./parent./gs.): a field reference → the
            field name is looked up in the sys_dictionary;
          - otherwise the table[.field] shape → the EXISTENCE of the TABLE decides
            (the generic field names — sys_id, name — are too frequent for the
            field fallback: they would give a false "exists" for fabricated table names).
        """
        probes: list[tuple[str, str, str]] = []
        if kind == "dotted":
            segments = name.split(".")
            first, last = segments[0], segments[-1]
            if first in self._OBJECT_PREFIXES or first.startswith("g_"):
                if last and last != name:
                    probes.append(("sys_dictionary", "element", last))
            else:
                probes.append(("sys_db_object", "name", name))
                if first != name:
                    probes.append(("sys_db_object", "name", first))
        else:
            for table in ("sys_script_include", "sys_script", "sys_db_object"):
                probes.append((table, "name", name))
        return probes

    def _query(self, table: str, field_name: str, value: str) -> bool:
        """A Table API query: True if there is a hit. Error → exception."""
        resp = self.session.get(
            f"{self.base_url}/{table}",
            params={"sysparm_query": f"{field_name}={value}",
                    "sysparm_limit": "1", "sysparm_fields": "sys_id"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"{table} HTTP {resp.status_code}")
        return bool(resp.json().get("result"))

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self._cache, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001 — a cache write error must not decide
            logger.warning("Spot-check cache write error (%s): %s", self.cache_path, exc)

    # -- public -------------------------------------------------------------

    def check(self, name: str, kind: str = "quoted") -> NameVerdict:
        """The spot-check of a single name (cache-first).

        Returns:
            NameVerdict — status: exists / not_exists / unknown (an error or
            cache-miss in replay mode; FR-002 fail-open).
        """
        key = name.casefold()
        if key in self._cache:
            entry = self._cache[key]
            return NameVerdict(name=name, status=entry["status"], confidence=1.0,
                               evidence=entry["evidence"], layer="spotcheck")
        if self.session is None:
            return NameVerdict(name=name, status="unknown", confidence=0.0,
                               evidence="cache-miss, replay mode (no session)",
                               layer="spotcheck")
        try:
            for table, field_name, value in self._probes(name, kind):
                if self._query(table, field_name, value):
                    evidence = f"{table}.{field_name}={value}"
                    self._cache[key] = {"status": "exists", "evidence": evidence}
                    self._save_cache()
                    return NameVerdict(name=name, status="exists", confidence=1.0,
                                       evidence=evidence, layer="spotcheck")
            evidence = "no hit: " + ", ".join(t for t, _, _ in self._probes(name, kind))
            self._cache[key] = {"status": "not_exists", "evidence": evidence}
            self._save_cache()
            return NameVerdict(name=name, status="not_exists", confidence=1.0,
                               evidence=evidence, layer="spotcheck")
        except Exception as exc:  # noqa: BLE001 — deliberately wide net (FR-002)
            logger.warning("Spot-check error (%s): %s: %s — fail-open", name,
                           type(exc).__name__, exc)
            return NameVerdict(name=name, status="unknown", confidence=0.0,
                               evidence=f"{type(exc).__name__}: {exc}", layer="spotcheck")


# ---------------------------------------------------------------------------
# Calibrated layer (US3) — TypeSafe Noul, pinned model (FR-005)
# ---------------------------------------------------------------------------

_REFERS_QUESTION = (
    "Classify the name: (a) 'yes' — it refers to a real component that EXISTS on "
    "the given ServiceNow instance (table, field, Business Rule, Script "
    "Include etc.), possibly with a spelling variant or abbreviated; "
    "(b) 'external' — an object of an external (non-ServiceNow) system (e.g. SAP, "
    "SolMan, the Jira server side), a generic text fragment, a state or an "
    "error message — the gate does NOT validate these (spec Out of Scope); "
    "(c) 'no' — it LOOKS like a ServiceNow component, but it is fabricated/non-existent."
)

_REFERS_CRITERIA = {
    "yes": "the name refers to a real ServiceNow component (a spelling variant is possible)",
    "external": "an object of an external system, generic text, a state or an error message — not to be validated",
    "no": "it looks like a ServiceNow component, but it is fabricated or does not exist",
}

_REFERS_EPS = 1e-9  # the 013 pattern: the '<' operator + eps on the float boundary


def _calibrated_decision(
    name: str,
    story_context: str,
    *,
    client: Any,
    model: str,
    threshold: float,
) -> NameVerdict | None:
    """The calibrated decision about an ambiguous candidate (US3).

    Returns:
        NameVerdict layer="calibrated", or None in the fail-open case (the caller
        then keeps the result of the deterministic path).
    """
    from typesafe_sdk import Choice

    state = (
        f"Article excerpt context (the environment of the source story and/or of the article):\n"
        f"{story_context[:4000]}\n\n"
        f"Examined name: '{name}'"
    )
    questions = {"refers": Choice(instructions=_REFERS_QUESTION,
                                  criteria=dict(_REFERS_CRITERIA))}
    try:
        response = client.system_one(state=state, questions=questions, model=model)
        answer = response.answers["refers"]
        confidence = float(getattr(answer, "confidence", 0.0) or 0.0)
        choice = getattr(answer, "choice", None)
        # Threshold operator: '<' (not '<=') — exactly the threshold value leans
        # to the safe direction (the signal) (spec Edge Cases; the 013 pattern).
        confident = not (confidence < threshold + _REFERS_EPS)
        if choice == "yes" and confident:
            return NameVerdict(name=name, status="exists", confidence=confidence,
                               evidence=f"calibrated decision: reference (model={model})",
                               layer="calibrated")
        if choice == "external" and confident:
            # An object of an external system / generic text — the gate does NOT
            # validate it (spec Out of Scope), there is no signal.
            return NameVerdict(name=name, status="not_applicable", confidence=confidence,
                               evidence=f"calibrated decision: not a SNOW component "
                                        f"(model={model})",
                               layer="calibrated")
        return NameVerdict(name=name, status="not_exists", confidence=confidence,
                           evidence=f"calibrated decision: fabricated/low confidence "
                                    f"(model={model}, threshold={threshold})",
                           layer="calibrated")
    except Exception as exc:  # noqa: BLE001 — fail-open to the deterministic path
        logger.warning("Calibrated decision error (%s): %s: %s — fail-open",
                       name, type(exc).__name__, exc)
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def verify_component_names(
    article_html: str,
    update_set_text: str = "",
    *,
    spot_checker: SpotChecker | None = None,
    story_context: str = "",
    decision_client: Any = None,
    decision_model: str = "",
    confidence_threshold: float = 0.7,
) -> VerificationResult:
    """Validates the component names of the article against the instance (FR-001).

    Args:
        article_html: the HTML of the generated KB article.
        update_set_text: the output of get_update_set_changes (may be empty).
        spot_checker: the per-name spot-checker (None → the check is skipped).
        story_context: the context of the calibrated layer (story_text / article excerpt).
        decision_client: a system_one-compatible client for the calibrated layer
            (None → only the deterministic path runs).
        decision_model: the pinned decision model (FR-005).
        confidence_threshold: the calibrated gate (SC-002 confirmatory: 0.7).

    Returns:
        VerificationResult — the verdicts per candidate; skipped=True on fail-open.
    """
    result = VerificationResult()
    candidates = extract_component_candidates(article_html)
    if not candidates:
        return result
    if spot_checker is None:
        result.skipped = True
        result.warning = "no spot_checker — the instance verification is skipped"
        logger.warning(result.warning)
        return result

    whitelist = build_update_set_whitelist(update_set_text)
    unknown_seen = False
    for cand in candidates:
        # 1. Update Set whitelist (KD3: primary; what is in here is real AND the subject of the article)
        if cand.name.casefold() in whitelist:
            result.verdicts.append(NameVerdict(
                name=cand.name, status="exists", confidence=1.0,
                evidence="update_set whitelist", layer="update_set"))
            continue
        # 2. Per-name spot-check (cached)
        verdict = spot_checker.check(cand.name, cand.kind)
        if verdict.status == "unknown":
            unknown_seen = True
            result.verdicts.append(verdict)
            continue
        # 3. Ambiguous case (deterministically not_exists) → calibrated layer (US3)
        if verdict.status == "not_exists" and decision_client is not None:
            calibrated = _calibrated_decision(
                cand.name, story_context or article_html,
                client=decision_client, model=decision_model,
                threshold=confidence_threshold,
            )
            if calibrated is not None:
                result.verdicts.append(calibrated)
                continue
        result.verdicts.append(verdict)

    # FR-002: if not a single candidate got a decision (all unknown), the whole
    # check is skipped with a warning — with a partial result the successful
    # verdicts live and the failed ones are logged as "unknown".
    if result.verdicts and all(v.status == "unknown" for v in result.verdicts):
        result.skipped = True
        result.warning = "the instance verification is unreachable — fail-open (FR-002)"
        logger.warning(result.warning)
    elif unknown_seen:
        result.warning = "partial instance verification: some types are unreachable"
        logger.warning(result.warning)
    return result
