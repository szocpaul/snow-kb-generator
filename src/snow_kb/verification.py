"""verification.py — komponensnév-hitelesítés az instance ellen (spec 014).

A generált KB-cikk nevesített komponensneveit a ServiceNow-írás ELŐTT
validálja az instance-metaadatok ellenében:

  1. Jelölt-kinyerés (011-minta: idézett nevek, CamelCase, dotted azonosítók;
     az általános terminusok a 011-whitelisttel kiesnek; FQDN-szerű dotted
     nevek — külső rendszer hostjai — szintén kiesnek: T004 baseline-tanulság).
  2. Determinisztikus mag (plan KD2/KD3):
     a. Update Set-whitelist (a story update setjének tartalma — elsődleges);
     b. ami nincs benne: per-név spot-check az instance metaadataiban
        (sys_db_object / sys_dictionary / sys_script / sys_script_include),
        JSON-cache-elve (a cache a recording része → a replay byte-identikus,
        SC-004).
  3. A homályos esetek (determinisztikusan "not_exists") a kalibrált réteghez
     kerülnek (TypeSafe Noul, pinnelt modell — FR-005): "ez a megnevezés valós
     komponensre utal-e?" (plan KD2, US3).

Fail-open kötelező (FR-002): bármilyen lekérdezési/SDK-hiba esetén a réteg
kihagyódik warninggal, a pipeline a meglévő úton fut tovább.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# A 011-es általános-terminus whitelist megosztott forrása az eval-metrika
# (a tests/test_style_guidance.py-minta szerint egy helyen él a lista).
from eval.metric import COMPONENT_NAME_WHITELIST

logger = logging.getLogger(__name__)

_WHITELIST_CF: set[str] = {w.casefold() for w in COMPONENT_NAME_WHITELIST}

# Publikus TLD-k: az ezekre végződő dotted nevek külső hostok/domainek
# (a T004 baseline tanulsága: aldi.com, interface.solman-stílusú false positive-ok).
_TLD_SUFFIXES = {
    "com", "net", "org", "io", "de", "hu", "eu", "at", "ch", "co", "ai", "dev",
    "local", "internal", "corp", "lan",
}

# A ServiceNow metaadat-táblák, amikben a spot-check keres (deploy/README.md).
_SPOTCHECK_TABLES = ("sys_db_object", "sys_script", "sys_script_include", "sys_dictionary")


# ---------------------------------------------------------------------------
# Adatmodell
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComponentCandidate:
    """A cikkből kinyert nevesített entitás + kinyerési mód (Key Entities)."""

    name: str
    kind: str  # "quoted" | "dotted" | "camelcase"


@dataclass(frozen=True)
class NameVerdict:
    """Egy komponensnév validálási döntése (Key Entities: Validálási döntés)."""

    name: str
    status: Literal["exists", "not_exists", "not_applicable", "unknown"]
    confidence: float          # determinisztikus réteg: 1.0
    evidence: str              # naplózott bizonyíték (tábla/mező, whitelist, stb.)
    layer: str                 # "update_set" | "spotcheck" | "calibrated"


@dataclass
class VerificationResult:
    """A verify_component_names kimenete."""

    verdicts: list[NameVerdict] = field(default_factory=list)
    skipped: bool = False      # True, ha fail-open miatt a vizsgálat kihagyódott
    warning: str = ""

    @property
    def not_existing_names(self) -> list[str]:
        return [v.name for v in self.verdicts if v.status == "not_exists"]


# ---------------------------------------------------------------------------
# Jelölt-kinyerés (011-minta, eval/metric.py regexeivel azonosan)
# ---------------------------------------------------------------------------

def extract_component_candidates(html: str) -> list[ComponentCandidate]:
    """Komponensnév-jelöltek kinyerése a 011-es mintával.

    A eval/metric.py _find_hallucinated_components reguláris kifejezéseivel
    AZONOS kinyerés; a különbség a szűrésben van: itt a story-igazolás helyett
    az instance-igazolás a következő lépés, ezért a whitelisten és a
    FQDN-szűrésen kívül minden jelölt továbbmegy.
    """
    text = re.sub(r"<[^>]+>", " ", html)  # tagek + attribútum-URL-ek eldobása
    text = re.sub(r"https?://\S+", " ", text)  # látható URL-ek
    text = re.sub(r"\b\S+@\S+\b", " ", text)  # email címek

    candidates: list[ComponentCandidate] = []

    def _add(name: str, kind: str) -> None:
        name = name.strip()
        if not name or name.casefold() in _WHITELIST_CF:
            return
        if any(c.name == name for c in candidates):
            return
        candidates.append(ComponentCandidate(name=name, kind=kind))

    for m in re.findall(r"'([A-Z][A-Za-z0-9 _.:/-]{2,50})'", text):  # idézett nevek
        _add(m, "quoted")
    for d in re.findall(r"\b([a-z]+[a-z0-9]*(?:\.[a-z0-9_]+)+)\b", text):  # dotted
        if not any(len(seg) >= 2 for seg in d.split(".")):  # 'e.g'/'i.e' kiesik
            continue
        if d.rsplit(".", 1)[-1].casefold() in _TLD_SUFFIXES:  # FQDN → külső host
            continue
        _add(d, "dotted")
    for m in re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", text):  # CamelCase
        _add(m, "camelcase")

    return candidates


# ---------------------------------------------------------------------------
# Update Set whitelist (KD3: elsődleges ground truth)
# ---------------------------------------------------------------------------

def build_update_set_whitelist(update_set_text: str) -> set[str]:
    """Komponensnevek (casefold) a get_update_set_changes kimenetéből.

    Két forrás: a formázott módosításlista sorai ("- [ACTION] Type: Name") és a
    nyers payload XML-ek name attribútumai.
    """
    whitelist: set[str] = set()
    if not update_set_text:
        return whitelist
    for m in re.findall(r"^\s*-\s*\[[^\]]+\]\s*[^:]+:\s*(.+)$", update_set_text, re.M):
        name = m.strip()
        if name and name != "ismeretlen":
            whitelist.add(name.casefold())
    for m in re.findall(r'\bname="([^"]+)"', update_set_text):
        whitelist.add(m.strip().casefold())
    return whitelist


# ---------------------------------------------------------------------------
# SpotChecker — per-név spot-check, cache-elve (KD3)
# ---------------------------------------------------------------------------

class SpotChecker:
    """Per-név létezik/nem létezik lekérdezés az instance metaadataiban.

    A cache (spotcheck_cache_path) a recording része: cache-only módban
    (session=None) a korábbi válaszok byte-identikusan replayelhetők (SC-004),
    cache-miss esetén a válasz "unknown" (fail-open — replay-módban NEM
    gyártunk új "nem létezik" döntést).
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
            except Exception as exc:  # noqa: BLE001 — sérült cache ne állítsa le
                logger.warning("Spot-check cache olvasási hiba (%s): %s — üres cache",
                               self.cache_path, exc)
                self._cache = {}

    # -- belső ------------------------------------------------------------

    def _probes(self, name: str, kind: str) -> list[tuple[str, str, str]]:
        """Lekérdezés-lista: (tábla, mező, érték) hármasok, kinyerési mód szerint."""
        probes: list[tuple[str, str, str]] = []
        if kind == "dotted":
            probes.append(("sys_db_object", "name", name))
            last = name.split(".")[-1]
            if last and last != name:
                probes.append(("sys_dictionary", "element", last))
        else:
            for table in ("sys_script_include", "sys_script", "sys_db_object"):
                probes.append((table, "name", name))
        return probes

    def _query(self, table: str, field_name: str, value: str) -> bool:
        """Egy Table API lekérdezés: True, ha van találat. Hiba → kivétel."""
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
        except Exception as exc:  # noqa: BLE001 — a cacheírás hibája ne döntse el
            logger.warning("Spot-check cache írási hiba (%s): %s", self.cache_path, exc)

    # -- nyilvános ----------------------------------------------------------

    def check(self, name: str, kind: str = "quoted") -> NameVerdict:
        """Egy név spot-checkje (cache-first).

        Returns:
            NameVerdict — status: exists / not_exists / unknown (hiba vagy
            cache-miss replay-módban; FR-002 fail-open).
        """
        key = name.casefold()
        if key in self._cache:
            entry = self._cache[key]
            return NameVerdict(name=name, status=entry["status"], confidence=1.0,
                               evidence=entry["evidence"], layer="spotcheck")
        if self.session is None:
            return NameVerdict(name=name, status="unknown", confidence=0.0,
                               evidence="cache-miss, replay-mód (nincs session)",
                               layer="spotcheck")
        try:
            for table, field_name, value in self._probes(name, kind):
                if self._query(table, field_name, value):
                    evidence = f"{table}.{field_name}={value}"
                    self._cache[key] = {"status": "exists", "evidence": evidence}
                    self._save_cache()
                    return NameVerdict(name=name, status="exists", confidence=1.0,
                                       evidence=evidence, layer="spotcheck")
            evidence = "nincs találat: " + ", ".join(t for t, _, _ in self._probes(name, kind))
            self._cache[key] = {"status": "not_exists", "evidence": evidence}
            self._save_cache()
            return NameVerdict(name=name, status="not_exists", confidence=1.0,
                               evidence=evidence, layer="spotcheck")
        except Exception as exc:  # noqa: BLE001 — szándékosan széles háló (FR-002)
            logger.warning("Spot-check hiba (%s): %s: %s — fail-open", name,
                           type(exc).__name__, exc)
            return NameVerdict(name=name, status="unknown", confidence=0.0,
                               evidence=f"{type(exc).__name__}: {exc}", layer="spotcheck")


