# Implementation Plan: Direction-Aware KB Quality

**Branch**: `007-direction-aware-quality` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.2.x, `skilled-proposer` (új pip függőség), pytest
- Érintett fájlok: `eval/metric.py`, `eval/gepa_optimize.py`, `src/snow_kb/signatures.py`, `tests/`, `pyproject.toml`

## Architecture

```
story_text ──► detect_direction() ──► inbound | outbound | both | unknown
                         │
        ┌────────────────┼─────────────────────┐
        ▼                ▼                     ▼
  rich_metric      SkilledProposer       GenerateKbFromTemplate
  (direction       (extra_guidance:      (signature: explicit
   violation        direction rule +      direction rule)
   feedback)        no invented KB refs)
        │                │
        └──── GEPA ◄─────┘
              (Kimi K3 reflection látja a jelet)
```

## Key Decisions

1. **Irány-detektálás helye**: a metric-ben, egyszerű kulcsszó-számlálással (story_text). Nem a programban — a metric az igazságpont, a program a GEPA által szabadon alakítható.
2. **Súlyok változatlanok**: a direction violation a meglévő `template_adherence` tengelyen belül pontoz (0 helyett 0.5 vagy 0), nem kerül új tengely — elkerüljük a spec 004-es újrasúlyozást.
3. **SkilledProposer fallback**: ha a csomag nem importálható, a `run_gepa_optimization()` stock proposerre esik vissza warning-gal (a CI/mock tesztek így nem igénylik a csomagot).
4. **Guardrail NEM bővül** (out of scope): előbb megnézzük, a metric+GEPA útvonal elég-e.

## Phases

1. **Phase 1 (Metric)**: `detect_direction()` + direction violation a template_adherence-ben + feedback + tesztek.
2. **Phase 2 (Signature)**: explicit irányszabály a `GenerateKbFromTemplate` docstringbe.
3. **Phase 3 (Proposer)**: `skilled-proposer` telepítés, `run_gepa_optimization()` átállás + konfig (`extra_guidance`) + teszt.
4. **Phase 4 (Re-opt)**: baseline + GEPA + export + éles validáció + docs.
