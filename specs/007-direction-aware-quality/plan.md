# Implementation Plan: Evidence-First KB Generation

**Branch**: `007-direction-aware-quality` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.2.x, `skilled-proposer` (új pip függőség), pytest
- Érintett fájlok: `eval/metric.py`, `eval/gepa_optimize.py`, `src/snow_kb/signatures.py`, `data/examples/gold_dataset.md`, `tests/`, `pyproject.toml`

## Architecture

```
story_text ──► detect_direction() ──► inbound | outbound | both | unknown
      │
      ├──── rich_metric: direction violation + unsupported section ──► feedback ──┐
      │                                                                           ▼
      ├──── GenerateKbFromTemplate (evidence-first: menu, not mandate) ◄── GEPA (Kimi K3)
      │                                                                           ▲
      └──── SkilledProposer(extra_guidance: evidence-first + no invented refs) ───┘

Sablon (KBA1–KBA11): MENÜ — a cikk a támogatott szekciókból épül fel.
```

## Key Decisions

1. **Kihagyás, nem N/A**: a támogatatlan szekció teljesen kimarad (sem "N/A" placeholder). A gold dataset is így áll át (N/A-only blokkok törlése).
2. **Direction violation = speciális eset explicit feedbackkel**: az általános unsupported-section ellenőrzés mellett az irányhiba saját, jól felismerhető feedback-stringet kap (a reflection modell gyorsabban tanul konkrét mintára).
3. **A metric az igazságpont**: irány-detektálás és támogatottság-ellenőrzés a metric-ben, a program a GEPA által szabadon alakítható.
4. **Súlyok változatlanok**: mindkét ellenőrzés a meglévő `template_adherence` tengelyen belül pontoz.
5. **SkilledProposer fallback**: import-hiba esetén stock proposer + warning (mock tesztek nem igénylik a csomagot).
6. **Guardrail NEM bővül** (out of scope).

## Phases

1. **Phase 1 (Metric)**: `detect_direction()` + direction violation + unsupported-section penalty + tesztek.
2. **Phase 2 (Signature + Dataset)**: evidence-first instrukció; gold dataset N/A-only blokkok törlése; dataset tesztek igazítása.
3. **Phase 3 (Proposer)**: `skilled-proposer` telepítés + `run_gepa_optimization()` átállás + teszt.
4. **Phase 4 (Re-opt)**: baseline + GEPA + export + éles validáció + docs.