# ---------------------------------------------------------------------------
# Kalibrált réteg (US3) — TypeSafe Noul, pinnelt modell (FR-005)
# ---------------------------------------------------------------------------

_REFERS_QUESTION = (
    "Osztályozd a megnevezést: (a) 'yes' — egy valós, az adott ServiceNow "
    "instance-en LÉTEZŐ komponensre (tábla, mező, Business Rule, Script "
    "Include stb.) utal, esetleg írásvariánssal vagy rövidítve; "
    "(b) 'external' — külső (NEM ServiceNow) rendszer objektuma (pl. SAP, "
    "SolMan, Jira szerver-oldali), általános szövegrészlet, állapot vagy "
    "hibaüzenet — ezeket a gate NEM validálja (spec Out of Scope); "
    "(c) 'no' — ServiceNow-komponensnek LÁTSZÓ, de fabrikált/nem létező név."
)

_REFERS_CRITERIA = {
    "yes": "a megnevezés egy valós ServiceNow-komponensre utal (írásvariáns is lehet)",
    "external": "külső rendszer objektuma, általános szöveg, állapot vagy hibaüzenet — nem validálandó",
    "no": "ServiceNow-komponensnek látszó, de fabrikált vagy nem létező név",
}

_REFERS_EPS = 1e-9  # a 013-as minta: '<' operátor + eps a float-határon


