"""eval/verification_labeled_015.py — spec 015 T005: címkézett minta a
PDI-natív fixture-ből (US1).

A dumpolt (és a T003 MANUÁLIS KAPU-ban az ember által jóváhagyott) név-halmazból
GÉPIESEN származtat példákat:
  - valós:        a komponensnév pontos alakja          → label "exists"
  - írásvariáns:  gépi variáns (kötőjel/kisbetű alakok) → label "variant" (+variant_of)
  - fabrikált:    valóságosnak tűnő, de nem létező név  → label "fabricated"
  - típus-eltérés: valós név, MÁS típusú táblában értelmezve → label "exists"
                  (a NÉV létezik; a 3-as mechanizmus tesztje — ld. plan)

MAGMINIMUM (spec tilalom): ha a jóváhagyott magnév-halmaz < 8 név, a script
ÁLL és exit 2 — a minta NEM hígítható korrelált variánsokkal.

A kimenet a meglévő 24 példával egyesül (az aldidev-eredetű "létezik" címkék
kizárva — FR-002: a 014-es minta "exists" címkéi PDI-ellenőrzöttek, a
JiraInboundUtils-féle aldidev-nevek "missing_real"-ek, azok nem létezik-címkék)
→ összesen ≥30 példa, data/examples/verification_labeled_015.json.

Futtatás:
  python -m eval.verification_labeled_015 build [--approved <json>]
    --approved: opcionális JSON (a T003 review kimenete): {"approved_names": [...]}
                nélküle a dump komponens-listája a mag.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DUMP_PATH = Path("artifacts/verification_fixture_components.json")
OLD_LABELED = Path("data/examples/verification_labeled.json")
OUT_PATH = Path("data/examples/verification_labeled_015.json")
MIN_CORE_NAMES = 8  # spec tilalom: ennél kevesebb magnév → ÁLLJ MEG

# Fabrikált nevek: valóságosnak tűnő, de NEM létező (a hallucináció-osztály).
# Szándékosan NEM a komponensnevek korrelált variánsai (a spec tilalma).
_FABRICATED = [
    {"name": "WebhookRetryPolicyManager", "kind": "camelcase",
     "note": "fabrikált Script Include-szerű név — nincs a PDI-n"},
    {"name": "KbDraftAuditInterceptor", "kind": "camelcase",
     "note": "fabrikált Script Include-szerű név — nincs a PDI-n"},
    {"name": "snowkb.generator.retry.interval", "kind": "dotted",
     "note": "fabrikált property-szerű név — nincs a PDI-n"},
    {"name": "Validate KB draft before push", "kind": "quoted",
     "note": "fabrikált Business Rule-szerű név — nincs a PDI-n"},
]


def _mention_html(name: str, kind: str) -> str:
    """A jelölt cikk-beli megjelenése (a 011-minta szerint — a measure is ezt használja)."""
    if kind == "quoted":
        return f"<h2>Megoldás</h2><p>A '{name}' komponens a megoldás része.</p>"
    return f"<h2>Megoldás</h2><p>A {name} komponens a megoldás része.</p>"


def _extractable(name: str, kind: str) -> bool:
    """A gate jelölt-kinyerője (011-es konzervatív regexek) látja-e ezt a felületi alakot."""
    from snow_kb.verification import extract_component_candidates

    return any(c.name == name for c in extract_component_candidates(_mention_html(name, kind)))


def _space_variant(name: str) -> str:
    """CamelCase → szóközös alak ('PrototypeServer' → 'Prototype Server')."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)


def _variants_of(name: str, kind: str) -> list[tuple[str, str]]:
    """Gépi írásvariánsok (a 2-es mechanizmus tesztelésére) — (felületi alak, kind).

    FONTOS: csak a gate-kinyerő által LÁTHATÓ felületi alakok (a 011-es
    konzervatív regexek: idézett nagybetűs / dotted kisbetűs / CamelCase).
    A kinyerhetetlen variánsokat a build kiszűri és jelenti.
    """
    out: list[tuple[str, str]] = []
    if kind == "camelcase":
        spaced = _space_variant(name)
        out.append((spaced, "quoted"))                    # 'Prototype Server'
        out.append((spaced.replace(" ", "-"), "quoted"))  # 'Prototype-Server'
    elif "." in name:
        out.append((name.upper(), "quoted"))              # 'GLIDE.LASTPLUGIN'
        out.append((name[:1].upper() + name[1:], "quoted"))  # 'Glide.lastplugin'
    else:  # quoted (Business Rule) core
        out.append((name.replace(" ", "-"), "quoted"))    # 'Change-Phase-Events-Before'
        words = name.split(" ")
        if len(words) > 1:
            out.append((" ".join(words[:-1] + [words[-1].lower()]), "quoted"))
    return [(v, k) for v, k in dict.fromkeys(out) if v != name]


