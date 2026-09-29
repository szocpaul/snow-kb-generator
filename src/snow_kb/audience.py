"""audience.py — kalibrált, típusos audience-döntés a TypeSafe System One-nal (spec 013).

A pipeline ExtractChange.audience mezőjét ez a modul állítja elő a generatív
modell helyett: egy dedikált, típusos Choice-hívás adja a kiválasztott opciót,
az opciónkénti valószínűségeket és a confidence-t.

Elvek (spec.md):
  - FR-001 fail-open: BÁRMILYEN hiba (timeout, 5xx, auth, séma-eltérés) esetén
    None-t adunk vissza — a pipeline a generatív audience-úton fut tovább.
  - FR-002: a döntési modell pinnelt verziója a config.yaml-ból jön.
  - FR-003: minden sikeres döntés JSONL-be naplózódik (request hash, response,
    latency, modellazonosító — a jev-dspy-lab formátuma), replay-kompatibilisen.
  - US2: confidence < küszöb → "developer" default + work_notes-jelzés.
    A küszöb-operátor '<' (NEM '<='), és a pontosan határérték is a biztonságos
    (fallback) irányba dől (spec Edge Cases + T009): ezt a confidence < threshold + eps
    alak elégíti ki — eps = 1e-9, ami a kettes tizedesjegyes API-confidence-on
    pontosan a határértékre korlátozódik.
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

# A zárt opcióhalmaz — a schemas.Audience Literal-lel azonos sorrendben.
AUDIENCE_OPTIONS: tuple[str, ...] = ("helpdesk", "end-user", "developer")

# A döntési kérdés és kritériumok. A T012 kalibrációs wrapper (eval-only)
# UGYANEZEKET tükrözi — a szöveg módosítása = új baseline + újramérés.
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

# US2 default: a legbiztonságosabb technikai hangnem (plan.md Key Decision 6).
LOW_CONFIDENCE_DEFAULT = "developer"

# Ld. modul-docstring: '<' operátor + határérték a fallback irányába.
_BOUNDARY_EPSILON = 1e-9


@dataclass(frozen=True)
class AudienceDecision:
    """Egy típusos audience-döntés eredménye."""

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
    """JSONL recording a jev-dspy-lab formátumában (FR-003).

    A már rögzített request hashet nem írjuk újra (a replay-index
    fail-closed a duplikációra — ld. vendor/jev_replay.load_replay_index).
    A recording hibája sosem dönti el a pipeline-t.
    """
    try:
        path = Path(recording_path)
        request_hash = system_one_request_hash(state, questions, model=model)
        if path.exists():
            if request_hash in load_replay_index(path):
                return
        payload = response_to_payload(response)
        if not isinstance(payload, dict):
            raise TypeError("A rögzített válasz nem objektumra sorolható")
        row = {
            "request_hash": request_hash,
            "source": "recorded",
            "model": model,
            "response": {**payload, "latency_ms": round(latency_ms, 3)},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    except Exception as exc:  # a naplózás hibája ne állítsa le a pipeline-t
        logger.warning("Audience recording sikertelen (%s): %s", recording_path, exc)


def decide_audience(
    story_text: str,
    settings: Settings,
    *,
    client: Any = None,
) -> AudienceDecision | None:
    """Típusos audience-döntés a System One API-val.

    Args:
        story_text: a teljes, címkézett Story-szöveg (assemble_story_text kimenete).
        settings: a pipeline Settings (audience_decision blokkot olvas).
        client: opcionális system_one-kompatibilis client (teszt/replay).
            None esetén éles TypeSafeClient készül a TYPESAFE_API_KEY-ből.

    Returns:
        AudienceDecision, vagy None fail-open esetén (hiba, hiányzó kulcs,
        séma-eltérés) — a hívó ilyenkor a generatív audience-útra esik vissza.
    """
    cfg = settings.audience_decision
    try:
        if client is None:
            if not os.environ.get("TYPESAFE_API_KEY"):
                logger.warning(
                    "TYPESAFE_API_KEY nincs beállítva — audience fail-open a generatív útra."
                )
                return None
            from typesafe_sdk import TypeSafeClient

            client = TypeSafeClient()

        state = {"text": story_text}
        questions = _build_questions()

        started = time.perf_counter()
        response = client.system_one(state=state, questions=questions, model=cfg.model)
        latency_ms = (time.perf_counter() - started) * 1000.0

        # --- Válasz validálása (séma-eltérés = fail-open, spec Edge Cases) ---
        answer = response.answers["audience"]
        choice = str(answer.choice)
        confidence = float(answer.confidence)
        probabilities = {str(k): float(v) for k, v in dict(answer.probabilities).items()}
        if choice not in AUDIENCE_OPTIONS:
            raise ValueError(f"Ismeretlen audience-opció a válaszban: {choice!r}")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence kívül a [0,1] intervallumon: {confidence}")
        missing = set(AUDIENCE_OPTIONS) - set(probabilities)
        if missing:
            raise ValueError(f"Hiányzó valószínűségek a válaszból: {sorted(missing)}")

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
            "Audience döntés: %s (confidence=%.2f, modell=%s, %.0f ms)",
            decision.choice, decision.confidence, decision.model, latency_ms,
        )
        return decision
    except Exception as exc:
        logger.warning(
            "Audience döntés fail-open (%s: %s) — a generatív út marad.",
            type(exc).__name__, exc,
        )
        return None


def resolve_audience(
    story_text: str,
    settings: Settings,
    *,
    client: Any = None,
) -> tuple[str | None, str]:
    """A pipeline által hívott belépési pont: (audience_override, work_note).

    - enabled=False vagy fail-open → (None, ""): a generatív út marad.
    - confidence < threshold (+ eps, ld. modul-docstring) →
      ("developer", jelzés a mért értékkel) — US2.
    - egyébként → (decision.choice, "").
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
            f"Audience döntés bizonytalan: mért confidence={decision.confidence:.2f} "
            f"(küszöb={threshold:.2f}); alapértelmezett '{LOW_CONFIDENCE_DEFAULT}' "
            "hangnem használva (spec 013)."
        )
        logger.info("Alacsony audience-confidence (%.2f < %.2f) → developer default.",
                    decision.confidence, threshold)
        return LOW_CONFIDENCE_DEFAULT, note

    return decision.choice, ""


def replay_client_from_recording(recording_path: str | Path) -> ReplayClient:
    """Fail-closed replay client egy korábbi recordingból (SC-004)."""
    return ReplayClient(load_replay_index(recording_path))
