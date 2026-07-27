# Feature Specification: Remove Legacy Draft/Format Pipeline Branch

**Feature Branch**: `009-remove-legacy-draft-format`

**Created**: 2026-07-27

**Status**: Approved (code review follow-up)

**Input**: A code review megállapította, hogy a `DraftSections`+`FormatKB` generálási ág (template nélküli fallback) produkcióban halott: minden csapathoz tartozik sablon, a `GenerateKbFromTemplate` az elsődleges út. A két párhuzamos út miatt a GEPA 5 prediktort optimalizál 3 helyett, és az instrukciók eltérhetnek. A régi ág kivezetése; a `template_context` kötelező lesz.

## Scope

- `program.py`: a template nélküli ág törlése; `template_context=""` esetén `ValueError` (a pipeline amúgy is mindig átadja; dry-run nem érintett).
- `signatures.py`: `DraftSections` és `FormatKB` törlése.
- `program.py` prediktorok: 5 → 3 (`analyze_changes`, `extract`, `generate_from_template`).
- Tesztek igazítása (`test_program.py`, `test_signatures.py`).
- `artifacts/program.json` újragenerálása (architektúra-változás miatt a régi state inkompatibilis) — GEPA újrafutás.

## Acceptance Criteria

1. `StoryToKBArticle().predictors()` hossza 3.
2. `forward(template_context="")` ValueError-t dob ("template kötelező").
3. Teljes tesztcsomag zöld; `DraftSections`/`FormatKB` sehol nem hivatkozott.
4. GEPA újrafutás + éles STRY0010010 validáció.
