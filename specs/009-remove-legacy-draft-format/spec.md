# Feature Specification: Remove Legacy Draft/Format Pipeline Branch

**Feature Branch**: `009-remove-legacy-draft-format`

**Created**: 2026-07-27

**Status**: Approved (code review follow-up)

**Input**: A code review established that the `DraftSections`+`FormatKB` generation branch (the fallback without a template) is dead in production: every team has a template, and `GenerateKbFromTemplate` is the primary path. Because of the two parallel paths, GEPA optimizes 5 predictors instead of 3, and the instructions can diverge. Removing the old branch; `template_context` becomes mandatory.

## Scope

- `program.py`: deleting the branch without a template; `ValueError` when `template_context=""` (the pipeline always passes it anyway; the dry-run is not affected).
- `signatures.py`: deleting `DraftSections` and `FormatKB`.
- `program.py` predictors: 5 → 3 (`analyze_changes`, `extract`, `generate_from_template`).
- Aligning the tests (`test_program.py`, `test_signatures.py`).
- Regenerating `artifacts/program.json` (the old state is incompatible because of the architecture change) — GEPA re-run.

## Acceptance Criteria

1. The length of `StoryToKBArticle().predictors()` is 3.
2. `forward(template_context="")` raises a ValueError ("template is mandatory").
3. The full test suite passes; `DraftSections`/`FormatKB` are not referenced anywhere.
4. GEPA re-run + production STRY0010010 validation.
