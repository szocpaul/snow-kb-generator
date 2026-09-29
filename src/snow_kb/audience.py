"""audience.py — calibrated, typed audience decision with TypeSafe System One (spec 013).

This module produces the pipeline's ExtractChange.audience field instead of the
generative model: a dedicated, typed Choice call returns the selected option,
the per-option probabilities and the confidence.

Elvek (spec.md):
  - FR-001 fail-open: on ANY error (timeout, 5xx, auth, schema mismatch) we
    return None — the pipeline continues on the generative audience path.
  - FR-002: the pinned version of the decision model comes from config.yaml.
  - FR-003: every successful decision is logged to JSONL (request hash, response,
    latency, model identifier — the jev-dspy-lab format), replay-compatible.
  - US2: confidence < threshold → "developer" default + a work_notes signal.
    The threshold operator is '<' (NOT '<='), and exactly the threshold value also
    leans to the safe (fallback) direction (spec Edge Cases + T009): the
    confidence < threshold + eps form satisfies this — eps = 1e-9, which on the
    two-decimal API confidence is limited to exactly the threshold value.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snow_kb.config import Settings
from snow_kb.vendor.jev_replay import (
    ReplayClient,
    load_replay_index,
    response_to_payload,
    system_one_request_hash,
)

logger = logging.getLogger(__name__)

# The closed option set — in the same order as the schemas.Audience Literal.
AUDIENCE_OPTIONS: tuple[str, ...] = ("helpdesk", "end-user", "developer")

# The decision question and criteria. The T012 calibration wrapper (eval-only)
# MIRRORS THESE — changing the text means a new baseline + a new measurement.
AUDIENCE_QUESTION = (
    "Who is the primary audience for a knowledge base article about this change?"
)
AUDIENCE_CRITERIA: dict[str, str] = {
    "helpdesk": (
        "IT support / helpdesk staff who use the article to diagnose and resolve "
        "user tickets; the article is a troubleshooting aid."
    ),
    "end-user": (
        "Business end users without technical background who follow the article "
        "to do their work."
    ),
    "developer": (
        "Developers or integration engineers who implement, maintain, or debug "
        "the technical change; the article documents the implementation."
    ),
}

# US2 default: the safest technical tone (plan.md Key Decision 6).
LOW_CONFIDENCE_DEFAULT = "developer"

# See the module docstring: the '<' operator + the threshold value leans to the fallback direction.
_BOUNDARY_EPSILON = 1e-9


@dataclass(frozen=True)
class AudienceDecision:
    """The result of a typed audience decision."""

    choice: str
    probabilities: dict[str, float]
    confidence: float
    model: str


def _build_questions() -> dict[str, Any]:
    from typesafe_sdk import Choice

    return {
        "audience": Choice(
            instructions=AUDIENCE_QUESTION,
            criteria=dict(AUDIENCE_CRITERIA),
        )
    }


def _record_decision(
    recording_path: str,
    *,
    state: dict,
    questions: dict,
    model: str,
    response: Any,
    latency_ms: float,
) -> None:
    """JSONL recording in the jev-dspy-lab format (FR-003).

    An already recorded request hash is not written again (the replay index is
    fail-closed on duplicates — see vendor/jev_replay.load_replay_index).
    A recording error never decides the pipeline.
    """
    try:
        path = Path(recording_path)
        request_hash = system_one_request_hash(state, questions, model=model)
        if path.exists():
            if request_hash in load_replay_index(path):
                return
        payload = response_to_payload(response)
        if not isinstance(payload, dict):
            raise TypeError("The recorded response cannot be mapped to an object")
        row = {
            "request_hash": request_hash,
            "source": "recorded",
            "model": model,
            "response": {**payload, "latency_ms": round(latency_ms, 3)},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    except Exception as exc:  # a logging error must not stop the pipeline
        logger.warning("Audience recording sikertelen (%s): %s", recording_path, exc)


def decide_audience(
    story_text: str,
    settings: Settings,
    *,
    client: Any = None,
) -> AudienceDecision | None:
    """Typed audience decision with the System One API.

    Args:
        story_text: the full, labelled Story text (the output of assemble_story_text).
        settings: a pipeline Settings (audience_decision blokkot olvas).
        client: an optional system_one-compatible client (test/replay).
            When None, a production TypeSafeClient is created from TYPESAFE_API_KEY.

    Returns:
        AudienceDecision, or None in the fail-open case (error, missing key,
        schema mismatch) — the caller then falls back to the generative audience path.
    """
    cfg = settings.audience_decision
    try:
        if client is None:
            if not os.environ.get("TYPESAFE_API_KEY"):
                logger.warning(
                    "TYPESAFE_API_KEY is not set — audience fail-open to the generative path."
                )
                return None
            from typesafe_sdk import TypeSafeClient

            client = TypeSafeClient()

        state = {"text": story_text}
        questions = _build_questions()

        started = time.perf_counter()
        response = client.system_one(state=state, questions=questions, model=cfg.model)
        latency_ms = (time.perf_counter() - started) * 1000.0

        # --- Response validation (schema mismatch = fail-open, spec Edge Cases) ---
        answer = response.answers["audience"]
        choice = str(answer.choice)
        confidence = float(answer.confidence)
        probabilities = {str(k): float(v) for k, v in dict(answer.probabilities).items()}
        if choice not in AUDIENCE_OPTIONS:
            raise ValueError(f"Unknown audience option in the response: {choice!r}")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence outside the [0,1] interval: {confidence}")
        missing = set(AUDIENCE_OPTIONS) - set(probabilities)
        if missing:
            raise ValueError(f"Missing probabilities in the response: {sorted(missing)}")

        model = str(getattr(response, "model", None) or cfg.model)
        decision = AudienceDecision(
            choice=choice,
            probabilities=probabilities,
            confidence=confidence,
            model=model,
        )
        _record_decision(
            cfg.recording_path,
            state=state,
            questions=questions,
            model=cfg.model,
            response=response,
            latency_ms=latency_ms,
        )
        logger.info(
            "Audience decision: %s (confidence=%.2f, model=%s, %.0f ms)",
            decision.choice, decision.confidence, decision.model, latency_ms,
        )
        return decision
    except Exception as exc:
        logger.warning(
            "Audience decision fail-open (%s: %s) — the generative path stays.",
            type(exc).__name__, exc,
        )
        return None


def resolve_audience(
    story_text: str,
    settings: Settings,
    *,
    client: Any = None,
) -> tuple[str | None, str]:
    """The entry point called by the pipeline: (audience_override, work_note).

    - enabled=False or fail-open → (None, ""): the generative path stays.
    - confidence < threshold (+ eps, ld. modul-docstring) →
      ("developer", a signal with the measured value) — US2.
    - otherwise → (decision.choice, "").
    """
    cfg = settings.audience_decision
    if not cfg.enabled:
        return None, ""

    decision = decide_audience(story_text, settings, client=client)
    if decision is None:
        return None, ""

    threshold = cfg.confidence_threshold
    if decision.confidence < threshold + _BOUNDARY_EPSILON:
        note = (
            f"Audience decision uncertain: measured confidence={decision.confidence:.2f} "
            f"(threshold={threshold:.2f}); using the default '{LOW_CONFIDENCE_DEFAULT}' "
            "tone (spec 013)."
        )
        logger.info("Alacsony audience-confidence (%.2f < %.2f) → developer default.",
                    decision.confidence, threshold)
        return LOW_CONFIDENCE_DEFAULT, note

    return decision.choice, ""


def replay_client_from_recording(recording_path: str | Path) -> ReplayClient:
    """Fail-closed replay client from an earlier recording (SC-004)."""
    return ReplayClient(load_replay_index(recording_path))
