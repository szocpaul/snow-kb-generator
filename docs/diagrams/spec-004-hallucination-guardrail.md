# Spec 004 — Hallucination-Free KB Generation: what changed?

**Scope:** `bacdce8..HEAD` (spec 004 commits) · **Lens:** control-flow
**Behaviour-carrying files:** `eval/metric.py`, `src/snow_kb/pipeline.py` (+ `data/examples/gold_dataset.md` data cleanup, tests)

The change builds two lines of defence against hallucinated KB references (e.g. fictional `KB0012345`):
(1) the new **hallucination axis** of the `rich_metric` penalises unknown KB article numbers during GEPA optimisation,
(2) the **`strip_hallucinated_references()` guardrail** built into the pipeline removes every KB reference that does not appear in the source Story text *before* the push. In addition, the fictional article numbers of the gold dataset were replaced with a `KBXXXXXXX` placeholder.

## Before (old behaviour)

```mermaid
flowchart TD
  S["Story fetch + story_text"]:::same --> G["StoryToKBArticle program (LM)"]:::same
  G --> A["article = pred.article"]:::same
  A --> P{"push?"}:::same
  P -->|yes| SN["ServiceNow push (with hallucinations)"]:::same
  P -->|no| R["return article"]:::same

  subgraph Metric["rich_metric (GEPA/eval)"]
    M1["structure_match (0.4)"]:::same
    M2["content_accuracy (0.4)"]:::same
    M3["template_adherence (0.2)"]:::same
    M1 --> MS["score + feedback"]:::same
    M2 --> MS
    M3 --> MS
  end

  classDef same fill:#f6f8fa,stroke:#8c959f,color:#1f2328
```

## After (new behaviour)

```mermaid
flowchart TD
  S["Story fetch + story_text"]:::same --> G["StoryToKBArticle program (LM)"]:::same
  G --> A["article = pred.article"]:::same
  A --> GU["strip_hallucinated_references(article.html, story_text)"]:::same
  GU --> GUQ{"unknown KB\\d{6,} in the HTML?"}:::same
  GUQ -->|yes| STRIP["delete <li> / replace with KBXXXXXXX + warning log"]:::same
  GUQ -->|no| CLEAN["HTML unchanged"]:::same
  STRIP --> P{"push?"}:::same
  CLEAN --> P
  P -->|yes| SN["ServiceNow push (clean HTML only)"]:::same
  P -->|no| R["return article"]:::same

  subgraph Metric["rich_metric (GEPA/eval)"]
    M1["structure_match (0.3)"]:::same
    M2["content_accuracy (0.3)"]:::same
    M3["template_adherence (0.2)"]:::same
    M4["hallucination axis (0.2): KB refs vs story_text"]:::same
    M1 --> MS["score + feedback (Hallucinated reference: KB...)"]:::same
    M2 --> MS
    M3 --> MS
    M4 --> MS
  end

  classDef same fill:#f6f8fa,stroke:#8c959f,color:#1f2328
```

## What changed (merged diff view)

Green is new, red is removed, yellow is modified; grey is untouched. The dashed red edges are the old, no longer existing paths.

```mermaid
flowchart TD
  S["Story fetch + story_text"]:::same --> G["StoryToKBArticle program (LM)"]:::same
  G --> A["article = pred.article"]:::same
  A -.->|"old path: without guardrail"| P{"push?"}:::same
  A -->|"new path: with guardrail"| GU["strip_hallucinated_references()"]:::added
  GU --> GUQ{"unknown KB ref in the HTML?"}:::added
  GUQ -->|yes| STRIP["strip + placeholder replacement + warning"]:::added
  GUQ -->|no| CLEAN["HTML unchanged"]:::added
  STRIP --> P
  CLEAN --> P
  P -->|yes| SN["ServiceNow push"]:::changed
  P -->|no| R["return article"]:::same

  subgraph Metric["rich_metric (GEPA/eval)"]
    M1["structure_match: 0.4 → 0.3"]:::changed
    M2["content_accuracy: 0.4 → 0.3"]:::changed
    M3["template_adherence (0.2)"]:::same
    M4["hallucination axis (0.2)"]:::added
    M1 --> MS["score + feedback"]:::changed
    M2 --> MS
    M3 --> MS
    M4 --> MS
  end

  subgraph Data["gold_dataset.md"]
    FIC["KB0012345-KB0012349 (fictional)"]:::removed
    PH["KBXXXXXXX placeholder"]:::added
  end

  classDef added   fill:#d4f8d4,stroke:#2ea043,color:#1f2328
  classDef removed fill:#ffd7d5,stroke:#cf222e,color:#1f2328
  classDef changed fill:#fff5cc,stroke:#bf8700,color:#1f2328
  classDef same    fill:#f6f8fa,stroke:#8c959f,color:#1f2328
  linkStyle 2 stroke:#cf222e,stroke-dasharray:5
  linkStyle 3 stroke:#2ea043
```

**Edge numbering (merged view):** 0: S→G, 1: G→A, 2: A⇢P (deleted), 3: A→GU (new), 4: GU→GUQ, 5: GUQ→STRIP, 6: GUQ→CLEAN, 7: STRIP→P, 8: CLEAN→P, 9: P→SN, 10: P→R.

## Notes

- **Modified, not new:** the `ServiceNow push` node is the same code path, but it now only receives HTML that passed the guardrail — hence yellow. The composition of the metric's `score + feedback` got a new feedback branch ("Hallucinated reference(s): ...").
- **Weight change:** the metric axes go 0.4/0.4/0.2 → 0.3/0.3/0.2 (+0.2 hallucination) — this is an intentional trade-off: non-hallucinated output gets 0.2 by default (see the threshold adjustment of `test_mismatch_returns_low_score`).
- **Left out of the diagram:** the `eval/gepa_optimize.py` CLI (`python -m eval.gepa_optimize`), the tests (8 new ones), and the server startup load — these fell into the main change in spec 003; here only the hallucination-specific behaviour is shown.
- **Result:** baseline 0.386 → optimized 0.962 (GEPA re-run on clean data), valset 0/2 hallucinations, the production article verified via the ServiceNow API to be clean.
