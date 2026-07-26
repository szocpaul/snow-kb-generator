# Spec 004 — Hallucination-Free KB Generation: mi változott?

**Scope:** `bacdce8..HEAD` (spec 004 commitok) · **Lens:** control-flow
**Viselkedést hordozó fájlok:** `eval/metric.py`, `src/snow_kb/pipeline.py` (+ `data/examples/gold_dataset.md` adattisztítás, tesztek)

A változás két védelmi vonalat épít a hallucinált KB-hivatkozások (pl. fiktív `KB0012345`) ellen:
(1) a `rich_metric` új **hallucination axis**-a bünteti a GEPA optimalizáció alatt az ismeretlen KB cikkszámokat,
(2) a pipeline-ba beépült **`strip_hallucinated_references()` guardrail** push *előtt* eltávolít minden olyan KB hivatkozást, ami nem szerepel a forrás Story szövegében. Emellett a gold dataset fiktív cikkszámai `KBXXXXXXX` placeholder-re cserélődtek.

## Before (régi viselkedés)

```mermaid
flowchart TD
  S["Story fetch + story_text"]:::same --> G["StoryToKBArticle program (LM)"]:::same
  G --> A["article = pred.article"]:::same
  A --> P{"push?"}:::same
  P -->|igen| SN["ServiceNow push (hallucinációval együtt)"]:::same
  P -->|nem| R["return article"]:::same

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

## After (új viselkedés)

```mermaid
flowchart TD
  S["Story fetch + story_text"]:::same --> G["StoryToKBArticle program (LM)"]:::same
  G --> A["article = pred.article"]:::same
  A --> GU["strip_hallucinated_references(article.html, story_text)"]:::same
  GU --> GUQ{"ismeretlen KB\\d{6,} a HTML-ben?"}:::same
  GUQ -->|igen| STRIP["<li> törlése / KBXXXXXXX csere + warning log"]:::same
  GUQ -->|nem| CLEAN["HTML változatlan"]:::same
  STRIP --> P{"push?"}:::same
  CLEAN --> P
  P -->|igen| SN["ServiceNow push (csak tiszta HTML)"]:::same
  P -->|nem| R["return article"]:::same

  subgraph Metric["rich_metric (GEPA/eval)"]
    M1["structure_match (0.3)"]:::same
    M2["content_accuracy (0.3)"]:::same
    M3["template_adherence (0.2)"]:::same
    M4["hallucination axis (0.2): KB-refek vs story_text"]:::same
    M1 --> MS["score + feedback (Hallucinated reference: KB...)"]:::same
    M2 --> MS
    M3 --> MS
    M4 --> MS
  end

  classDef same fill:#f6f8fa,stroke:#8c959f,color:#1f2328
```

## What changed (merged diff view)

A zöld az új, a piros a megszűnt, a sárga a módosult elem; a szürke érintetlen. A szaggatott piros élek a régi, már nem létező útvonalak.

```mermaid
flowchart TD
  S["Story fetch + story_text"]:::same --> G["StoryToKBArticle program (LM)"]:::same
  G --> A["article = pred.article"]:::same
  A -.->|"régi út: guardrail nélkül"| P{"push?"}:::same
  A -->|"új út: guardrail"| GU["strip_hallucinated_references()"]:::added
  GU --> GUQ{"ismeretlen KB-ref a HTML-ben?"}:::added
  GUQ -->|igen| STRIP["strip + placeholder csere + warning"]:::added
  GUQ -->|nem| CLEAN["HTML változatlan"]:::added
  STRIP --> P
  CLEAN --> P
  P -->|igen| SN["ServiceNow push"]:::changed
  P -->|nem| R["return article"]:::same

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
    FIC["KB0012345-KB0012349 (fiktív)"]:::removed
    PH["KBXXXXXXX placeholder"]:::added
  end

  classDef added   fill:#d4f8d4,stroke:#2ea043,color:#1f2328
  classDef removed fill:#ffd7d5,stroke:#cf222e,color:#1f2328
  classDef changed fill:#fff5cc,stroke:#bf8700,color:#1f2328
  classDef same    fill:#f6f8fa,stroke:#8c959f,color:#1f2328
  linkStyle 2 stroke:#cf222e,stroke-dasharray:5
  linkStyle 3 stroke:#2ea043
```

**Élszámozás (merged view):** 0: S→G, 1: G→A, 2: A⇢P (törölt), 3: A→GU (új), 4: GU→GUQ, 5: GUQ→STRIP, 6: GUQ→CLEAN, 7: STRIP→P, 8: CLEAN→P, 9: P→SN, 10: P→R.

## Notes

- **Módosult, nem új:** a `ServiceNow push` csomópont ugyanaz a kódút, de most már kizárólag guardrailen átment HTML-t kap — ezért sárga. A metric `score + feedback` összeállítása új feedback-ágat kapott ("Hallucinated reference(s): ...").
- **Súlyváltozás:** a metric tengelyek 0.4/0.4/0.2 → 0.3/0.3/0.2 (+0.2 hallucination) — ez szándékos trade-off: a nem-hallucinált output alapból kap 0.2-t (ld. `test_mismatch_returns_low_score` küszöb igazítása).
- **Kihagyva a diagramból:** `eval/gepa_optimize.py` CLI (`python -m eval.gepa_optimize`), a tesztek (8 új), és a szerver startup betöltés — ezek a spec 003-ban estek át a fő változáson; itt csak a hallucináció-specifikus viselkedés szerepel.
- **Eredmény:** baseline 0.386 → optimized 0.962 (tiszta adaton újrafuttatott GEPA), valset 0/2 hallucináció, éles cikk ServiceNow API-val verifikálva tisztán.