def _calibrated_decision(
    name: str,
    story_context: str,
    *,
    client: Any,
    model: str,
    threshold: float,
) -> NameVerdict | None:
    """Kalibrált döntés egy homályos jelöltről (US3).

    Returns:
        NameVerdict layer="calibrated", vagy None fail-open esetén (a hívó
        ilyenkor a determinisztikus út eredményét tartja meg).
    """
    from typesafe_sdk import Choice

    state = (
        f"Cikkrészlet-kontextus (a forrás-story és/vagy a cikk környezete):\n"
        f"{story_context[:4000]}\n\n"
        f"Vizsgált megnevezés: '{name}'"
    )
    questions = {"refers": Choice(instructions=_REFERS_QUESTION,
                                  criteria=dict(_REFERS_CRITERIA))}
    try:
        response = client.system_one(state=state, questions=questions, model=model)
        answer = response.answers["refers"]
        confidence = float(getattr(answer, "confidence", 0.0) or 0.0)
        choice = getattr(answer, "choice", None)
        # Küszöb-operátor: '<' (nem '<=') — a pontos határérték a biztonságos
        # irányba (jelzés) dől (spec Edge Cases; a 013-as minta).
        confident = not (confidence < threshold + _REFERS_EPS)
        if choice == "yes" and confident:
            return NameVerdict(name=name, status="exists", confidence=confidence,
                               evidence=f"kalibrált döntés: utalás (model={model})",
                               layer="calibrated")
        if choice == "external" and confident:
            # Külső rendszer objektuma / általános szöveg — a gate NEM
            # validálja (spec Out of Scope), nincs jelzés.
            return NameVerdict(name=name, status="not_applicable", confidence=confidence,
                               evidence=f"kalibrált döntés: nem SNOW-komponens "
                                        f"(model={model})",
                               layer="calibrated")
        return NameVerdict(name=name, status="not_exists", confidence=confidence,
                           evidence=f"kalibrált döntés: fabrikált/alacsony confidence "
                                    f"(model={model}, threshold={threshold})",
                           layer="calibrated")
    except Exception as exc:  # noqa: BLE001 — fail-open a determinisztikus útra
        logger.warning("Kalibrált döntés hiba (%s): %s: %s — fail-open",
                       name, type(exc).__name__, exc)
        return None


