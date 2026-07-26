# Implementation Plan: Hallucination-Free KB Article Generation

**Branch**: `004-no-hallucinated-references` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

## Technical Context

- **Language**: Python 3.12, DSPy 3.2.x, pytest
- **Affected modules**: `data/examples/gold_dataset.md`, `eval/metric.py`, `src/snow_kb/pipeline.py` (guardrail), `tests/`
- **No new dependencies** — regex-alapú detektálás a stdlib-ből.

## Architecture

```
Story text (source of truth)
      │
      ▼
StoryToKBArticle (GEPA-optimized) ──► generated HTML
      │                                   │
      │                          guardrail: strip_hallucinated_references()
      │                                   │  (KB\d{6,} minták összevetve a story_text-tel)
      │                                   ▼
      │                           clean HTML ──► ServiceNow push
      ▼
rich_metric: + hallucination axis (GEPA feedback)
```

## Key Decisions

1. **Placeholder formátum**: `KBXXXXXXX` — egyértelműen nem-valós, a regex detektáló külön kezeli.
2. **Detektálási minta**: `\bKB\d{6,}\b` — a ServiceNow KB számok 7 számjegyűek; ≥6 számjegy elfogadott határnak.
3. **Guardrail stratégia**: strip (eltávolítás) + warning log, NEM hiba — a cikk így is pusholható, a hallucináció nem.
4. **Metric súlyok**: az új hallucination axis a meglévő tengelyek mellé kerül (0.3 structure + 0.3 content + 0.2 template + 0.2 hallucination).

## Phases

1. **Phase 1 (Data)**: gold_dataset.md sanitization + dataset teszt bővítés.
2. **Phase 2 (Metric)**: hallucination axis a rich_metric-ben + tesztek.
3. **Phase 3 (Guardrail)**: `strip_hallucinated_references()` a pipeline-ban + tesztek.
4. **Phase 4 (Re-optimization)**: baseline + GEPA újrafuttatás, export, éles validáció (STRY0010010).
