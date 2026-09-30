"""jev_replay.py — a vendored record/replay helper based on the jev-dspy-lab pattern.

Source: https://github.com/jmanhype/jev-dspy-lab (MIT License),
src/jev_dspy_lab/replay.py — adapted for snow_kb_generator:
to the call shape of the typesafe-sdk 0.7.x `system_one(state=..., questions=...)`
(instead of the lab's `document=...` parameterization).

The format stayed compatible: {request_hash, source, model, response} JSONL lines,
the request_hash is a canonical (key order independent) SHA-256.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


def _json_safe(value: Any) -> Any:
    """Turns SDK structures and namespaces into stable JSON data."""
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
    """A canonical, key order independent SHA-256 hash of the request."""
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
    """The hash of the full system_one request, together with the chosen model."""
    return canonical_request_hash({"state": state, "questions": questions, "model": model})


def response_to_payload(value: Any) -> Any:
    """An SDK pydantic response or a replay namespace → a stable JSON payload."""
    return _json_safe(value)


def payload_to_namespace(value: Any, *, root: bool = True) -> Any:
    """A JSON payload → namespace tree (the attribute shape of the typesafe_sdk response).

    A `model`/`usage`/`answers` szintek SimpleNamespace-k, az `answers` alatt
    stays a dict (question name → answer namespace), `probabilities` is a dict as well.
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
    """Loads a JSONL replay fixture; it rejects a duplicated request_hash."""
    index: dict[str, Mapping[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            request_hash = row.get("request_hash")
            response = row.get("response")
            if not isinstance(request_hash, str) or not isinstance(response, dict):
                raise ValueError(f"Invalid replay line: {path}:{line_number}")
            if request_hash in index:
                raise ValueError(
                    f"Duplicated replay request hash: {path}:{line_number}: {request_hash}"
                )
            index[request_hash] = response
    return index


class ReplayClient:
    """A fail-closed system_one client from the recorded responses (SC-004 replay).

    For an unknown request hash it raises a KeyError — in replay mode it NEVER
    fabricates a decision without a live call.
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
                f"No replay response for the request hash: {request_hash}; "
                "in replay mode we do not fabricate a decision"
            ) from exc
        return payload_to_namespace({k: v for k, v in payload.items() if k != "latency_ms"})
