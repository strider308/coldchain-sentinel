from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import html
import json
import math
import random
from typing import Any, Callable

SEED = 260606
MODEL_VERSION = "sers-synthetic-linear-v2.0.0"
SYNTHETIC_TRAIN_ROWS = 420
SYNTHETIC_TEST_ROWS = 180
WINDOW_MINUTES = 60
READINGS_PER_WINDOW = 12

LABELS = (
    "breachWithinNext30Minutes",
    "unresolvedMappingRisk",
    "falseSpikeLikely",
)

FEATURES = (
    "currentTempC",
    "rollingAvgTempC",
    "maxTempC",
    "slopeCPerHour",
    "minutesAbove8C",
    "doorOpenRatio",
    "shockFlagRatio",
    "dropoutRatio",
    "weakSignalRatio",
    "singleSensorSpikeScore",
    "unresolvedMappingFlag",
    "neighborAgreementScore",
    "zoneConsensusScore",
)

FAILURE_MODES = (
    "no_excursion_control",
    "slow_warming_excursion",
    "door_left_open_warming",
    "early_warning_slope",
    "false_single_sensor_spike",
    "unresolved_mapping_risk",
    "dropout_weak_signal_noise",
)


@dataclass(frozen=True)
class LinearModel:
    label: str
    threshold: float
    weights: dict[str, float]
    means: dict[str, float]
    stdevs: dict[str, float]

    def score(self, row: dict[str, Any]) -> float:
        total = 0.0
        for feature, weight in self.weights.items():
            stdev = self.stdevs.get(feature, 1.0) or 1.0
            total += weight * ((float(row[feature]) - self.means[feature]) / stdev)
        return total

    def predict(self, row: dict[str, Any]) -> bool:
        return self.score(row) >= self.threshold


