"""jev_replay.py — vendored record/replay helper a jev-dspy-lab mintájára.

Forrás: https://github.com/jmanhype/jev-dspy-lab (MIT License),
src/jev_dspy_lab/replay.py — a snow_kb_generator számára adaptálva:
a typesafe-sdk 0.7.x `system_one(state=..., questions=...)` hívási alakjára
(a lab `document=...` paraméterezése helyett).

A formátum kompatibilis maradt: {request_hash, source, model, response} JSONL sorok,
a request_hash kanonikus (kulcssorrend-független) SHA-256.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


def _json_safe(value: Any) -> Any:
    """SDK-struktúrákat és namespace-eket stabil JSON-adattá alakít."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_safe(model_dump())
    if isinstance(value, SimpleNamespace):
        return {key: _json_safe(item) for key, item in vars(value).items()}
    return {"__opaque__": type(value).__name__, "repr": repr(value)}


def canonical_request_hash(request: Mapping[str, Any]) -> str:
    """Kanonikus, kulcssorrend-független SHA-256 hash a kérésre."""
    payload = json.dumps(
        _json_safe(request), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def system_one_request_hash(
    state: Mapping[str, Any],
    questions: Mapping[str, Any],
    *,
    model: str | None,
) -> str:
    """A teljes system_one kérés hashe, a választott modellel együtt."""
    return canonical_request_hash({"state": state, "questions": questions, "model": model})


def response_to_payload(value: Any) -> Any:
    """SDK pydantic válasz vagy replay-namespace → stabil JSON-payload."""
    return _json_safe(value)


def payload_to_namespace(value: Any, *, root: bool = True) -> Any:
    """JSON-payload → namespace-fa (a typesafe_sdk válaszának attribútum-alakja).

    A `model`/`usage`/`answers` szintek SimpleNamespace-k, az `answers` alatt
    dict marad (question-név → answer-namespace), a `probabilities` szintén dict.
    """
    if isinstance(value, dict):
        if root and "answers" in value:
            ns = {k: payload_to_namespace(v, root=False) for k, v in value.items()}
            ns["answers"] = {
                qname: SimpleNamespace(**{
                    k: payload_to_namespace(v, root=False) for k, v in ans.items()
                })
                for qname, ans in value["answers"].items()
            }
            return SimpleNamespace(**ns)
        return {k: payload_to_namespace(v, root=False) for k, v in value.items()}
    if isinstance(value, list):
        return [payload_to_namespace(item, root=False) for item in value]
    return value


def load_replay_index(path: str | Path) -> dict[str, Mapping[str, Any]]:
    """JSONL replay-fixture betöltése; a duplikált request_hasht elutasítja."""
    index: dict[str, Mapping[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            request_hash = row.get("request_hash")
            response = row.get("response")
            if not isinstance(request_hash, str) or not isinstance(response, dict):
                raise ValueError(f"Érvénytelen replay sor: {path}:{line_number}")
            if request_hash in index:
                raise ValueError(
                    f"Duplikált replay request hash: {path}:{line_number}: {request_hash}"
                )
            index[request_hash] = response
    return index


class ReplayClient:
    """Fail-closed system_one client rögzített válaszokból (SC-004 replay).

    Ismeretlen request hash esetén KeyError-t dob — replay módban SOHA nem
    gyárt döntést élő hívás nélkül.
    """

    def __init__(self, responses_by_hash: Mapping[str, Mapping[str, Any]]) -> None:
        self._responses_by_hash = dict(responses_by_hash)

    def system_one(
        self,
        state: Mapping[str, Any],
        questions: Mapping[str, Any],
        *,
        model: str | None = None,
        **_kwargs: Any,
    ) -> Any:
        request_hash = system_one_request_hash(state, questions, model=model)
        try:
            payload = self._responses_by_hash[request_hash]
        except KeyError as exc:
            raise KeyError(
                f"Nincs replay-válasz a request hash-re: {request_hash}; "
                "replay módban nem fabrikálunk döntést"
            ) from exc
        return payload_to_namespace({k: v for k, v in payload.items() if k != "latency_ms"})
