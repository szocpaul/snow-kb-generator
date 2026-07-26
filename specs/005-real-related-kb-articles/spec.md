# Feature Specification: Real Related KB Articles from ServiceNow

**Feature Branch**: `005-real-related-kb-articles`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "The 'Table of related KB articles' section currently contains hallucinated short descriptions with KBXXXXXXX placeholder numbers, because the template requires the section but there is no real data source. The pipeline must find real related articles via a ServiceNow KB search before generation, and those (real number + real title) must go into the table. If there is no hit, the section must be 'N/A'."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - KB Search in ServiceNow Client (Priority: P1)

The `ServiceNowClient` gets a `search_kb_articles(query, limit)` method that searches the `kb_knowledge` table (by short_description, with `123TEXTQUERY321` or the CONTAINS operator) and returns a structured list: `[{number, short_description, sys_id}]`.

**Why this priority**: This data source is the foundation of the whole feature — without real articles there is nothing to put into the table.

**Independent Test**: Testable with a mocked ServiceNow response: the method builds the query correctly and extracts the fields from the response.

**Acceptance Scenarios**:

1. **Given** a mocked kb_knowledge response with 2 articles, **When** `search_kb_articles("jira")` runs, **Then** the list contains the real number + short_description pairs.
2. **Given** an empty result list, **When** the method runs, **Then** it returns an empty list (it does not raise an error).

---

### User Story 2 - Pipeline Integration (Priority: P1)

Before generation, `generate_kb_article()` fetches the related articles (based on the keywords of the Story short_description) and passes the `related_articles_context` to the program as a new input. The program fills the "Table of related KB articles" section from this; in case of an empty list, "N/A".

**Why this priority**: This way the real data reaches the model — the source of the hallucination disappears.

**Independent Test**: Mock client + mock program: the pipeline calls the search and forwards the received context into the program call.

**Acceptance Scenarios**:

1. **Given** the client finds 2 real articles, **When** the pipeline runs, **Then** the program's `related_articles_context` contains the real KB numbers and titles.
2. **Given** there is no hit, **When** the pipeline runs, **Then** the context is an empty value marked as "N/A", and the section in the generated article is "N/A".
3. **Given** the KB search raises an error (network), **When** the pipeline runs, **Then** generation continues with a warning (as with the Update Set retrieval).

---

### User Story 3 - Guardrail & Metric Extension (Priority: P1)

The hallucination check (spec 004) is extended to the `related_articles_context`: KB numbers originating from the real search results count as "known" references both in `strip_hallucinated_references()` and in the metric's hallucination axis.

**Why this priority**: Without this, the guardrail from spec 004 would delete exactly the real articles as hallucinations (false positive).

**Independent Test**: The guardrail leaves a KB number appearing in the related context untouched, and still removes the ones outside it.

**Acceptance Scenarios**:

1. **Given** generated HTML with a KB number originating from the related context, **When** the guardrail runs, **Then** the reference stays intact.
2. **Given** the metric also knows the related context, **When** the pred contains the real number, **Then** there is no hallucination penalty.

---

### User Story 4 - Re-optimization (Priority: P2)

Because the signature changes (new input), the baseline + GEPA are re-run, a new `artifacts/program.json` is exported, and production validation is performed.

**Acceptance Scenarios**:

1. **Given** the new program, **When** the GEPA run completes, **Then** the optimized program fills the related section with real data (validated on the valset + production STRY0010010).

## Requirements

- **FR-001**: `ServiceNowClient.search_kb_articles(query, limit=5)` → `[{number, short_description, sys_id}]`, error-tolerant (ServiceNowError propagates, but the pipeline catches it).
- **FR-002**: The pipeline passes the search result to the program as a `related_articles_context` string (format: `KB<number> | <short_description>` per line).
- **FR-003**: The program signature is extended with the `related_articles_context` input (default ""); in the empty case the section is "N/A".
- **FR-004**: `strip_hallucinated_references(html, story_text, known_refs="")` — the KB numbers of the `related_articles_context` count as known references.
- **FR-005**: The metric's hallucination axis also takes the gold example's optional `related_articles_context` field into account.
- **FR-006**: In dry-run mode the search can be skipped (mock article).

## Success Criteria

- **SC-001**: In the production STRY0010010 article the "Related articles" table contains real KB numbers (articles that exist in ServiceNow), or "N/A".
- **SC-002**: The guardrail's false-positive rate is 0 on the real hits (covered by tests).
- **SC-003**: The full test suite is GREEN.