def _round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def _safe_div(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _mean(values: list[float]) -> float:
    return _safe_div(sum(values), len(values))


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    mean = _mean(values)
    variance = _safe_div(sum((value - mean) ** 2 for value in values), len(values))
    return math.sqrt(variance) or 1.0


def _line(start: float, end: float, rng: random.Random, noise: float = 0.18) -> list[float]:
    return [
        start + (end - start) * (index / (READINGS_PER_WINDOW - 1)) + rng.uniform(-noise, noise)
        for index in range(READINGS_PER_WINDOW)
    ]


def _generate_row(index: int, rng: random.Random) -> dict[str, Any]:
    mode = FAILURE_MODES[index % len(FAILURE_MODES)]
    base = rng.uniform(3.0, 5.6)

    door_open_ratio = 0.0
    shock_flag_ratio = 0.0
    dropout_ratio = 0.0
    weak_signal_ratio = rng.uniform(0.0, 0.15)
    single_sensor_spike_score = 0.0
    unresolved_mapping_flag = 0.0
    neighbor_agreement_score = rng.uniform(0.78, 0.97)
    zone_consensus_score = rng.uniform(0.76, 0.96)

    if mode == "no_excursion_control":
        readings = _line(base, base + rng.uniform(-0.3, 0.4), rng)
    elif mode == "slow_warming_excursion":
        readings = _line(base + rng.uniform(0.2, 1.0), rng.uniform(8.6, 10.5), rng)
        neighbor_agreement_score = rng.uniform(0.76, 0.93)
        zone_consensus_score = rng.uniform(0.74, 0.91)
    elif mode == "door_left_open_warming":
        readings = _line(base, rng.uniform(7.8, 9.7), rng)
        door_open_ratio = rng.uniform(0.35, 0.75)
        neighbor_agreement_score = rng.uniform(0.71, 0.9)
        zone_consensus_score = rng.uniform(0.69, 0.88)
    elif mode == "early_warning_slope":
        readings = _line(base + rng.uniform(0.0, 0.6), rng.uniform(7.1, 7.9), rng, noise=0.12)
        neighbor_agreement_score = rng.uniform(0.82, 0.97)
        zone_consensus_score = rng.uniform(0.8, 0.95)
    elif mode == "false_single_sensor_spike":
        readings = _line(base, base + rng.uniform(-0.2, 0.3), rng, noise=0.13)
        readings[rng.randrange(READINGS_PER_WINDOW)] = rng.uniform(9.0, 12.0)
        single_sensor_spike_score = rng.uniform(0.82, 1.0)
        neighbor_agreement_score = rng.uniform(0.15, 0.42)
        zone_consensus_score = rng.uniform(0.18, 0.48)
    elif mode == "unresolved_mapping_risk":
        readings = _line(base, base + rng.uniform(-0.2, 0.3), rng, noise=0.12)
        unresolved_mapping_flag = 1.0
        dropout_ratio = rng.uniform(0.05, 0.22)
        weak_signal_ratio = rng.uniform(0.12, 0.35)
    else:
        readings = _line(base, base + rng.uniform(-0.1, 0.6), rng, noise=0.5)
        dropout_ratio = rng.uniform(0.28, 0.55)
        weak_signal_ratio = rng.uniform(0.42, 0.82)
        shock_flag_ratio = rng.uniform(0.0, 0.2)
        neighbor_agreement_score = rng.uniform(0.45, 0.7)
        zone_consensus_score = rng.uniform(0.42, 0.68)

    labels = {
        "breachWithinNext30Minutes": mode in {
            "slow_warming_excursion",
            "door_left_open_warming",
            "early_warning_slope",
        },
        "unresolvedMappingRisk": mode == "unresolved_mapping_risk",
        "falseSpikeLikely": mode == "false_single_sensor_spike",
    }

    return {
        "syntheticWindowId": f"syn-window-{index + 1:04d}",
        "failureMode": mode,
        "currentTempC": _round(readings[-1], 3),
        "rollingAvgTempC": _round(_mean(readings[-6:]), 3),
        "maxTempC": _round(max(readings), 3),
        "slopeCPerHour": _round(readings[-1] - readings[0], 3),
        "minutesAbove8C": sum(1 for value in readings if value >= 8.0) * 5,
        "doorOpenRatio": _round(door_open_ratio, 3),
        "shockFlagRatio": _round(shock_flag_ratio, 3),
        "dropoutRatio": _round(dropout_ratio, 3),
        "weakSignalRatio": _round(weak_signal_ratio, 3),
        "singleSensorSpikeScore": _round(single_sensor_spike_score, 3),
        "unresolvedMappingFlag": _round(unresolved_mapping_flag, 3),
        "neighborAgreementScore": _round(neighbor_agreement_score, 3),
        "zoneConsensusScore": _round(zone_consensus_score, 3),
        "labels": labels,
    }


def _generate_dataset() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(SEED)
    rows = [_generate_row(index, rng) for index in range(SYNTHETIC_TRAIN_ROWS + SYNTHETIC_TEST_ROWS)]
    return rows[:SYNTHETIC_TRAIN_ROWS], rows[SYNTHETIC_TRAIN_ROWS:]


def _metrics(*, tp: int, fp: int, tn: int, fn: int) -> dict[str, Any]:
    total = tp + fp + tn + fn
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return {
        "accuracy": _round(_safe_div(tp + tn, total), 4),
        "precision": _round(precision, 4),
        "recall": _round(recall, 4),
        "f1": _round(_safe_div(2 * precision * recall, precision + recall), 4),
        "falsePositives": fp,
        "falseNegatives": fn,
        "confusionMatrix": {
            "truePositive": tp,
            "falsePositive": fp,
            "trueNegative": tn,
            "falseNegative": fn,
        },
    }


def _evaluate_scores(scored_labels: list[tuple[float, bool]], threshold: float) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for score, actual in scored_labels:
        predicted = score >= threshold
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and not actual:
            tn += 1
        else:
            fn += 1
    return _metrics(tp=tp, fp=fp, tn=tn, fn=fn)


def _train_linear_model(rows: list[dict[str, Any]], label: str) -> LinearModel:
    means = {feature: _mean([float(row[feature]) for row in rows]) for feature in FEATURES}
    stdevs = {feature: _stdev([float(row[feature]) for row in rows]) for feature in FEATURES}
    positives = [row for row in rows if bool(row["labels"][label])]
    negatives = [row for row in rows if not bool(row["labels"][label])]

    weights: dict[str, float] = {}
    for feature in FEATURES:
        pos_values = [(float(row[feature]) - means[feature]) / stdevs[feature] for row in positives]
        neg_values = [(float(row[feature]) - means[feature]) / stdevs[feature] for row in negatives]
        weights[feature] = _round(_mean(pos_values) - _mean(neg_values), 5)

    provisional = LinearModel(label=label, threshold=0.0, weights=weights, means=means, stdevs=stdevs)
    scored = sorted((provisional.score(row), bool(row["labels"][label])) for row in rows)
    candidates = [score for score, _ in scored]
    candidates.extend((scored[i][0] + scored[i + 1][0]) / 2 for i in range(len(scored) - 1))

    best_threshold = 0.0
    best_key = (-1.0, -1.0, -1.0)
    for threshold in candidates:
        metric = _evaluate_scores(scored, threshold)
        key = (metric["f1"], metric["recall"], metric["precision"])
        if key > best_key:
            best_key = key
            best_threshold = threshold

    return LinearModel(
        label=label,
        threshold=_round(best_threshold, 5),
        weights=weights,
        means={key: _round(value, 5) for key, value in means.items()},
        stdevs={key: _round(value, 5) for key, value in stdevs.items()},
    )


def _evaluate_model(model: LinearModel, rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for row in rows:
        predicted = model.predict(row)
        actual = bool(row["labels"][model.label])
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and not actual:
            tn += 1
        else:
            fn += 1
    metric = _metrics(tp=tp, fp=fp, tn=tn, fn=fn)
    metric["threshold"] = model.threshold
    return metric


def _baseline_predictions(rows: list[dict[str, Any]], predictor: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for row in rows:
        predicted = predictor(row)
        actual = bool(row["labels"]["breachWithinNext30Minutes"])
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and not actual:
            tn += 1
        else:
            fn += 1
    return _metrics(tp=tp, fp=fp, tn=tn, fn=fn)


def _build_payload() -> dict[str, Any]:
    train_rows, test_rows = _generate_dataset()
    models = {label: _train_linear_model(train_rows, label) for label in LABELS}

    label_metrics = {
        label: {
            "train": _evaluate_model(models[label], train_rows),
            "test": _evaluate_model(models[label], test_rows),
        }
        for label in LABELS
    }

    baselines = {
        "current-temperature threshold": _baseline_predictions(
            test_rows, lambda row: float(row["currentTempC"]) >= 8.0
        ),
        "rolling-average threshold": _baseline_predictions(
            test_rows, lambda row: float(row["rollingAvgTempC"]) >= 8.0
        ),
        "last-N-minutes max threshold": _baseline_predictions(
            test_rows, lambda row: float(row["maxTempC"]) >= 8.5
        ),
        "simple slope rule": _baseline_predictions(
            test_rows,
            lambda row: float(row["slopeCPerHour"]) >= 2.5 and float(row["currentTempC"]) >= 7.0,
        ),
    }

    sers_metric = label_metrics["breachWithinNext30Minutes"]["test"]
    best_baseline_accuracy = max(metric["accuracy"] for metric in baselines.values())

    return {
        "phase": "Phase 6 - Synthetic Training and Benchmark Lab",
        "claimsBoundary": {
            "dataScope": "deterministic synthetic sensor windows only",
            "decisionScope": "advisory model benchmark only",
            "hardwareScope": "no hardware acceleration claim is made by this lab endpoint",
            "allowedClaim": "On deterministic synthetic benchmark data, SERS outperforms simple baselines.",
        },
        "trainingPipeline": [
            "Generate deterministic synthetic sensor windows.",
            "Inject known failure modes.",
            "Create advisory labels for breachWithinNext30Minutes, unresolvedMappingRisk, and falseSpikeLikely.",
            "Train a dependency-free linear scoring model.",
            "Compare against simple deterministic baselines.",
            "Export repeatable synthetic metrics.",
        ],
        "dataset": {
            "seed": SEED,
            "syntheticTrainRows": SYNTHETIC_TRAIN_ROWS,
            "syntheticTestRows": SYNTHETIC_TEST_ROWS,
            "windowMinutes": WINDOW_MINUTES,
            "readingsPerWindow": READINGS_PER_WINDOW,
            "failureModes": list(FAILURE_MODES),
            "labels": list(LABELS),
            "sampleRows": test_rows[:5],
        },
        "model": {
            "name": "SERS dependency-free synthetic linear scorer",
            "version": MODEL_VERSION,
            "authoritativeDecisionLayer": "deterministic rules remain authoritative",
            "advisoryUseOnly": True,
            "features": list(FEATURES),
            "labelModels": {
                label: {
                    "threshold": models[label].threshold,
                    "weights": models[label].weights,
                }
                for label in LABELS
            },
        },
        "metrics": {
            "labels": label_metrics,
            "benchmarkComparison": {
                "SERS synthetic scorer": sers_metric,
                **baselines,
            },
            "sersBeatsAllBaselinesOnAccuracy": sers_metric["accuracy"] > best_baseline_accuracy,
        },
    }


@lru_cache(maxsize=1)
def get_training_lab_payload() -> dict[str, Any]:
    return _build_payload()


def get_model_benchmark_v2_payload() -> dict[str, Any]:
    payload = get_training_lab_payload()
    return {
        "phase": payload["phase"],
        "claimsBoundary": payload["claimsBoundary"],
        "modelVersion": payload["model"]["version"],
        "seed": payload["dataset"]["seed"],
        "syntheticTrainRows": payload["dataset"]["syntheticTrainRows"],
        "syntheticTestRows": payload["dataset"]["syntheticTestRows"],
        "metrics": payload["metrics"]["benchmarkComparison"],
        "sersBeatsAllBaselinesOnAccuracy": payload["metrics"]["sersBeatsAllBaselinesOnAccuracy"],
    }


def get_model_card_payload() -> dict[str, Any]:
    payload = get_training_lab_payload()
    return {
        "modelName": payload["model"]["name"],
        "modelVersion": payload["model"]["version"],
        "modelType": "dependency-free synthetic linear scorer",
        "intendedUse": [
            "synthetic benchmark discipline",
            "advisory risk explanation support",
            "human review prioritization support",
        ],
        "outOfScope": [
            "real data performance claims",
            "external comparison claims",
            "regulatory signoff",
            "automated operational actions",
        ],
        "data": payload["claimsBoundary"]["dataScope"],
        "labels": payload["dataset"]["labels"],
        "features": payload["model"]["features"],
        "metrics": payload["metrics"]["labels"],
        "allowedClaim": payload["claimsBoundary"]["allowedClaim"],
        "safetyControls": [
            "deterministic rules remain authoritative",
            "SERS remains advisory-only",
            "Fireworks remains optional and safety-gated",
            "synthetic data only",
        ],
    }


def _json_script(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def _page(title: str, summary: str, payload: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #071014; color: #eef7f2; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }}
    .card {{ background: #102129; border: 1px solid #21414d; border-radius: 18px; padding: 20px; margin: 18px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
    .metric {{ background: #0b171d; border: 1px solid #1c3944; border-radius: 14px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 1.65rem; }}
    code, pre {{ white-space: pre-wrap; word-break: break-word; }}
    pre {{ background: #071014; border: 1px solid #21414d; border-radius: 14px; padding: 16px; overflow-x: auto; }}
    a {{ color: #96e6b3; }}
  </style>
</head>
<body>
<main>
  <p><a href="/">ColdChain Sentinel</a></p>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(summary)}</p>
  <section class="card">
    <h2>Claims boundary</h2>
    <div class="grid">
      <div class="metric"><span>Data scope</span><strong>Synthetic</strong></div>
      <div class="metric"><span>Decision scope</span><strong>Advisory</strong></div>
      <div class="metric"><span>Rules layer</span><strong>Authoritative</strong></div>
    </div>
  </section>
  <section class="card">
    <h2>Machine-readable payload</h2>
    <pre>{_json_script(payload)}</pre>
  </section>
</main>
</body>
</html>"""


def render_training_lab_html() -> str:
    payload = get_training_lab_payload()
    return _page(
        "Synthetic Training and Benchmark Lab",
        "Dependency-free synthetic training pipeline with known failure modes, advisory labels, and repeatable benchmark metrics.",
        payload,
    )


def render_model_benchmark_v2_html() -> str:
    payload = get_model_benchmark_v2_payload()
    return _page(
        "Model Benchmark v2",
        "Synthetic benchmark comparison between SERS and simple deterministic baselines.",
        payload,
    )


def render_model_card_html() -> str:
    payload = get_model_card_payload()
    return _page(
        "SERS Synthetic Model Card",
        "Synthetic-only model card for the advisory SERS benchmark model.",
        payload,
    )