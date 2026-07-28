# Implementation Plan: Human-Written Style for Generated KB Articles

**Branch**: `010-human-style-articles` | **Date**: 2026-07-28 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.2.x, Kimi K3 (task + judge LM, `_RefreshingKimiLM`)
- Érintett fájlok: `src/snow_kb/signatures.py` (US1), `eval/metric.py` (US2), `eval/gepa_optimize.py` (US3), `tests/`

## Architecture

```
                        (US1) signature docstring + stílus-blokk
                                    │
generált cikk ──► rich_metric ──────┼── structure / content / template / hallucination
                    │               └── (US2) style_judge() [Kimi K3, LLM-as-judge]
                    │                     score 0-1 + konkrét kritika
                    ▼
              GEPA reflection látja a feedback-et
                    │
                    ▼
         (US3) SkilledProposer(additional_instructions = style guidance)
                    │  általánosítható stílus-szabályok a promptokba
                    ▼
         (US4) kis büdzséjű GEPA (≤300 call) → style axis javulás igazolása
```

## Key Decisions

1. **A judge egy `dspy.Signature` a metric.py-ben** (`StyleJudge`: article_html + style_reference → score + critique), Kimi K3 LM-mel. Nem külön modul — a metric a helye.
2. **Hibatűrés:** judge-Exception → score=0.5 + warning log; a metric sosem áll meg.
3. **Súlyok:** 0.25 structure + 0.25 content + 0.15 template + 0.15 hallucination + 0.20 style. A meglévő tesztek thresholdjai igazítandók.
4. **A style referencia a judge promptjába égett**: a KB0010015 gold cikk egy reprezentatív részlete (nem a teljes HTML — token-takarékosság).
5. **Boilerplate-tiltólista megosztott konstans** (`BANNED_PHRASES`): a signature-blokk, a judge prompt és az SC-001 regex-ellenőrzés ugyanazt a listát használja.
6. **US3 csak az `additional_instructions` szövegét cseréli** a meglévő SkilledProposer-példányon — a fallback-logika és a prompt_model változatlan.
7. **Nincs docstring-konszolidáció** (külön spec, backlog).

## Phases

1. **Phase 1 (US1)**: signature stílus-blokk + `BANNED_PHRASES` konstans + tesztek.
2. **Phase 2 (US2)**: `StyleJudge` signature + `style_score()` a metric-ben + hibatűrés + tesztek (mock judge-dal).
3. **Phase 3 (US3)**: SkilledProposer style guidance + teszt.
4. **Phase 4 (US4)**: GEPA futás (≤300 call, Kimi task+reflection) → style axis javulásának igazolása + éles validáció + docs.