def build(approved_path: str | None = None) -> int:
    if not DUMP_PATH.exists():
        print(f"Hianyzik a fixture-dump: {DUMP_PATH} — futtasd a fixture create-et.")
        return 2
    dump = json.loads(DUMP_PATH.read_text(encoding="utf-8"))
    components = dump["components"]

    if approved_path:
        approved = set(json.loads(Path(approved_path).read_text(
            encoding="utf-8"))["approved_names"])
        core = [c for c in components if c["name"] in approved]
        dropped = [c["name"] for c in components if c["name"] not in approved]
        print(f"T003-jovahagyott mag: {len(core)} nev (eldobva: {dropped})")
    else:
        core = components
        print(f"Magnév-halmaz: a teljes dump ({len(core)} nev) — a T003 review "
              "kimenete legyen --approved-kent megadva, ha szukitett.")

    # MAGMINIMUM — a spec tilalma szerint NEM hígítunk
    if len(core) < MIN_CORE_NAMES:
        print(f"MEGALLAS: a jovahagyott magnév-halmaz {len(core)} nev < {MIN_CORE_NAMES} — "
              "a minta NEM hígítható korrelált variánsokkal. Jelentsd az embernek.")
        return 2

    story_ctx = dump["story"]["short_description"]
    examples: list[dict] = []

    _KIND_MAP = {"script_include": "camelcase", "business_rule": "quoted",
                 "system_property": "dotted", "field": "dotted"}

    # 0. Kinyerhetőségi szűrő: a gate jelölt-kinyerője (011-es konzervatív
    #    regexek) csak az idézett nagybetűs / tiszta dotted / CamelCase alakokat
    #    látja. Ami nem nyerhető ki, az a gate számára ELÉRHETETLEN — nem
    #    mérhető példa (a T003 által jóváhagyott név attól még valós).
    extractable_core = []
    for c in core:
        kind = _KIND_MAP[c["kind"]]
        if _extractable(c["name"], kind):
            extractable_core.append((c, kind))
        else:
            print(f"  KIHAGYVA (a gate-kinyerő nem látja): {c['name']} [{c['kind']}]")
    # A magminimum a KINYERHETŐ magnév-halmazra is érvényes
    if len(extractable_core) < MIN_CORE_NAMES:
        print(f"MEGALLAS: a kinyerheto magnév-halmaz {len(extractable_core)} nev "
              f"< {MIN_CORE_NAMES} — a minta NEM hígítható. Jelentsd az embernek.")
        return 2

    # 1. valós nevek
    for c, kind in extractable_core:
        examples.append({
            "name": c["name"], "kind": kind, "label": "exists",
            "note": f"fixture (STRY0010004 update set): valós {c['xml_type']} a PDI-n",
            "source": "fixture015",
        })
    # 2. írásvariánsok (komponensenként max 2 KINYERHETŐ gépi variáns)
    for c, kind in extractable_core:
        for v, vkind in [vk for vk in _variants_of(c["name"], kind)
                         if _extractable(vk[0], vk[1])][:2]:
            examples.append({
                "name": v, "kind": vkind, "label": "variant", "variant_of": c["name"],
                "note": f"gépi írásvariáns: {c['name']}",
                "source": "fixture015",
            })
    # 3. fabrikált nevek
    for f in _FABRICATED:
        examples.append({**f, "label": "fabricated", "source": "fixture015"})
    # 4. típus-eltérés: valós Script Include-név Business Rule-KÉNT hivatkozva
    #    (idézett felületi alak — a NÉV létezik, a típus-hivatkozás téves).
    for c, kind in [ck for ck in extractable_core if ck[1] == "camelcase"][:2]:
        examples.append({
            "name": c["name"], "kind": "quoted", "label": "exists",
            "note": f"típus-eltérés: valós Script Include ('{c['name']}') "
                    "Business Rule-ként hivatkozva — a név létezik",
            "source": "fixture015",
        })

    # 5. önellenőrzés: MINDEN generált példa kinyerhető a saját mention-html-jéből
    not_extractable = [e["name"] for e in examples
                       if not _extractable(e["name"], e["kind"])]
    if not_extractable:
        print(f"BELSO HIBA: kinyerhetetlen pelda kerult a mintaba: {not_extractable}")
        return 2

    # 5. egyesítés a meglévő 24 példával (FR-002: az aldidev-eredetű "létezik"
    #    címkék kizárva — azaz ami NEM támasztja alá az instance-tény. Az
    #    instance-tény itt a spot-check CACHE (a 014-es élő ellenőrzés lekottázott
    #    eredménye): csak a cache-empírikusan "exists" címkék maradhatnak.
    cache_path = Path("artifacts/verification_spotcheck_cache.json")
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    old = json.loads(OLD_LABELED.read_text(encoding="utf-8"))
    old_examples = []
    excluded = []
    for e in old["examples"]:
        if e["label"] == "exists":
            entry = cache.get(e["name"].casefold(), {})
            if entry.get("status") != "exists":
                excluded.append(e["name"])
                continue
        e2 = dict(e)
        e2.setdefault("source", "spec014")
        old_examples.append(e2)
    if excluded:
        print(f"FR-002: kizárva (az instance-tény NEM támasztja alá): {excluded}")

    merged = old_examples + examples
    out = {
        "spec": "015-asymmetric-verification-gate",
        "task": "T005",
        "fixture_story": dump["story"]["number"],
        "labels": old["labels"],
        "decision_mapping": old["decision_mapping"],
        "story_context": story_ctx,
        "examples": merged,
        "note": "A fixture-példák címkéi az instance-tényből (a capture-ölt update "
                "set tartalmából) gépiesen származnak; a minta NEM hígított "
                "korrelált variánsokkal (a fabrikált nevek fuggetlenek).",
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"Kimenet: {OUT_PATH} — {len(old_examples)} régi + {len(examples)} új = "
          f"{len(merged)} példa")
    if len(merged) < 30:
        print(f"FIGYELEM: az egyesített minta {len(merged)} példa < 30 (SC-002 minimum)!")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build"])
    parser.add_argument("--approved", default=None)
    args = parser.parse_args()
    sys.exit(build(args.approved))


if __name__ == "__main__":
    main()
