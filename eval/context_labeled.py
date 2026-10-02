"""eval/context_labeled.py — spec 016 T010: building the labelled context sample.

At least 20 pieces: relevant / noise / borderline — from the chunking of the gold examples,
with a machine pre-labeling + a HUMAN review (the "manual" label is the review of the runner;
every piece label has a justification, the `label_note` field).

    python -m eval.context_labeled build   # the candidates + the pre-labels → stdout report
                                           # and the (re)generation of the labelled file

Output: data/examples/context_labeled_016.json (committed)

The semantics of the labels (the T011 calibration measures the threshold for this):
  - "relevant":   the piece MUST be included (show) — hiding it is a recall error
  - "noise":      the piece can be hidden safely (hide) — showing it is only cost
  - "borderline": a summarize candidate — the summary preserves the essence

IMPORTANT: the story_core pieces (FR-004) are NOT labelled — the policy does not
run a Score decision on them, they are outside the scope of the calibration.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.context_baseline import GENERATIONS_PATH as BASELINE_GENS_PATH
from snow_kb.context_selection import split_context_into_pieces

LABELED_PATH = Path("data/examples/context_labeled_016.json")

# The human review labels (the T010 "manual" review). Key: (example_id, piece_id).
# The build CHECKS that every candidate piece has a review label — the machine
# pre-label alone is NEVER final.
REVIEWED_LABELS: dict[tuple[str, str], tuple[str, str]] = {
    ("gold-1", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-1", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-1", "story:comments"): ("borderline", "QA verification of the u_jira_key mapping — compressible into one sentence"),
    ("gold-1", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-1", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-1", "story:work_notes"): ("borderline", "dev log (endpoint, Basic Auth) — the essence is also in the tech spec, compressible"),
    ("gold-2", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-2", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-2", "story:comments"): ("borderline", "QA payload verification — compressible"),
    ("gold-2", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-2", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-2", "story:work_notes"): ("borderline", "a mention of JiraIntegrationUtils, but the details are in the tech spec — compressible"),
    ("gold-3", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-3", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-3", "story:comments"): ("borderline", "QA test (50 mock users) — compressible"),
    ("gold-3", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-3", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-3", "story:work_notes"): ("borderline", "LDAP_Retry_Authenticator dev details — the component name is also in the tech spec"),
    ("gold-4", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-4", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-4", "story:comments"): ("borderline", "finance validation — one sentence"),
    ("gold-4", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-4", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-4", "story:work_notes"): ("borderline", "the SAP plugin installation procedure — background, compressible"),
    ("gold-5", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-5", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-5", "story:comments"): ("borderline", "edge case verification (duplication, missing group) — compressible"),
    ("gold-5", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-5", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-5", "story:work_notes"): ("borderline", "SnowKbGenerator implementation log — the record itself is in the update set"),
    ("gold-5", "update_set:0:sys_script_include:SnowKbGenerator"): ("relevant", "the Script Include that carries the change — the main source of the article"),
    ("gold-5", "update_set:1:sys_ui_action:createKbArticle"): ("relevant", "the UI Action record — the article refers to it"),
    ("gold-6", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-6", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-6", "story:comments"): ("noise", "pure QA administration (staging/regression OK), without content"),
    ("gold-6", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-6", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-6", "story:work_notes"): ("borderline", "Business Rule review log — the BR name is also in the tech spec"),
    ("gold-7", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-7", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-7", "story:comments"): ("borderline", "a log review with IntegrationFrameworkUtil — a component name, compressible"),
    ("gold-7", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-7", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-7", "story:work_notes"): ("borderline", "ChangeSyncInterface mapping log — the details are in the tech spec"),
    ("gold-8", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-8", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-8", "story:comments"): ("noise", "pure approval administration"),
    ("gold-8", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-8", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-8", "story:work_notes"): ("noise", "a single boilerplate sentence (completed and verified), zero content"),
    ("gold-9", "story:assigned_to"): ("noise", "person meta, not content"),
    ("gold-9", "story:assignment_group"): ("noise", "team metadata, not content"),
    ("gold-9", "story:comments"): ("relevant", "a concrete operational fact: the 100 calls/min throttling limit + the retry behaviour — this is NOT in the tech spec"),
    ("gold-9", "story:number"): ("noise", "story identifier, not needed for the article"),
    ("gold-9", "story:state"): ("noise", "workflow state, administrative meta"),
    ("gold-9", "story:work_notes"): ("borderline", "API_PROJECT_MAINTAIN / S4ProjectInterface log — the names are in the tech spec as well"),
}

def build_candidates() -> list[dict]:
    """All the scoreable pieces from the gold examples (story_core excluded, FR-004)."""
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
    print(f"candidate pieces: {len(candidates)}; reviewed: {len(labeled)} "
          f"(relevant={n_rel}, noise={n_noise}, borderline={n_bord})")
    if missing_review:
        print(f"without a review (does NOT enter the sample): {len(missing_review)}")
        for key in missing_review:
            print(f"  - {key[0]} {key[1]}")

    doc = {
        "spec": "016-context-selection / T010 labelled context sample",
        "label_semantics": {
            "relevant": "show is needed — hiding it is a recall error",
            "noise": "hide is OK — showing it is only cost",
            "borderline": "a summarize candidate",
        },
        "review": "the human manual review (REVIEWED_LABELS, with a justification per piece)",
        "examples": labeled,
    }
    LABELED_PATH.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Labelled sample: {LABELED_PATH} ({len(labeled)} pieces)")
    if len(labeled) < 20:
        print("ERROR: fewer than 20 labelled pieces (the 013 sample size lesson)")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        cmd_build()
    else:
        print(__doc__)
        sys.exit(2)
