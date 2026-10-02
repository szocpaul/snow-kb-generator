"""eval/context_calibration_016.py — spec 016 T011: the ReAnchor calibration for the
hide threshold, with the ASYMMETRIC metric (starting from 5:1, plan KD4).

Both parts of the 015 sample in one:
  - `reanchor`: ReAnchor on the T010 labelled sample, on an EVAL-ONLY wrapper
    (the wrapper MIRRORS the Score call of context_selection.py, but NOT the
    production path — the production stays a direct SDK call). EXPLORATORY.
  - `capture` + `report`: a production _score_piece-szel AZONOS probe a
    labelled pieces → raw (score, confidence) pairs → a PURE replay
    threshold sweep with the asymmetric cost + a sensitivity analysis
    (3:1, 5:1, 10:1). The "the threshold stays" branch is a written result as well.

The safety floor is NOT calibratable: the sweep moves ONLY the hide_below —
the min_confidence (fail-open=show) and the FR-004 story-core rule are fixed.

GEPA is FORBIDDEN in dev mode — the ReAnchor calibration without reflection is allowed.

Run:
    python -m eval.context_calibration_016 capture    # live (TYPESAFE_API_KEY)
    python -m eval.context_calibration_016 reanchor   # live (TYPESAFE_API_KEY)
    python -m eval.context_calibration_016 report     # TISZTA replay

Kimenetek:
    artifacts/context_calibration_capture_016.json
    artifacts/context_reanchor_report_016.json
    artifacts/context_calibration_report_016.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LABELED_PATH = Path("data/examples/context_labeled_016.json")
CAPTURE_PATH = Path("artifacts/context_calibration_capture_016.json")
REANCHOR_REPORT = Path("artifacts/context_reanchor_report_016.json")
REPORT_PATH = Path("artifacts/context_calibration_report_016.json")

PINNED_MODEL = "jev-1.13.0"  # the same as the context_selection.model in the config
CURRENT_HIDE_BELOW = 0.25     # the current value in the config (the sweep is exploratory)
CURRENT_SUMMARIZE_BELOW = 0.60
CURRENT_MIN_CONFIDENCE = 0.6  # the safety floor — NOT calibratable

BASE_RATIO = 5   # the starting asymmetric ratio (plan KD4)
SWEEP_THRESHOLDS = [round(t / 20, 2) for t in range(0, 21)]  # 0.00..1.00


# ---------------------------------------------------------------------------
# A PURE copy of the production policy (context_selection.py, with threshold parameters)
# ---------------------------------------------------------------------------

def verdict_at(relevance: float, confidence: float, hide_below: float,
               summarize_below: float = CURRENT_SUMMARIZE_BELOW,
               min_confidence: float = CURRENT_MIN_CONFIDENCE) -> str:
    eps = 1e-9
    if confidence < min_confidence + eps:
        return "show"
    if relevance < hide_below:
        return "hide"
    if relevance < summarize_below:
        return "summarize"
    return "show"


def asymmetric_cost(truth: str, verdict: str, ratio: float) -> float:
    """The asymmetric cost (plan KD4): hiding a relevant piece
    (a recall error) is `ratio` times more expensive than showing the noise (a precision error).
    For a relevant piece the summarize is half the cost (the essence survives, but not
    unchanged), and for noise it is also half the cost (the summarizer call + the remaining noise).
    """
    if truth == "relevant":
        return {"hide": ratio, "summarize": 0.5, "show": 0.0}[verdict]
    if truth == "noise":
        return {"hide": 0.0, "summarize": 0.5, "show": 1.0}[verdict]
    # borderline: the summarize is ideal, both extremes are a mild error
    return {"hide": 1.0, "summarize": 0.0, "show": 1.0}[verdict]


# ---------------------------------------------------------------------------
# capture: the raw (score, confidence) probes on the labelled pieces (live)
# ---------------------------------------------------------------------------

def cmd_capture() -> None:
    import os

    from dotenv import load_dotenv

    load_dotenv()
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is required for the capture")

    from typesafe_sdk import Score, TypeSafeClient

    from snow_kb.context_selection import RELEVANCE_CRITERIA, RELEVANCE_QUESTION

    labeled = json.loads(LABELED_PATH.read_text(encoding="utf-8"))["examples"]
    client = TypeSafeClient()

    rows = []
    for item in labeled:
        state = {
            "story_context": "",  # the pieces of the labelled sample stand on their own
            "piece_type": item["source_type"],
            "piece_label": item["label_text"],
            "piece": item["text"][:6000],
        }
        questions = {"relevance": Score(
            instructions=RELEVANCE_QUESTION, criteria=list(RELEVANCE_CRITERIA))}
        try:
            response = client.system_one(state=state, questions=questions,
                                         model=PINNED_MODEL)
            answer = response.answers["relevance"]
            score = float(answer.score)
            confidence = float(answer.confidence)
        except Exception as exc:  # noqa: BLE001
            score, confidence = None, None
            print(f"  ERROR {item['piece_id']}: {type(exc).__name__}: {exc}", flush=True)
        rows.append({
            "example_id": item["example_id"],
            "piece_id": item["piece_id"],
            "source_type": item["source_type"],
            "label": item["label"],
            "label_note": item["label_note"],
            "score": score,
            "confidence": confidence,
        })
        print(f"  {item['piece_id']}: score={score} conf={confidence} "
              f"(truth={item['label']})", flush=True)

    doc = {"capture": "calibration-probes", "model": PINNED_MODEL,
           "n_labeled": len(rows), "rows": rows}
    CAPTURE_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
    print(f"Calibration capture: {CAPTURE_PATH} ({len(rows)} pieces)")


# ---------------------------------------------------------------------------
# reanchor: ReAnchor on the eval-only wrapper (EXPLORATORY, the 015 pattern)
# ---------------------------------------------------------------------------

def cmd_reanchor() -> None:
    import dspy
    from dspy.experimental import ReAnchor, Score as DspyScore, TypeSafe
    from typing_extensions import Annotated

    from snow_kb.context_selection import RELEVANCE_CRITERIA, RELEVANCE_QUESTION

    class RelevanceDecisionEval016(dspy.Signature):
        """Score how much of a context piece matters for writing the KB article (eval-only mirror, spec 016)."""

        piece_type: str = dspy.InputField(desc="The context piece source type.")
        piece_label: str = dspy.InputField(desc="The context piece label.")
        piece: str = dspy.InputField(desc="The context piece text.")
        relevance: DspyScore[RELEVANCE_CRITERIA] = dspy.OutputField(
            desc=RELEVANCE_QUESTION)

    def metric(example, pred) -> float:
        """The negated asymmetric cost with the CURRENT thresholds (the ReAnchor
        MAXIMIZES it) — the threshold sweep is in the report, from a pure replay."""
        relevance = float(pred.relevance) / 2.0  # 3 szint → [0,1]
        confidence = float(getattr(pred.relevance, "confidence", 1.0) or 1.0)
        verdict = verdict_at(relevance, confidence, CURRENT_HIDE_BELOW)
        return -asymmetric_cost(example.truth, verdict, BASE_RATIO)

    labeled = json.loads(LABELED_PATH.read_text(encoding="utf-8"))["examples"]
    trainset = [
        dspy.Example(
            piece_type=item["source_type"],
            piece_label=item["label_text"],
            piece=item["text"][:6000],
            truth=item["label"],
        ).with_inputs("piece_type", "piece_label", "piece")
        for item in labeled
    ]

    lm = TypeSafe(model=PINNED_MODEL, cache=True)
    dspy.configure(lm=lm)
    wrapper = dspy.Predict(RelevanceDecisionEval016)

    from dspy.teleprompt.reanchor.calibrate import run

    before = run(wrapper, trainset, metric, num_threads=2)
    print(f"uncalibrated: asymmetric score={before:.3f} ({len(trainset)} pieces)")

    optimizer = ReAnchor(metric, num_threads=2,
                         log_dir="artifacts/reanchor_logs_016")
    calibrated = optimizer.compile(wrapper, trainset=trainset)
    after = run(calibrated, trainset, metric, num_threads=2)
    print(f"calibrated:     asymmetric score={after:.3f}")

    fitted_fields = {
        name: dict(p.fields)
        for name, p in calibrated.named_parameters()
        if isinstance(p, dspy.Predict) and p.fields
    }
    report = {
        "spec": "016-context-selection / T011 ReAnchor (aszimmetrikus, eval-only)",
        "model": PINNED_MODEL,
        "n_train": len(trainset),
        "asymmetric_score_before": before,
        "asymmetric_score_after": after,
        "ratio": BASE_RATIO,
        "fitted_fields": fitted_fields,
        "reanchor_report": optimizer.report,
        "note": (
            "The fitted parameters are EXPLORATORY — the threshold decision is in the "
            "sweep of context_calibration_report_016.json, and it can only go into the config "
            "after the approval of the T012 MANUAL GATE. The safety "
            "floor (min_confidence, fail-open=show, FR-004) is NOT calibrated."
        ),
    }
    REANCHOR_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"ReAnchor-riport: {REANCHOR_REPORT}")


# ---------------------------------------------------------------------------
# report: a PURE replay sweep + the decision + the sensitivity analysis
# ---------------------------------------------------------------------------

def _costs_at(rows: list[dict], hide_below: float, ratio: float) -> dict:
    total = 0.0
    per_label = {"relevant": 0.0, "noise": 0.0, "borderline": 0.0}
    errors = []
    for row in rows:
        if row["score"] is None:
            continue  # probe error: fail-open show → the cost is show in reality as well
        relevance = row["score"] / 2.0
        verdict = verdict_at(relevance, row["confidence"], hide_below)
        cost = asymmetric_cost(row["label"], verdict, ratio)
        total += cost
        per_label[row["label"]] += cost
        if cost > 0:
            errors.append({"piece_id": row["piece_id"], "label": row["label"],
                           "verdict": verdict, "cost": cost,
                           "relevance": round(relevance, 3),
                           "confidence": row["confidence"]})
    return {"total": round(total, 3), "per_label": {k: round(v, 3) for k, v in per_label.items()},
            "errors": errors}


def cmd_report() -> None:
    capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
    rows = capture["rows"]
    n = len(rows)

    sweep = []
    for t in SWEEP_THRESHOLDS:
        point = {"hide_below": t}
        for ratio in (3, 5, 10):
            point[f"cost_{ratio}to1"] = _costs_at(rows, t, ratio)["total"]
        sweep.append(point)

    current = _costs_at(rows, CURRENT_HIDE_BELOW, BASE_RATIO)
    # the best candidate is the best at 5:1, but it can only win if it is not worse at 3:1
    # and 10:1 either than the current one (the ratio-sensitive rule of 015)
    current_c3 = _costs_at(rows, CURRENT_HIDE_BELOW, 3)["total"]
    current_c10 = _costs_at(rows, CURRENT_HIDE_BELOW, 10)["total"]
    best = min(sweep, key=lambda p: p["cost_5to1"])
    best_c3 = _costs_at(rows, best["hide_below"], 3)["total"]
    best_c10 = _costs_at(rows, best["hide_below"], 10)["total"]

    strictly_better = (
        best["cost_5to1"] < current["total"]
        and best_c3 <= current_c3
        and best_c10 <= current_c10
        and best["hide_below"] != CURRENT_HIDE_BELOW
    )
    if strictly_better:
        decision = "valtozik"
        proposed = best["hide_below"]
        rationale = (
            f"the {best['hide_below']} candidate is strictly better at 5:1 "
            f"({current['total']} → {best['cost_5to1']}), and not worse "
            f"at 3:1 ({current_c3} → {best_c3}) and at 10:1 ({current_c10} → "
            f"{best_c10}) either. EXPLORATORY — the config is only changed with the approval of the "
            "T012 MANUAL GATE."
        )
    else:
        decision = "marad"
        proposed = CURRENT_HIDE_BELOW
        rationale = (
            f"the sweep found no strictly better threshold: the current "
            f"{CURRENT_HIDE_BELOW} costs {current['total']} at 5:1; the "
            f"best candidate ({best['hide_below']}: {best['cost_5to1']}) does not "
            "fulfil the strict improvement + ratio insensitivity condition. "
            "The threshold stays — this is NOT a silent stay, the sweep is the evidence "
            "in the sweep table."
        )

    report = {
        "spec": "016-context-selection / T011 calibration report",
        "model": PINNED_MODEL,
        "n_labeled": n,
        "base_ratio": "5:1 (hiding a relevant piece : showing the noise)",
        "safety_floor": {
            "min_confidence": CURRENT_MIN_CONFIDENCE,
            "fail_open": "show",
            "story_core_never_hide": True,
            "note": "the safety floor is NOT calibrated — the sweep only moved the hide_below",
        },
        "current": {"hide_below": CURRENT_HIDE_BELOW,
                    "cost_5to1": current["total"],
                    "per_label": current["per_label"],
                    "errors": current["errors"]},
        "calibration": {
            "decision": decision,
            "proposed_hide_below": proposed,
            "rationale": rationale,
            "exploratory": True,
        },
        "sweep": sweep,
        "sensitivity": {
            "costs_at_current_by_ratio": {
                "3:1": current_c3, "5:1": current["total"], "10:1": current_c10},
            "costs_at_proposed_by_ratio": {
                "3:1": best_c3, "5:1": best["cost_5to1"], "10:1": best_c10},
        },
        "notes": [
            "The sweep is EXPLORATORY — the best sweep row is NOT a confirmatory result.",
            "The report is a PURE replay from the capture file — a double run "
            "byte-identikus.",
            "The config change can happen ONLY after the T012 MANUAL GATE.",
        ],
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Calibration report: {REPORT_PATH}")
    print(f"  decision: {decision} (current {CURRENT_HIDE_BELOW}, "
          f"candidate {proposed}, cost {current['total']} → {best['cost_5to1']})")


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] not in ("capture", "reanchor", "report"):
        print(__doc__)
        sys.exit(2)
    if argv[0] == "capture":
        cmd_capture()
    elif argv[0] == "reanchor":
        cmd_reanchor()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
