"""context_selection.py — kontextus-válogatás a cikkgenerálás előtt (spec 016).

A GenerateKb kontextus-darabjai (story-szekciók, update set rekordok,
kapcsolódó KB-cikkek) a generálás előtt kalibrált Score-minősítést kapnak:
hide / summarize / show. A pontszám a TypeSafe System One Score-primitívéből
jön (pinnelt modellel, confidence-szel); a végrehajtás PLAIN PYTHON POLICY —
a modell csak pontoz, a küszöböket a config tartja (plan.md KD1/KD2).

Elvek:
  - FR-002 fail-open: BÁRMILYEN hiba (SDK, séma, endpoint) vagy alacsony
    confidence esetén a darab változatlanul bekerül (show) — a jelenlegi
    viselkedés a biztonságos alap.
  - FR-003: minden Score-döntés replay-kompatibilis JSONL-be naplózódik
    (a 013-as jev-formátum, vendor/jev_replay.py).
  - FR-004: a story-főtörzs (short_description / description /
    acceptance_criteria / u_technical_specification) SOSEM hide — rá
    LLM-hívás sem indul.
  - FR-006: enabled=False esetén a select_context bit-azonos identitás.
  - A küszöb-operátor '<' — a pontos határérték a biztonságos (show-felé
    eső) osztályba dől (a 013-as _BOUNDARY_EPSILON minta).
  - A summarize a LOKÁLIS Qwen-endpointon készül (KD3), NEM a task-modellel;
    endpoint-hiba esetén a darab az eredeti szöveggel kerül be (fail-open).
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from snow_kb.config import Settings
from snow_kb.vendor.jev_replay import (
    load_replay_index,
    response_to_payload,
    system_one_request_hash,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Típusok
# ---------------------------------------------------------------------------

SourceType = Literal["story_core", "story_meta", "update_set_record", "related_article"]
Verdict = Literal["hide", "summarize", "show"]

# FR-004: a story-főtörzs mezői — ezek SOSEM rejthetők el.
STORY_CORE_FIELDS: frozenset[str] = frozenset({
    "short_description",
    "description",
    "acceptance_criteria",
    "u_technical_specification",
})

# A Score-rubric 3 szintje (0..2). A szöveg módosítása = új baseline
# (a recording request-hash a kérdésből származik).
RELEVANCE_CRITERIA: tuple[str, str, str] = (
    "Noise: irrelevant metadata, boilerplate, or administrative content that "
    "does not help write the knowledge base article",
    "Supporting: useful background that can be condensed to a short summary "
    "without losing what the knowledge base article needs",
    "Essential: concrete change details (components, steps, configuration) "
    "the knowledge base article must reflect",
)
RELEVANCE_QUESTION = (
    "How much of this context piece matters for writing the knowledge base "
    "article about the change?"
)

# A summarize alapértelmezett modellje a lokális llama.cpp szerveren (KD3).
SUMMARIZER_MODEL = r"models\Qwen3.8-27B-UD-Q4_K_M.gguf"

# Ld. modul-docstring: '<' operátor + határérték a biztonságos irányába.
_BOUNDARY_EPSILON = 1e-9

# A Score-szintek száma → a normalizált relevancia = score / (N-1) ∈ [0,1].
_SCORE_LEVELS = len(RELEVANCE_CRITERIA)


@dataclass(frozen=True)
class ContextPiece:
    """A generálás bemenetének egy darabja + forrás-típus."""

    piece_id: str
    source_type: SourceType
    label: str
    text: str


@dataclass(frozen=True)
class PieceDecision:
    """Egy darab minősítése + bizonyíték."""

    piece_id: str
    source_type: SourceType
    verdict: Verdict
    relevance: float | None   # normalizált [0,1]; None fail-open/story-core esetén
    confidence: float | None
    model: str
    reason: str               # score | low-confidence | fail-open | story-core
    summarized: bool = False  # True, ha a summarize ténylegesen lecserélte a szöveget


@dataclass
class SelectionResult:
    """A válogatott kontextus + a döntési nyomvonal."""

    story_text: str
    update_set_payloads: str
    related_articles_context: str
    decisions: list[PieceDecision] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Darabolás
# ---------------------------------------------------------------------------

# A markdown címkék → mezőazonosítók (a pipeline._FIELD_LABELS inverze +
# a Technical Specification alias).
def _label_to_field(label: str) -> str:
    from snow_kb.pipeline import _FIELD_LABELS

    reverse = {v: k for k, v in _FIELD_LABELS.items()}
    return reverse.get(label.strip(), label.strip().lower().replace(" ", "_"))


def split_story_into_pieces(story_text: str) -> list[ContextPiece]:
    """A story-szöveg felbontása mező/szekció-darabokra.

    Két formátumot kezel:
      - JSON story (a gold dataset alakja): mezőnként egy darab, a darab
        szövege egy JSON-fragment ("mező": érték), amiből a story
        újraépíthető.
      - Markdown story (a production assemble_story_text alakja): '## '
        fejlécenként egy darab; az első fejléc előtti preambulum (pl.
        '# Story: STRY...') mindig story_core.
    """
    text = (story_text or "").strip()
    if not text:
        return []

    # --- JSON story ---
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            pieces = []
            for field_name, value in data.items():
                if value is None or (isinstance(value, str) and not value.strip()):
                    continue
                fragment = json.dumps(field_name, ensure_ascii=False) + ": " + json.dumps(
                    value, ensure_ascii=False)
                source: SourceType = (
                    "story_core" if field_name in STORY_CORE_FIELDS else "story_meta"
                )
                pieces.append(ContextPiece(
                    piece_id=f"story:{field_name}",
                    source_type=source,
                    label=field_name.replace("_", " ").title(),
                    text=fragment,
                ))
            if pieces:
                return pieces
        # nem parse-olható JSON → essen át a markdown-útra

    # --- Markdown story ---
    import re

    parts = re.split(r"(?m)^(?=## )", text)
    pieces = []
    preamble = parts[0].strip() if parts else ""
    if preamble:
        pieces.append(ContextPiece(
            piece_id="story:header",
            source_type="story_core",  # '# Story: STRY...' fejléc — mindig bekerül
            label="Story Header",
            text=preamble,
        ))
    for section in parts[1:] if preamble else parts:
        section = section.strip()
        if not section:
            continue
        m = re.match(r"## ([^\n]+)\n?", section)
        label = m.group(1).strip() if m else "Section"
        field_name = _label_to_field(label)
        source = "story_core" if field_name in STORY_CORE_FIELDS else "story_meta"
        pieces.append(ContextPiece(
            piece_id=f"story:{field_name}",
            source_type=source,
            label=label,
            text=section,
        ))
    return pieces


def split_update_set_into_pieces(update_set_payloads: str) -> list[ContextPiece]:
    """Az update set XML felbontása rekord-darabokra.

    Minden <record_update ...>...</record_update> blokk egy darab. Ha a
    payload nem parse-olható vagy nincs record_update blokk, a teljes
    payload EGY darab (fail-open a darabolásban is).
    """
    import re

    text = (update_set_payloads or "").strip()
    if not text:
        return []

    blocks = re.findall(
        r"<record_update\b.*?</record_update>", text, flags=re.DOTALL
    )
    if not blocks:
        return [ContextPiece(
            piece_id="update_set:raw",
            source_type="update_set_record",
            label="update set payload",
            text=text,
        )]

    pieces = []
    for idx, block in enumerate(blocks):
        table_m = re.search(r'table="([^"]+)"', block)
        table = table_m.group(1) if table_m else "record"
        name_m = re.search(r"<name>([^<]*)</name>", block)
        name = name_m.group(1).strip() if name_m else ""
        label = f"{table}:{name}" if name else table
        pieces.append(ContextPiece(
            piece_id=f"update_set:{idx}:{table}:{name}",
            source_type="update_set_record",
            label=label,
            text=block,
        ))
    return pieces


def split_related_into_pieces(related_articles_context: str) -> list[ContextPiece]:
    """A kapcsolódó KB cikkek soronként egy darab ('KB001 | cím' sorok)."""
    text = (related_articles_context or "").strip()
    if not text:
        return []
    pieces = []
    for idx, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        number = line.split("|", 1)[0].strip() or f"line-{idx}"
        pieces.append(ContextPiece(
            piece_id=f"related:{number}",
            source_type="related_article",
            label=line[:80],
            text=line,
        ))
    return pieces


def split_context_into_pieces(
    *,
    story_text: str,
    update_set_payloads: str,
    related_articles_context: str,
) -> list[ContextPiece]:
    """A teljes kontextus darabolása (story + update set + kapcsolódó cikkek)."""
    return (
        split_story_into_pieces(story_text)
        + split_update_set_into_pieces(update_set_payloads)
        + split_related_into_pieces(related_articles_context)
    )


# ---------------------------------------------------------------------------
# Recording (FR-003) — a 013-as audience._record_decision mintája
# ---------------------------------------------------------------------------

def _build_questions() -> dict[str, Any]:
    from typesafe_sdk import Score

    return {
        "relevance": Score(
            instructions=RELEVANCE_QUESTION,
            criteria=list(RELEVANCE_CRITERIA),
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

    A már rögzített request hashet nem írjuk újra; a recording hibája
    sosem dönti el a pipeline-t.
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
        logger.warning("Context-selection recording sikertelen (%s): %s",
                       recording_path, exc)


# ---------------------------------------------------------------------------
# Score-döntés per darab
# ---------------------------------------------------------------------------

def _score_piece(
    piece: ContextPiece,
    *,
    settings: Settings,
    client: Any,
    story_context: str,
) -> PieceDecision:
    """Egy darab Score-minősítése + Python-policy. Bármilyen hiba → show."""
    cfg = settings.context_selection
    model = cfg.model
    state = {
        "story_context": story_context[:2000],
        "piece_type": piece.source_type,
        "piece_label": piece.label,
        "piece": piece.text[:6000],
    }
    questions = _build_questions()
    try:
        started = time.perf_counter()
        response = client.system_one(state=state, questions=questions, model=model)
        latency_ms = (time.perf_counter() - started) * 1000.0

        answer = response.answers["relevance"]
        score = float(answer.score)
        confidence = float(answer.confidence)
        if not 0.0 <= score <= _SCORE_LEVELS - 1:
            raise ValueError(f"score kívül a [0,{_SCORE_LEVELS - 1}] skálán: {score}")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence kívül a [0,1] intervallumon: {confidence}")

        _record_decision(
            cfg.recording_path,
            state=state, questions=questions, model=model,
            response=response, latency_ms=latency_ms,
        )
        relevance = score / (_SCORE_LEVELS - 1)

        # --- Python-policy (a modell csak pontoz; a küszöb a configé) ---
        if confidence < cfg.min_confidence + _BOUNDARY_EPSILON:
            return PieceDecision(
                piece.piece_id, piece.source_type, "show",
                relevance, confidence, model, "low-confidence",
            )
        if relevance < cfg.hide_below:
            verdict: Verdict = "hide"
        elif relevance < cfg.summarize_below:
            verdict = "summarize"
        else:
            verdict = "show"
        return PieceDecision(
            piece.piece_id, piece.source_type, verdict,
            relevance, confidence, model, "score",
        )
    except Exception as exc:
        logger.warning(
            "Context-selection fail-open a '%s' darabon (%s: %s) — show.",
            piece.piece_id, type(exc).__name__, exc,
        )
        return PieceDecision(
            piece.piece_id, piece.source_type, "show",
            None, None, model, "fail-open",
        )


def classify_pieces(
    pieces: list[ContextPiece],
    *,
    settings: Settings,
    client: Any = None,
    story_context: str = "",
) -> list[PieceDecision]:
    """Minden darab minősítése. A story_core darabokra LLM-hívás sem indul
    (FR-004); SDK-hiba esetén az adott darab show (FR-002), a többi
    feldolgozása folytatódik.
    """
    cfg = settings.context_selection
    decisions: list[PieceDecision] = []

    scoreable = [p for p in pieces if p.source_type != "story_core"]
    if scoreable and client is None:
        if not os.environ.get("TYPESAFE_API_KEY"):
            logger.warning(
                "TYPESAFE_API_KEY nincs beállítva — context-selection fail-open: "
                "minden darab változatlanul bekerül."
            )
            return [
                PieceDecision(p.piece_id, p.source_type, "show",
                              None, None, cfg.model,
                              "story-core" if p.source_type == "story_core" else "fail-open")
                for p in pieces
            ]
        from typesafe_sdk import TypeSafeClient

        client = TypeSafeClient()

    if not story_context:
        story_context = "\n".join(p.text for p in pieces if p.source_type == "story_core")

    for piece in pieces:
        if piece.source_type == "story_core":
            decisions.append(PieceDecision(
                piece.piece_id, piece.source_type, "show",
                None, None, cfg.model, "story-core",
            ))
            continue
        decisions.append(_score_piece(
            piece, settings=settings, client=client, story_context=story_context,
        ))
    return decisions


# ---------------------------------------------------------------------------
# Summarize a lokális Qwen-endpointon (KD3) — fail-open az eredeti szövegre
# ---------------------------------------------------------------------------

def summarize_piece(piece: ContextPiece, *, endpoint: str,
                    timeout_s: float = 120.0) -> str:
    """Rövid összefoglaló a darabról a LOKÁLIS endpointon.

    Bármilyen hiba esetén kivételt dob — a hívó ilyenkor az eredeti
    szöveget tartja meg (fail-open show).
    """
    import requests

    prompt = (
        "Summarize the following context piece for a knowledge-base-article "
        "writing task. Keep all component names, technical identifiers, table "
        "names, and error messages verbatim. Maximum 120 words.\n\n"
        f"Context piece ({piece.label}):\n{piece.text[:8000]}"
    )
    resp = requests.post(
        endpoint.rstrip("/") + "/chat/completions",
        json={
            "model": SUMMARIZER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 400,
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    summary = resp.json()["choices"][0]["message"]["content"].strip()
    if not summary:
        raise ValueError("üres összefoglaló érkezett az endpointról")
    return summary


# ---------------------------------------------------------------------------
# Döntések végrehajtása + újraépítés
# ---------------------------------------------------------------------------

def _reassemble(pieces: list[ContextPiece], texts: list[str], group: str) -> str:
    """A megmaradt darab-szövegekből kontextus-rész újraépítése."""
    if not texts:
        return ""
    if group == "story":
        # JSON-fragmentek → JSON-objektum; markdown szekciók → '\n\n' join
        if all(t.lstrip().startswith('"') for t in texts):
            return "{\n" + ",\n".join(texts) + "\n}"
        return "\n\n".join(texts)
    if group == "update_set":
        return "".join(texts)
    return "\n".join(texts)  # related_article sorok


def apply_decisions(
    pieces: list[ContextPiece],
    decisions: list[PieceDecision],
    *,
    settings: Settings,
) -> SelectionResult:
    """A döntések végrehajtása: hide → eldobás, summarize → összefoglaló
    (hiba esetén eredeti szöveg, fail-open), show → változatlan.
    """
    cfg = settings.context_selection
    by_id = {d.piece_id: d for d in decisions}

    story_texts: list[str] = []
    us_texts: list[str] = []
    related_texts: list[str] = []
    final_decisions: list[PieceDecision] = []

    for piece in pieces:
        decision = by_id.get(piece.piece_id)
        if decision is None:
            decision = PieceDecision(piece.piece_id, piece.source_type, "show",
                                     None, None, cfg.model, "fail-open")
        text: str | None = piece.text
        summarized = False
        if decision.verdict == "hide":
            text = None
        elif decision.verdict == "summarize":
            try:
                text = summarize_piece(piece, endpoint=cfg.summarizer_endpoint)
                summarized = True
            except Exception as exc:
                logger.warning(
                    "Summarize fail-open a '%s' darabon (%s: %s) — az eredeti "
                    "szöveg kerül be.",
                    piece.piece_id, type(exc).__name__, exc,
                )
                text = piece.text
        final_decisions.append(PieceDecision(
            decision.piece_id, decision.source_type, decision.verdict,
            decision.relevance, decision.confidence, decision.model,
            decision.reason, summarized=summarized,
        ))
        if text is None:
            continue
        if piece.source_type in ("story_core", "story_meta"):
            story_texts.append(text)
        elif piece.source_type == "update_set_record":
            us_texts.append(text)
        else:
            related_texts.append(text)

    return SelectionResult(
        story_text=_reassemble(pieces, story_texts, "story"),
        update_set_payloads=_reassemble(pieces, us_texts, "update_set"),
        related_articles_context=_reassemble(pieces, related_texts, "related"),
        decisions=final_decisions,
    )


def select_context(
    *,
    story_text: str,
    update_set_payloads: str,
    related_articles_context: str,
    settings: Settings,
    client: Any = None,
    pieces: list[ContextPiece] | None = None,
) -> SelectionResult:
    """A pipeline belépési pontja: kontextus → válogatott kontextus.

    enabled=False esetén bit-azonos identitás (FR-006). A `pieces`
    paraméterrel a hívó adhat előre darabolt kontextust (teszt/mérés).
    """
    cfg = settings.context_selection
    if not cfg.enabled:
        return SelectionResult(
            story_text=story_text,
            update_set_payloads=update_set_payloads,
            related_articles_context=related_articles_context,
            decisions=[],
        )

    if pieces is None:
        pieces = split_context_into_pieces(
            story_text=story_text,
            update_set_payloads=update_set_payloads,
            related_articles_context=related_articles_context,
        )
    decisions = classify_pieces(pieces, settings=settings, client=client)
    result = apply_decisions(pieces, decisions, settings=settings)

    n_hide = sum(1 for d in result.decisions if d.verdict == "hide")
    n_sum = sum(1 for d in result.decisions if d.verdict == "summarize")
    logger.info(
        "Context-selection: %d darab → %d hide, %d summarize, %d show",
        len(result.decisions), n_hide, n_sum,
        len(result.decisions) - n_hide - n_sum,
    )
    return result
