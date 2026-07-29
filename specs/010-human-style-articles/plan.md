# Implementation Plan: Human-Written Style for Generated KB Articles

**Branch**: `010-human-style-articles` | **Date**: 2026-07-28 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.2.x
- **Task + judge LM: lokális Qwen3.6-35B-A3B** (llama.cpp, `http://desktop-c5ikame-1.tailee6bc1.ts.net:8033/v1`) — 2026-07-29-i TISZTA mérések (`cache=False`, régi dataset): K3 0.769 > lokális 0.733; a lokális mellett a nulla marginális költség döntött (GEPA-rolloutok)
- **Dataset**: tisztított, 8 példás (4 train / 4 val, 2026-07-29) — gold HTML-ek boilerplate-mentesek, KB0010015 referencia a `data/examples/`-ben; a baseline-t ezen kell újramérni (T010)
- **GEPA reflection/proposer: Kimi K3** (`_RefreshingKimiLM`) — az egyetlen megmaradt Kimi-függés, kevés hívással
- Judge és task ugyanaz a modell — tudatos kompromisszum (költség 0); az SC-002 validáció (gépies/emberi teszt-ikonok) ellenőrzi a judge torzítását
- Mérési scriptekben `cache=False` kötelező (fals cache-replay tanulság, 2026-07-29)
- Érintett fájlok: `src/snow_kb/signatures.py` (US1), `eval/metric.py` (US2), `eval/gepa_optimize.py` (US3), `tests/`

## Architecture

```
                        (US1) signature docstring + stílus-blokk
                                    │
generált cikk ──► rich_metric ──────┼── structure / content / template / hallucination
                    │               └── (US2) style_judge() [lokális Qwen, LLM-as-judge]
                    │                     score 0-1 + konkrét kritika
                    ▼
              GEPA reflection látja a feedback-et
                    │
                    ▼
         (US3) SkilledProposer(additional_instructions = style guidance)
                    │  általánosítható stílus-szabályok a promptokba
                    ▼
         (US4) GEPA (max_metric_calls=200, lokális rollout + Kimi K3 reflection)
                    → style axis javulás igazolása
```

## Key Decisions

1. **A judge egy `dspy.Signature` a metric.py-ben** (`StyleJudge`: article_html + style_reference → score + critique), **lokális Qwen LM-mel** (ugyanaz az endpoint, mint a task modell). Nem külön modul — a metric a helye.
2. **Hibatűrés:** judge-Exception (pl. a lokális szerver nem elérhető) → score=0.5 + warning log; a metric sosem áll meg.
3. **Súlyok:** 0.25 structure + 0.25 content + 0.15 template + 0.15 hallucination + 0.20 style. A meglévő tesztek thresholdjai igazítandók.
4. **A style referencia a judge promptjába égett**: a KB0010015 gold cikk egy reprezentatív részlete (nem a teljes HTML — token-takarékosság).
5. **Boilerplate-tiltólista megosztott konstans** (`BANNED_PHRASES`): a signature-blokk, a judge prompt és az SC-001 regex-ellenőrzés ugyanazt a listát használja.
6. **US3 csak az `additional_instructions` szövegét cseréli** a meglévő SkilledProposer-példányon — a fallback-logika és a prompt_model (Kimi K3) változatlan.
7. **Nincs docstring-konszolidáció** (külön spec, backlog).
8. **Cache-higiénia:** minden mérési útvonal (`run_baseline`, GEPA compile, validáció) `cache=False` LM-mel fut — a disk cache más modell válaszait is visszajátszhatja (2026-07-29-i fals baseline). Az `eval/baseline.py` javítása már megtörtént.

## Phases

1. **Phase 1 (US1)**: signature stílus-blokk + `BANNED_PHRASES` konstans + tesztek.
2. **Phase 2 (US2)**: `StyleJudge` signature + `style_score()` a metric-ben + hibatűrés + tesztek (mock judge-dal).
3. **Phase 3 (US3)**: SkilledProposer style guidance + teszt.
4. **Phase 4 (US4)**: GEPA futás (`max_metric_calls=200`, lokális task + judge + Kimi K3 reflection; ~2.5-3.5 óra, `-np 2` / `num_threads=2`) → style axis javulásának igazolása + éles validáció + docs.
