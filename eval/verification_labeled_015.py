"""eval/verification_labeled_015.py — spec 015 T005: the labelled sample from the
PDI-native fixture (US1).

From the dumped (and in the T003 MANUAL GATE approved by a human) set of names it
derives examples MACHINALLY:
  - real:        the exact form of the component name     → label "exists"
  - spelling variant: a machine variant (hyphen/lowercase forms) → label "variant" (+variant_of)
  - fabricated:   a plausible looking but non-existent name → label "fabricated"
  - type mismatch: a real name interpreted in a DIFFERENT type of table → label "exists"
                  (the NAME exists; it is the test of the 3rd mechanism — see the plan)

MINIMUM (spec prohibition): if the approved set of core names is < 8, the script
STOPS with exit 2 — the sample must NOT be diluted with correlated variants.

The output is merged with the existing 24 examples (the dev-derived "exists" labels
are excluded — FR-002: the "exists" labels of the 014 sample were PDI-verified, the
dev names like JiraInboundUtils are "missing_real", those are not-exists labels)
→ at least 30 examples in total, data/examples/verification_labeled_015.json.

Run:
  python -m eval.verification_labeled_015 build [--approved <json>]
    --approved: optional JSON (the output of the T003 review): {"approved_names": [...]}
                without it the component list of the dump is the source.
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
MIN_CORE_NAMES = 8  # spec prohibition: fewer core names → STOP

# The fabricated names: plausible looking but NOT existing (the hallucination class).
# Deliberately NOT the correlated variants of the component names (the spec prohibition).
_FABRICATED = [
    {"name": "WebhookRetryPolicyManager", "kind": "camelcase",
     "note": "a fabricated Script Include-like name — it does not exist on the PDI"},
    {"name": "KbDraftAuditInterceptor", "kind": "camelcase",
     "note": "a fabricated Script Include-like name — it does not exist on the PDI"},
    {"name": "snowkb.generator.retry.interval", "kind": "dotted",
     "note": "a fabricated property-like name — it does not exist on the PDI"},
    {"name": "Validate KB draft before push", "kind": "quoted",
     "note": "a fabricated Business Rule-like name — it does not exist on the PDI"},
]


def _mention_html(name: str, kind: str) -> str:
    """The appearance of the candidate in the article (per the 011 pattern — the measure uses this too)."""
    if kind == "quoted":
        return f"<h2>Solution</h2><p>The '{name}' component is part of the solution.</p>"
    return f"<h2>Solution</h2><p>The {name} component is part of the solution.</p>"


def _extractable(name: str, kind: str) -> bool:
    """Whether the candidate extractor of the gate (the conservative 011 regexes) sees this surface form."""
    from snow_kb.verification import extract_component_candidates

    return any(c.name == name for c in extract_component_candidates(_mention_html(name, kind)))


def _space_variant(name: str) -> str:
    """CamelCase → the form with spaces ('PrototypeServer' → 'Prototype Server')."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)


def _variants_of(name: str, kind: str) -> list[tuple[str, str]]:
    """The machine spelling variants (to test the 2nd mechanism) — (surface form, kind).

    IMPORTANT: only the surface forms VISIBLE to the gate extractor (the
    conservative 011 regexes: quoted capitalised / dotted lowercase / CamelCase).
    The build filters out and reports the variants that cannot be extracted.
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
        print(f"Core name set: the full dump ({len(core)} names) — the T003 review "
              "output should be given as --approved, if it was narrowed.")

    # MINIMUM — according to the spec prohibition we do NOT dilute
    if len(core) < MIN_CORE_NAMES:
        print(f"STOP: the approved core name set {len(core)} names < {MIN_CORE_NAMES} — "
              "the sample must NOT be diluted with correlated variants. Report it to the human.")
        return 2

    story_ctx = dump["story"]["short_description"]
    examples: list[dict] = []

    _KIND_MAP = {"script_include": "camelcase", "business_rule": "quoted",
                 "system_property": "dotted", "field": "dotted"}

    # 0. The extractability filter: the candidate extractor of the gate (the conservative
    #    011 regexes) sees only the quoted capitalised / pure dotted / CamelCase forms.
    #    What cannot be extracted is UNREACHABLE for the gate — not
    #    a measurable example (the name approved by T003 is real nevertheless).
    extractable_core = []
    for c in core:
        kind = _KIND_MAP[c["kind"]]
        if _extractable(c["name"], kind):
            extractable_core.append((c, kind))
        else:
            print(f"  SKIPPED (the gate extractor does not see it): {c['name']} [{c['kind']}]")
    # The minimum also applies to the EXTRACTABLE core name set
    if len(extractable_core) < MIN_CORE_NAMES:
        print(f"STOP: the extractable core name set {len(extractable_core)} names "
              f"< {MIN_CORE_NAMES} — the sample must NOT be diluted. Report it to the human.")
        return 2

    # 1. The real names
    for c, kind in extractable_core:
        examples.append({
            "name": c["name"], "kind": kind, "label": "exists",
            "note": f"fixture (STRY0010004 update set): a real {c['xml_type']} on the PDI",
            "source": "fixture015",
        })
    # 2. The spelling variants (at most 2 EXTRACTABLE machine variants per component)
    for c, kind in extractable_core:
        for v, vkind in [vk for vk in _variants_of(c["name"], kind)
                         if _extractable(vk[0], vk[1])][:2]:
            examples.append({
                "name": v, "kind": vkind, "label": "variant", "variant_of": c["name"],
                "note": f"machine spelling variant: {c['name']}",
                "source": "fixture015",
            })
    # 3. The fabricated names
    for f in _FABRICATED:
        examples.append({**f, "label": "fabricated", "source": "fixture015"})
    # 4. The type mismatch: a real Script Include name referred to as a Business Rule
    #    (the quoted surface form — the NAME exists, the type reference is wrong).
    for c, kind in [ck for ck in extractable_core if ck[1] == "camelcase"][:2]:
        examples.append({
            "name": c["name"], "kind": "quoted", "label": "exists",
            "note": f"type mismatch: a real Script Include ('{c['name']}') "
                    "referred to as a Business Rule — the name exists",
            "source": "fixture015",
        })

    # 5. Self-check: EVERY generated example is extractable from its own mention html
    not_extractable = [e["name"] for e in examples
                       if not _extractable(e["name"], e["kind"])]
    if not_extractable:
        print(f"INTERNAL ERROR: a non-extractable example got into the sample: {not_extractable}")
        return 2

    # 5. Merging with the existing 24 examples (FR-002: the dev-derived "exists"
    #    labels are excluded — that is what does NOT support the instance fact. The
    #    instance fact here is the spot-check CACHE (the result fetched by the 014
    #    live check): only the labels empirically "exists" in the cache may remain.
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
        print(f"FR-002: excluded (the instance fact does NOT support it): {excluded}")

    merged = old_examples + examples
    out = {
        "spec": "015-asymmetric-verification-gate",
        "task": "T005",
        "fixture_story": dump["story"]["number"],
        "labels": old["labels"],
        "decision_mapping": old["decision_mapping"],
        "story_context": story_ctx,
        "examples": merged,
        "note": "The labels of the fixture examples come from the instance fact (from the captured update "
                "set content) and are derived mechanically; the sample is NOT diluted with "
                "correlated variants (the fabricated names are independent).",
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"Output: {OUT_PATH} — {len(old_examples)} old + {len(examples)} new = "
          f"{len(merged)} examples")
    if len(merged) < 30:
        print(f"WARNING: the merged sample {len(merged)} examples < 30 (the SC-002 minimum)!")
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
