"""eval/context_labeled.py — spec 016 T010: címkézett kontextus-minta építése.

Min. 20 darab: releváns / zaj / határeset — a gold példák darabolásából,
gépi előcímkézéssel + AGENTI review-val (a „kézi" címke a runner átnézése;
minden darab címkéje indoklással, `label_note` mező).

    python -m eval.context_labeled build   # jelöltek + előcímkék → stdout-riport
                                           # és a címkézett fájl (re)generálása

Kimenet: data/examples/context_labeled_016.json (commitolva)

A címkék szemantikája (a T011 kalibráció ehhez méri a küszöböt):
  - "relevant":   a darabnak BE KELL kerülnie (show) — elrejtése recall-hiba
  - "noise":      a darab nyugodtan elrejthető (hide) — mutatása csak költség
  - "borderline": summarize-jelölt — az összefoglaló megőrzi a lényeget

FONTOS: a story_core darabok (FR-004) NEM címkézettek — rájuk a policy nem
futtat Score-döntést, a kalibráció tárgyán kívül esnek.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.context_baseline import GENERATIONS_PATH as BASELINE_GENS_PATH
from snow_kb.context_selection import split_context_into_pieces

LABELED_PATH = Path("data/examples/context_labeled_016.json")

# Agenti review-s címkék (T010 „kézi" átnézés). Kulcs: (example_id, piece_id).
# A build ELLENŐRZI, hogy minden jelölt darabra van review-címke — a gépi
# előcímke önmagában SOHA nem végleges.
REVIEWED_LABELS: dict[tuple[str, str], tuple[str, str]] = {
    ("gold-1", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-1", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-1", "story:comments"): ("borderline", "QA-verifikáció az u_jira_key mappingről — egy mondatba sűríthető"),
    ("gold-1", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-1", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-1", "story:work_notes"): ("borderline", "dev-napló (endpoint, Basic Auth) — a lényeg a tech spec-ben is megvan, összefoglalható"),
    ("gold-2", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-2", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-2", "story:comments"): ("borderline", "QA payload-verifikáció — sűríthető"),
    ("gold-2", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-2", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-2", "story:work_notes"): ("borderline", "JiraIntegrationUtils említés, de a részletek a tech spec-ben — összefoglalható"),
    ("gold-3", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-3", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-3", "story:comments"): ("borderline", "QA-teszt (50 mock user) — sűríthető"),
    ("gold-3", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-3", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-3", "story:work_notes"): ("borderline", "LDAP_Retry_Authenticator dev-részletek — a komponensnév a tech spec-ben is megvan"),
    ("gold-4", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-4", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-4", "story:comments"): ("borderline", "Finance-validáció — egy mondat"),
    ("gold-4", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-4", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-4", "story:work_notes"): ("borderline", "SAP plugin-telepítés menete — háttér, összefoglalható"),
    ("gold-5", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-5", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-5", "story:comments"): ("borderline", "edge-case verifikáció (duplikáció, missing group) — sűríthető"),
    ("gold-5", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-5", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-5", "story:work_notes"): ("borderline", "SnowKbGenerator implementációs napló — a rekord maga az update set-ben benne van"),
    ("gold-5", "update_set:0:sys_script_include:SnowKbGenerator"): ("relevant", "a Script Include, ami a változást hordozza — a cikk fő forrása"),
    ("gold-5", "update_set:1:sys_ui_action:createKbArticle"): ("relevant", "a UI Action rekord — a cikk hivatkozik rá"),
    ("gold-6", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-6", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-6", "story:comments"): ("noise", "tiszta QA-adminisztráció (staging/regression OK), tartalom nélkül"),
    ("gold-6", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-6", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-6", "story:work_notes"): ("borderline", "Business Rule review-napló — a BR neve a tech spec-ben is megvan"),
    ("gold-7", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-7", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-7", "story:comments"): ("borderline", "log-áttekintés az ALDIIntegrationFrameworkUtil-lel — komponensnév, sűríthető"),
    ("gold-7", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-7", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-7", "story:work_notes"): ("borderline", "ALDISolManChangeInterface mapping-napló — a részletek a tech spec-ben"),
    ("gold-8", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-8", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-8", "story:comments"): ("noise", "tiszta jóváhagyási adminisztráció"),
    ("gold-8", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-8", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-8", "story:work_notes"): ("noise", "egyetlen boilerplate mondat (completed and verified), nulla tartalom"),
    ("gold-9", "story:assigned_to"): ("noise", "személy-meta, nem tartalom"),
    ("gold-9", "story:assignment_group"): ("noise", "csapat-meta, nem tartalom"),
    ("gold-9", "story:comments"): ("relevant", "konkrét üzemeltetési tény: 100 calls/min throttling limit + retry-viselkedés — ez a tech spec-ben NINCS benne"),
    ("gold-9", "story:number"): ("noise", "story-azonosító, a cikkíráshoz nem kell"),
    ("gold-9", "story:state"): ("noise", "workflow-állapot, adminisztratív meta"),
    ("gold-9", "story:work_notes"): ("borderline", "API_PROJECT_MAINTAIN / ALDIS4ProjectInterface napló — a nevek a tech spec-ben is megvannak"),
}

def build_candidates() -> list[dict]:
    """Az összes scoreable darab a gold példákból (story_core kihagyva, FR-004)."""
    gens = json.loads(BASELINE_GENS_PATH.read_text(encoding="utf-8"))["examples"]
    candidates = []
    for ex in gens:
        pieces = split_context_into_pieces(
            story_text=ex["story_text"],
            update_set_payloads=ex["update_set_payloads"],
            related_articles_context="",
        )
        for p in pieces:
            if p.source_type == "story_core":
                continue
            candidates.append({
                "example_id": ex["id"],
                "piece_id": p.piece_id,
                "source_type": p.source_type,
                "label_text": p.label,
                "text": p.text,
            })
    return candidates


def cmd_build() -> None:
    candidates = build_candidates()
    labeled = []
    missing_review = []
    for c in candidates:
        key = (c["example_id"], c["piece_id"])
        if key in REVIEWED_LABELS:
            label, note = REVIEWED_LABELS[key]
            labeled.append({**c, "label": label, "label_note": note})
        else:
            missing_review.append(key)

    n_rel = sum(1 for r in labeled if r["label"] == "relevant")
    n_noise = sum(1 for r in labeled if r["label"] == "noise")
    n_bord = sum(1 for r in labeled if r["label"] == "borderline")
    print(f"jelölt darabok: {len(candidates)}; review-zott: {len(labeled)} "
          f"(relevant={n_rel}, noise={n_noise}, borderline={n_bord})")
    if missing_review:
        print(f"review nélkül (NEM kerül a mintába): {len(missing_review)}")
        for key in missing_review:
            print(f"  - {key[0]} {key[1]}")

    doc = {
        "spec": "016-context-selection / T010 címkézett kontextus-minta",
        "label_semantics": {
            "relevant": "show kell — elrejtése recall-hiba",
            "noise": "hide OK — mutatása csak költség",
            "borderline": "summarize-jelölt",
        },
        "review": "agenti kézi átnézés (REVIEWED_LABELS, per-darab indoklással)",
        "examples": labeled,
    }
    LABELED_PATH.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Címkézett minta: {LABELED_PATH} ({len(labeled)} darab)")
    if len(labeled) < 20:
        print("HIBA: kevesebb mint 20 címkézett darab (a 013-as mintaméret-tanulság)")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        cmd_build()
    else:
        print(__doc__)
        sys.exit(2)