# ---------------------------------------------------------------------------
# Fő belépési pont
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
    """A cikk komponensneveinek validálása az instance ellen (FR-001).

    Args:
        article_html: a generált KB-cikk HTML-je.
        update_set_text: a get_update_set_changes kimenete (lehet üres).
        spot_checker: per-név spot-checker (None → a vizsgálat kihagyódik).
        story_context: a kalibrált réteg kontextusa (story_text / cikkrészlet).
        decision_client: system_one-kompatibilis client a kalibrált réteghez
            (None → csak a determinisztikus út fut).
        decision_model: pinnelt döntési modell (FR-005).
        confidence_threshold: a kalibrált kapu (SC-002 confirmatory: 0.7).

    Returns:
        VerificationResult — verdicts per jelölt; skipped=True fail-opennél.
    """
    result = VerificationResult()
    candidates = extract_component_candidates(article_html)
    if not candidates:
        return result
    if spot_checker is None:
        result.skipped = True
        result.warning = "nincs spot_checker — az instance-ellenőrzés kihagyva"
        logger.warning(result.warning)
        return result

    whitelist = build_update_set_whitelist(update_set_text)
    unknown_seen = False
    for cand in candidates:
        # 1. Update Set-whitelist (KD3: elsődleges; ami itt van, az valós ÉS a cikk tárgya)
        if cand.name.casefold() in whitelist:
            result.verdicts.append(NameVerdict(
                name=cand.name, status="exists", confidence=1.0,
                evidence="update_set whitelist", layer="update_set"))
            continue
        # 2. Per-név spot-check (cache-elve)
        verdict = spot_checker.check(cand.name, cand.kind)
        if verdict.status == "unknown":
            unknown_seen = True
            result.verdicts.append(verdict)
            continue
        # 3. Homályos eset (determinisztikusan not_exists) → kalibrált réteg (US3)
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

    # FR-002: ha EGYETLEN jelöltre sem sikerült döntés (mind unknown), a
    # vizsgálat egésze kihagyódik warninggal — részleges eredménynél a
    # sikeres verdict-ek élnek, a hibásak "unknown"-ként naplózódnak.
    if result.verdicts and all(v.status == "unknown" for v in result.verdicts):
        result.skipped = True
        result.warning = "az instance-ellenőrzés elérhetetlen — fail-open (FR-002)"
        logger.warning(result.warning)
    elif unknown_seen:
        result.warning = "részleges instance-ellenőrzés: egyes típusok elérhetetlenek"
        logger.warning(result.warning)
    return result
