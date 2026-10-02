"""eval/context_calibration_016.py — spec 016 T011: ReAnchor-kalibráció a
hide-küszöbre, ASZIMMETRIKUS metrikával (kiinduló 5:1, plan KD4).

A 015-ös minta két része egyben:
  - `reanchor`: ReAnchor a T010 címkézett mintán, EVAL-ONLY wrapperen
    (a wrapper TÜKRÖZI a context_selection.py Score-hívását, de NEM a
    production út — a production közvetlen SDK marad). EXPLORATÍV.
  - `capture` + `report`: a production _score_piece-szel AZONOS probe a
    címkézett darabokon → nyers (score, confidence) párok → TISZTA replay
    threshold-sweep aszimmetrikus költséggel + érzékenység-analízis
    (3:1, 5:1, 10:1). A „küszöb marad" ág is fájlba írt eredmény.

A safety floor NEM kalibrálható: a sweep CSAK a hide_below-t mozgatja —
a min_confidence (fail-open=show) és az FR-004 story-core szabály fix.

GEPA TILOS dev-módban — a ReAnchor reflection-mentes kalibráció, ez megengedett.

Futtatás:
    python -m eval.context_calibration_016 capture    # élő (TYPESAFE_API_KEY)
    python -m eval.context_calibration_016 reanchor   # élő (TYPESAFE_API_KEY)
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

PINNED_MODEL = "jev-1.13.0"  # a config context_selection.model-jével azonos
CURRENT_HIDE_BELOW = 0.25     # a config jelenlegi értéke (a sweep exploratív)
CURRENT_SUMMARIZE_BELOW = 0.60
CURRENT_MIN_CONFIDENCE = 0.6  # safety floor — NEM kalibrálható

BASE_RATIO = 5   # kiinduló aszimmetrikus arány (plan KD4)
SWEEP_THRESHOLDS = [round(t / 20, 2) for t in range(0, 21)]  # 0.00..1.00


# ---------------------------------------------------------------------------
# A production policy TISZTA mása (context_selection.py, küszöb-paraméteresen)
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
    """Az aszimmetrikus költség (plan KD4): a releváns darab elrejtése
    (recall-hiba) `ratio`-szor drágább, mint a zaj mutatása (precízió-hiba).
    A summarize a relevánsnál félköltség (a lényeg megmarad, de nem
    változatlanul), a zaj-nál is félköltség (summarizer-hívás + maradék zaj).
    """
    if truth == "relevant":
        return {"hide": ratio, "summarize": 0.5, "show": 0.0}[verdict]
    if truth == "noise":
        return {"hide": 0.0, "summarize": 0.5, "show": 1.0}[verdict]
    # borderline: a summarize az ideális, mindkét szélsőség enyhe hiba
    return {"hide": 1.0, "summarize": 0.0, "show": 1.0}[verdict]


# ---------------------------------------------------------------------------
# capture: nyers (score, confidence) probék a címkézett darabokon (élő)
# ---------------------------------------------------------------------------

def cmd_capture() -> None:
    import os

    from dotenv import load_dotenv

    load_dotenv()
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY kell a capture-höz")

    from typesafe_sdk import Score, TypeSafeClient

    from snow_kb.context_selection import RELEVANCE_CRITERIA, RELEVANCE_QUESTION

    labeled = json.loads(LABELED_PATH.read_text(encoding="utf-8"))["examples"]
    client = TypeSafeClient()

    rows = []
    for item in labeled:
        state = {
            "story_context": "",  # a címkézett minta darabjai önmagukban állnak
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
            print(f"  HIBA {item['piece_id']}: {type(exc).__name__}: {exc}", flush=True)
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
    print(f"Kalibrációs capture: {CAPTURE_PATH} ({len(rows)} darab)")


# ---------------------------------------------------------------------------
# reanchor: ReAnchor az eval-only wrapperen (EXPLORATÍV, a 015 minta)
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
        """Negált aszimmetrikus költség a JELENLEGI küszöbökkel (a ReAnchor
        MAXIMALIZÁL) — a küszöb-sweep a report-ban, tiszta replayből."""
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
    print(f"kalibrálatlan: aszimmetrikus score={before:.3f} ({len(trainset)} darab)")

    optimizer = ReAnchor(metric, num_threads=2,
                         log_dir="artifacts/reanchor_logs_016")
    calibrated = optimizer.compile(wrapper, trainset=trainset)
    after = run(calibrated, trainset, metric, num_threads=2)
    print(f"kalibrált:     aszimmetrikus score={after:.3f}")

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
            "A fitted paraméterek EXPLORATÍVAK — a threshold-döntés a "
            "context_calibration_report_016.json sweep-jében, és CSAK a T012 "
            "MANUÁLIS KAPU jóváhagyása után kerülhet a configba. A safety "
            "floor (min_confidence, fail-open=show, FR-004) NEM kalibrált."
        ),
    }
    REANCHOR_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"ReAnchor-riport: {REANCHOR_REPORT}")


# ---------------------------------------------------------------------------
# report: TISZTA replay sweep + döntés + érzékenység-analízis
# ---------------------------------------------------------------------------

def _costs_at(rows: list[dict], hide_below: float, ratio: float) -> dict:
    total = 0.0
    per_label = {"relevant": 0.0, "noise": 0.0, "borderline": 0.0}
    errors = []
    for row in rows:
        if row["score"] is None:
            continue  # probe-hiba: fail-open show → költség a valóságban is show
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
    # a legjobb jelölt az 5:1 szerint, de csak akkor nyerhet, ha 3:1-nél és
    # 10:1-nél sem rosszabb a jelenleginél (a 015-ös ratio-érzékeny szabály)
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
            f"a {best['hide_below']} jelölt szigorúan jobb 5:1-nél "
            f"({current['total']} → {best['cost_5to1']}), és nem rosszabb "
            f"3:1-nél ({current_c3} → {best_c3}) és 10:1-nél ({current_c10} → "
            f"{best_c10}) sem. EXPLORATÍV — a config CSAK a T012 MANUÁLIS KAPU "
            "jóváhagyásával módosul."
        )
    else:
        decision = "marad"
        proposed = CURRENT_HIDE_BELOW
        rationale = (
            f"a sweep nem talált szigorúan jobb küszöböt: a jelenlegi "
            f"{CURRENT_HIDE_BELOW} költsége 5:1-nél {current['total']}; a "
            f"legjobb jelölt ({best['hide_below']}: {best['cost_5to1']}) nem "
            "teljesíti a szigorú javulás + ratio-érzéketlenség feltételét. "
            "A küszöb marad — ez NEM csendes maradás, a sweep bizonyíték "
            "a sweep táblában."
        )

    report = {
        "spec": "016-context-selection / T011 kalibrációs riport",
        "model": PINNED_MODEL,
        "n_labeled": n,
        "base_ratio": "5:1 (releváns elrejtése : zaj mutatása)",
        "safety_floor": {
            "min_confidence": CURRENT_MIN_CONFIDENCE,
            "fail_open": "show",
            "story_core_never_hide": True,
            "note": "a safety floor NEM kalibrált — a sweep CSAK a hide_below-t mozgatta",
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
            "A sweep EXPLORATÍV — a legjobb sweep-sor NEM confirmatory eredmény.",
            "A riport TISZTA replay a capture-fájlból — kétszeri futtatás "
            "byte-identikus.",
            "A config-módosítás CSAK a T012 MANUÁLIS KAPU után történhet.",
        ],
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Kalibrációs riport: {REPORT_PATH}")
    print(f"  döntés: {decision} (jelenlegi {CURRENT_HIDE_BELOW}, "
          f"jelölt {proposed}, költség {current['total']} → {best['cost_5to1']})")


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
