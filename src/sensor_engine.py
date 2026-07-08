"""Deterministic high-volume synthetic sensor stream helpers."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Any

DEFAULT_SENSOR_COUNT = 24
DEFAULT_ZONE_COUNT = 4
DEFAULT_HOURS = 48
DEFAULT_INTERVAL_MINUTES = 5
MAX_WINDOW_LIMIT = 500


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sensor_config(case: dict[str, Any]) -> dict[str, Any]:
    first = parse_utc(case["temperatureReadings"][0]["timestampUtc"])
    start = first.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "caseId": case["caseId"],
        "seed": int(hashlib.sha256(case["caseId"].encode("utf-8")).hexdigest()[:8], 16),
        "sensorCount": DEFAULT_SENSOR_COUNT,
        "zoneCount": DEFAULT_ZONE_COUNT,
        "readingIntervalMinutes": DEFAULT_INTERVAL_MINUTES,
        "startUtc": iso_utc(start),
        "endUtc": iso_utc(start + timedelta(hours=DEFAULT_HOURS)),
        "thresholdMaxC": float(case["thresholdMaxC"]),
    }


def zone_ids(config: dict[str, Any]) -> list[str]:
    return [f"Z{index}" for index in range(1, config["zoneCount"] + 1)]


def sensor_zone(sensor_index: int, zones: list[str]) -> str:
    return zones[sensor_index % len(zones)]


def synthetic_readings(case: dict[str, Any]) -> list[dict[str, Any]]:
    config = sensor_config(case)
    rng = random.Random(config["seed"])
    zones = zone_ids(config)
    start = parse_utc(config["startUtc"])
    end = parse_utc(config["endUtc"])
    threshold = config["thresholdMaxC"]
    fixture_excursion = case.get("excursion")
    readings = []
    steps = int((end - start).total_seconds() // 60 // config["readingIntervalMinutes"])
    for sensor_index in range(config["sensorCount"]):
        sensor_id = f"SYN-SENSOR-{sensor_index + 1:03d}"
        zone_id = sensor_zone(sensor_index, zones)
        drift_sensor = sensor_index in (5, 17)
        dropout_sensor = sensor_index in (3, 15)
        for step in range(steps):
            ts = start + timedelta(minutes=step * config["readingIntervalMinutes"])
            humidity = 54 + (sensor_index % 4) * 2 + rng.uniform(-1.5, 1.5)
            battery = max(8.0, 96.0 - (step / steps * 14) - (sensor_index % 7))
            signal = max(12.0, 88.0 - (sensor_index % 6) * 4 + rng.uniform(-3, 3))
            door_open = bool(fixture_excursion and step % 288 in (126, 127) and sensor_index % 8 == 0)
            if dropout_sensor and 36 <= step % 288 <= 38:
                readings.append(reading(ts, sensor_id, zone_id, None, humidity, battery, signal, door_open, step, 35, "SENSOR_DROPOUT", ""))
                continue
            temp = 4.7 + (sensor_index % 5) * 0.18 + rng.uniform(-0.25, 0.25)
            quality = "SENSOR_OK"
            evidence_id = ""
            if fixture_excursion and zone_id == fixture_excursion["zoneId"]:
                exc_start = parse_utc(fixture_excursion["startUtc"])
                exc_end = parse_utc(fixture_excursion["endUtc"])
                if exc_start <= ts < exc_end:
                    temp = threshold + 1.0 + rng.uniform(0, 0.55)
                    quality = "SENSOR_READING_ABOVE_THRESHOLD"
                    evidence_id = f"E-SENSOR-{case['caseId']}-{sensor_id}-{step:04d}"
            if drift_sensor and step > steps * 0.65:
                temp += 1.4
                humidity += 6.0
                quality = "SENSOR_DRIFT_POSSIBLE" if temp <= threshold else "SENSOR_READING_ABOVE_THRESHOLD"
            if sensor_index == 8 and step in (80, 260, 430):
                temp = threshold + 6.5
                quality = "SENSOR_OUTLIER_REJECTED"
                evidence_id = f"E-SENSOR-{case['caseId']}-{sensor_id}-{step:04d}"
            if sensor_index == 10 and step == 90:
                temp = 99.9
            if sensor_index == 2 and step in (210, 211):
                duplicate_ts = start + timedelta(minutes=210 * config["readingIntervalMinutes"])
                readings.append(reading(duplicate_ts, sensor_id, zone_id, round(temp, 2), humidity, battery, signal, door_open, 210, 4, quality, evidence_id))
                continue
            if sensor_index in (6, 18) and step > steps * 0.8:
                battery = 12.0
            if sensor_index in (7, 19) and 120 <= step % 288 <= 130:
                signal = 18.0
            readings.append(reading(ts, sensor_id, zone_id, round(temp, 2), humidity, battery, signal, door_open, step, step % 7, quality, evidence_id))
    return sorted(readings, key=lambda row: (row["timestampUtc"], row["sensorId"]))


def reading(
    ts: datetime,
    sensor_id: str,
    zone_id: str,
    temperature: float | None,
    humidity: float,
    battery: float,
    signal: float,
    door_open: bool,
    sequence: int,
    ingestion_delay: int,
    quality: str,
    evidence_id: str,
) -> dict[str, Any]:
    return {
        "timestampUtc": iso_utc(ts),
        "sensorId": sensor_id,
        "zoneId": zone_id,
        "temperatureC": temperature,
        "humidityPercent": round(humidity, 2),
        "batteryPercent": round(battery, 2),
        "signalStrength": round(signal, 2),
        "doorOpen": door_open,
        "readingSequence": sequence,
        "ingestionDelaySeconds": ingestion_delay,
        "qualityLabel": quality,
        "evidenceId": evidence_id,
    }


def valid_temperature(reading_row: dict[str, Any]) -> bool:
    temp = reading_row["temperatureC"]
    return temp is not None and -40 <= temp <= 40 and reading_row["qualityLabel"] != "SENSOR_OUTLIER_REJECTED"


def excursion_windows(readings: list[dict[str, Any]], threshold: float, interval_minutes: int) -> list[dict[str, Any]]:
    windows = []
    active: dict[str, dict[str, Any]] = {}
    for row in readings:
        zone = row["zoneId"]
        above = valid_temperature(row) and row["temperatureC"] > threshold
        if above and zone not in active:
            active[zone] = {"zoneId": zone, "startUtc": row["timestampUtc"], "evidenceIds": []}
        if above:
            active[zone]["endUtc"] = iso_utc(parse_utc(row["timestampUtc"]) + timedelta(minutes=interval_minutes))
            if row["evidenceId"]:
                active[zone]["evidenceIds"].append(row["evidenceId"])
            continue
        if zone in active:
            windows.append(close_window(active.pop(zone)))
    windows.extend(close_window(value) for value in active.values())
    return [window for window in windows if window["durationMinutes"] >= interval_minutes]


def close_window(window: dict[str, Any]) -> dict[str, Any]:
    duration = int((parse_utc(window["endUtc"]) - parse_utc(window["startUtc"])).total_seconds() // 60)
    return {
        "zoneId": window["zoneId"],
        "startUtc": window["startUtc"],
        "endUtc": window["endUtc"],
        "durationMinutes": duration,
        "evidenceIds": sorted(set(window["evidenceIds"]))[:12],
    }


def aggregate(case: dict[str, Any]) -> dict[str, Any]:
    readings = synthetic_readings(case)
    config = sensor_config(case)
    threshold = config["thresholdMaxC"]
    zones = zone_ids(config)
    by_zone = {zone: [row for row in readings if row["zoneId"] == zone and valid_temperature(row)] for zone in zones}
    windows = excursion_windows(readings, threshold, config["readingIntervalMinutes"])
    quality_counts: dict[str, int] = {}
    for row in readings:
        quality_counts[row["qualityLabel"]] = quality_counts.get(row["qualityLabel"], 0) + 1
    for label in (
        "SENSOR_OK",
        "SENSOR_READING_ABOVE_THRESHOLD",
        "SENSOR_DROPOUT",
        "SENSOR_DRIFT_POSSIBLE",
        "SENSOR_OUTLIER_REJECTED",
        "SENSOR_WINDOW_ESCALATED",
    ):
        quality_counts.setdefault(label, 0)
    quality_counts["SENSOR_WINDOW_ESCALATED"] = len(windows)
    impacted_zones = sorted({window["zoneId"] for window in windows})
    zone_stats = {}
    for zone, rows in by_zone.items():
        temps = [row["temperatureC"] for row in rows]
        zone_stats[zone] = {
            "readingCount": len(rows),
            "minTemperatureC": round(min(temps), 2) if temps else None,
            "maxTemperatureC": round(max(temps), 2) if temps else None,
            "averageTemperatureC": round(sum(temps) / len(temps), 2) if temps else None,
            "aboveThresholdCount": sum(1 for row in rows if row["temperatureC"] > threshold),
        }
    mapped = sorted({pallet for mapping in case["zoneMappings"] if mapping["zoneId"] in impacted_zones for pallet in mapping["palletIds"]})
    unresolved = [pallet for pallet in case["palletIds"] if impacted_zones and pallet not in mapped]
    return {
        "config": config,
        "readings": readings,
        "generatedReadingCount": len(readings),
        "readingsPerSensor": len(readings) // config["sensorCount"],
        "readingsPerZone": {zone: len([row for row in readings if row["zoneId"] == zone]) for zone in zones},
        "zoneStats": zone_stats,
        "aboveThresholdReadingCount": sum(1 for row in readings if valid_temperature(row) and row["temperatureC"] > threshold),
        "excursionWindows": windows,
        "sensorQualitySummary": quality_counts,
        "dropoutCount": quality_counts.get("SENSOR_DROPOUT", 0),
        "outlierCount": quality_counts.get("SENSOR_OUTLIER_REJECTED", 0),
        "rejectedNoisyReadingCount": quality_counts.get("SENSOR_DROPOUT", 0)
        + quality_counts.get("SENSOR_OUTLIER_REJECTED", 0),
        "impactedZones": impacted_zones,
        "mappedPalletIds": mapped,
        "unresolvedPalletIds": unresolved,
    }


def sensor_summary(case: dict[str, Any], deterministic_result: dict[str, Any]) -> dict[str, Any]:
    data = aggregate(case)
    config = data["config"]
    return {
        "caseId": case["caseId"],
        "shipmentId": case["shipmentId"],
        "syntheticOnly": True,
        "generatedReadingCount": data["generatedReadingCount"],
        "sensorCount": config["sensorCount"],
        "zoneCount": config["zoneCount"],
        "timeRange": {"startUtc": config["startUtc"], "endUtc": config["endUtc"]},
        "thresholdMaxC": config["thresholdMaxC"],
        "aggregationSummary": {
            "readingsPerSensor": data["readingsPerSensor"],
            "readingsPerZone": data["readingsPerZone"],
            "zoneStats": data["zoneStats"],
            "aboveThresholdReadingCount": data["aboveThresholdReadingCount"],
            "rejectedNoisyReadingCount": data["rejectedNoisyReadingCount"],
        },
        "excursionWindows": data["excursionWindows"],
        "sensorQualitySummary": data["sensorQualitySummary"],
        "impactedZones": data["impactedZones"],
        "mappedPalletIds": deterministic_result["mappedPalletIds"],
        "unresolvedPalletIds": deterministic_result["unresolvedPalletIds"],
        "deterministicResult": deterministic_result,
        "safetyDisclaimers": [
            "Synthetic sensor stream only.",
            "Deterministic aggregation only; Fireworks is non-authoritative.",
            "No autonomous operational action.",
        ],
    }


def sensor_window(case: dict[str, Any], offset: int = 0, limit: int = 100) -> dict[str, Any]:
    if offset < 0 or limit < 1:
        return {"error": "offset must be non-negative and limit must be positive", "offset": offset, "limit": limit}
    limit = min(limit, MAX_WINDOW_LIMIT)
    readings = synthetic_readings(case)
    return {
        "caseId": case["caseId"],
        "offset": offset,
        "limit": limit,
        "totalReadings": len(readings),
        "readings": readings[offset : offset + limit],
    }


def normalize_reading_schema(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestampUtc": str(row.get("timestampUtc", "")),
        "sensorId": str(row.get("sensorId", "")),
        "zoneId": str(row.get("zoneId", "")),
        "temperatureC": row.get("temperatureC"),
        "humidityPercent": float(row.get("humidityPercent", 0)),
        "batteryPercent": float(row.get("batteryPercent", 0)),
        "signalStrength": float(row.get("signalStrength", 0)),
        "doorOpen": bool(row.get("doorOpen", False)),
        "readingSequence": int(row.get("readingSequence", -1)),
        "ingestionDelaySeconds": int(row.get("ingestionDelaySeconds", 0)),
        "qualityLabel": str(row.get("qualityLabel", "SENSOR_OK")),
        "evidenceId": str(row.get("evidenceId", "")),
    }


def cleaning_report(case: dict[str, Any]) -> dict[str, Any]:
    config = sensor_config(case)
    raw = [normalize_reading_schema(row) for row in synthetic_readings(case)]
    required = ("timestampUtc", "sensorId", "zoneId", "temperatureC", "humidityPercent", "batteryPercent", "signalStrength")
    seen = set()
    accepted = []
    rejected = []
    flags = {
        "FLAGGED_DROPOUT": 0,
        "FLAGGED_DRIFT": 0,
        "FLAGGED_OUTLIER": 0,
        "FLAGGED_LOW_BATTERY": 0,
        "FLAGGED_WEAK_SIGNAL": 0,
    }
    rejection_reasons: dict[str, int] = {"REJECTED_DUPLICATE": 0, "REJECTED_IMPOSSIBLE_VALUE": 0}
    for row in raw:
        key = (row["timestampUtc"], row["sensorId"])
        reasons = []
        if any(field not in row for field in required):
            reasons.append("REJECTED_IMPOSSIBLE_VALUE")
        if key in seen:
            reasons.append("REJECTED_DUPLICATE")
        temp = row["temperatureC"]
        if temp is not None and not (-40 <= temp <= 40):
            reasons.append("REJECTED_IMPOSSIBLE_VALUE")
        if not (0 <= row["humidityPercent"] <= 100 and 0 <= row["batteryPercent"] <= 100 and 0 <= row["signalStrength"] <= 100):
            reasons.append("REJECTED_IMPOSSIBLE_VALUE")
        if reasons:
            unique = sorted(set(reasons))
            for reason in unique:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            rejected.append({**row, "cleaningLabel": unique[0], "rejectionReasons": unique})
            seen.add(key)
            continue
        seen.add(key)
        row_flags = ["CLEAN_ACCEPTED"]
        if row["temperatureC"] is None or row["qualityLabel"] == "SENSOR_DROPOUT":
            row_flags.append("FLAGGED_DROPOUT")
        if row["qualityLabel"] == "SENSOR_DRIFT_POSSIBLE":
            row_flags.append("FLAGGED_DRIFT")
        if row["qualityLabel"] == "SENSOR_OUTLIER_REJECTED":
            row_flags.append("FLAGGED_OUTLIER")
        if row["batteryPercent"] < 20:
            row_flags.append("FLAGGED_LOW_BATTERY")
        if row["signalStrength"] < 25:
            row_flags.append("FLAGGED_WEAK_SIGNAL")
        for label in row_flags:
            if label in flags:
                flags[label] += 1
        accepted.append({**row, "cleaningLabel": row_flags[0], "flags": row_flags})
    expected = config["sensorCount"] * int(
        (parse_utc(config["endUtc"]) - parse_utc(config["startUtc"])).total_seconds() // 60 // config["readingIntervalMinutes"]
    )
    missing_expected = max(0, expected - len({(row["timestampUtc"], row["sensorId"]) for row in raw}))
    return {
        "caseId": case["caseId"],
        "rawReadingCount": len(raw),
        "acceptedReadingCount": len(accepted),
        "rejectedReadingCount": len(rejected),
        "duplicateCount": rejection_reasons.get("REJECTED_DUPLICATE", 0),
        "missingExpectedReadings": missing_expected,
        "rejectionReasons": rejection_reasons,
        "flagCounts": flags,
        "cleaningLabels": ["CLEAN_ACCEPTED", "REJECTED_DUPLICATE", "REJECTED_IMPOSSIBLE_VALUE", *flags.keys()],
        "sampleRejectedReadings": rejected[:5],
        "sampleAcceptedReadings": accepted[:5],
    }


def consensus_report(case: dict[str, Any]) -> dict[str, Any]:
    summary = aggregate(case)
    clean = cleaning_report(case)
    reports = []
    for zone, stats in summary["zoneStats"].items():
        above = stats["aboveThresholdCount"]
        total = max(1, stats["readingCount"])
        outlier_penalty = clean["flagCounts"]["FLAGGED_OUTLIER"] / max(1, summary["generatedReadingCount"]) * 100
        dropout_penalty = clean["flagCounts"]["FLAGGED_DROPOUT"] / max(1, summary["generatedReadingCount"]) * 100
        signal_penalty = clean["flagCounts"]["FLAGGED_WEAK_SIGNAL"] / max(1, summary["generatedReadingCount"]) * 50
        agreement = 100 - min(45, above / total * 100)
        zone_score = max(0, min(100, agreement - outlier_penalty - dropout_penalty - signal_penalty))
        if zone_score >= 85:
            label = "CONSENSUS_STRONG"
        elif zone_score >= 65:
            label = "CONSENSUS_PARTIAL"
        elif zone_score >= 45:
            label = "CONSENSUS_WEAK"
        else:
            label = "SENSOR_CONFLICT_REVIEW_REQUIRED"
        reports.append(
            {
                "zoneId": zone,
                "zoneConsensusScore": round(zone_score, 2),
                "sensorTrustScore": round(max(0, min(100, zone_score - dropout_penalty)), 2),
                "consensusLabel": label,
                "aboveThresholdCount": above,
                "outlierCount": clean["flagCounts"]["FLAGGED_OUTLIER"],
                "dropoutCount": clean["flagCounts"]["FLAGGED_DROPOUT"],
            }
        )
    return {"caseId": case["caseId"], "zones": reports}


def sers_risk(case: dict[str, Any], deterministic_result: dict[str, Any]) -> dict[str, Any]:
    summary = aggregate(case)
    clean = cleaning_report(case)
    consensus = consensus_report(case)
    threshold = float(case["thresholdMaxC"])
    max_temp = max(stat["maxTemperatureC"] or 0 for stat in summary["zoneStats"].values())
    distance = max(0, max_temp - threshold)
    longest_window = max([window["durationMinutes"] for window in summary["excursionWindows"]] or [0])
    door_open_count = sum(1 for row in summary["readings"] if row["doorOpen"])
    humidity_span = max((stat["maxTemperatureC"] or 0) - (stat["minTemperatureC"] or 0) for stat in summary["zoneStats"].values())
    weakest_consensus = min([zone["zoneConsensusScore"] for zone in consensus["zones"]] or [100])
    unresolved_penalty = 18 if deterministic_result["unresolvedPalletIds"] else 0
    score = (
        distance * 9
        + min(30, longest_window / 2)
        + (100 - weakest_consensus) * 0.18
        + clean["flagCounts"]["FLAGGED_DROPOUT"] * 0.08
        + clean["flagCounts"]["FLAGGED_OUTLIER"] * 1.5
        + door_open_count * 0.25
        + humidity_span * 0.5
        + unresolved_penalty
    )
    risk_score = round(max(0, min(100, score)), 2)
    if risk_score >= 75:
        band = "CRITICAL"
    elif risk_score >= 45:
        band = "REVIEW"
    elif risk_score >= 20:
        band = "WATCH"
    else:
        band = "LOW"
    factors = []
    if distance:
        factors.append("temperature distance above threshold")
    if longest_window:
        factors.append("consecutive above-threshold window")
    if deterministic_result["unresolvedPalletIds"]:
        factors.append("unresolved pallet mapping")
    if clean["flagCounts"]["FLAGGED_DROPOUT"]:
        factors.append("sensor dropout penalty")
    if door_open_count:
        factors.append("door-open events")
    return {
        "modelName": "Sentinel Excursion Risk Score",
        "modelVersion": "SERS-0.1-synthetic",
        "riskScore": risk_score,
        "riskBand": band,
        "topContributingFactors": factors[:5] or ["synthetic control profile"],
        "confidenceLabel": "SYNTHETIC_BENCHMARK_ONLY",
        "advisoryOnly": True,
    }


FEATURES = [
    "maxTemperatureC",
    "avgTemperatureC",
    "humidityAverage",
    "qualityIssueCount",
    "consensusScore",
    "doorOpenCount",
    "unresolvedPalletCount",
]


def training_dataset(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        result_unresolved = len(case.get("unresolvedPalletIds", []))
        data = aggregate(case)
        consensus = consensus_report(case)
        consensus_by_zone = {row["zoneId"]: row["zoneConsensusScore"] for row in consensus["zones"]}
        for window_start in range(0, len(data["readings"]), 96):
            chunk = data["readings"][window_start : window_start + 96]
            if not chunk:
                continue
            valid = [row for row in chunk if row["temperatureC"] is not None and -40 <= row["temperatureC"] <= 40]
            temps = [row["temperatureC"] for row in valid] or [0]
            hum = [row["humidityPercent"] for row in valid] or [0]
            zone = chunk[0]["zoneId"]
            above_future = any(
                valid_temperature(row) and row["temperatureC"] > case["thresholdMaxC"]
                for row in data["readings"][window_start + 96 : window_start + 102]
            )
            rows.append(
                {
                    "features": {
                        "maxTemperatureC": max(temps),
                        "avgTemperatureC": round(sum(temps) / len(temps), 2),
                        "humidityAverage": round(sum(hum) / len(hum), 2),
                        "qualityIssueCount": sum(1 for row in chunk if row["qualityLabel"] != "SENSOR_OK"),
                        "consensusScore": consensus_by_zone.get(zone, 100),
                        "doorOpenCount": sum(1 for row in chunk if row["doorOpen"]),
                        "unresolvedPalletCount": result_unresolved,
                    },
                    "label": int(above_future),
                }
            )
    return rows


def train_linear_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {feature: 0.0 for feature in FEATURES}
    bias = 0.0
    for _ in range(30):
        for row in rows:
            z = bias + sum(weights[name] * (row["features"][name] / 100) for name in FEATURES)
            pred = 1 / (1 + pow(2.71828, -z))
            error = pred - row["label"]
            bias -= 0.08 * error
            for name in FEATURES:
                weights[name] -= 0.08 * error * (row["features"][name] / 100)
    return {"weights": weights, "bias": bias}


def predict_probability(model: dict[str, Any], features: dict[str, Any]) -> float:
    z = model["bias"] + sum(model["weights"][name] * (features[name] / 100) for name in FEATURES)
    return 1 / (1 + pow(2.71828, -z))


def benchmark_model(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = training_dataset(cases)
    split = max(1, int(len(rows) * 0.7))
    train_rows = rows[:split]
    test_rows = rows[split:] or rows[:]
    model = train_linear_model(train_rows)

    def evaluate(fn: Any) -> dict[str, Any]:
        tp = tn = fp = fn_count = 0
        for row in test_rows:
            pred = fn(row)
            label = row["label"]
            tp += int(pred == 1 and label == 1)
            tn += int(pred == 0 and label == 0)
            fp += int(pred == 1 and label == 0)
            fn_count += int(pred == 0 and label == 1)
        total = max(1, len(test_rows))
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn_count)
        return {
            "accuracy": round((tp + tn) / total, 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "falsePositives": fp,
            "falseNegatives": fn_count,
            "confusionMatrix": {"truePositive": tp, "trueNegative": tn, "falsePositive": fp, "falseNegative": fn_count},
        }

    return {
        "benchmarkScope": "On deterministic synthetic benchmark data only.",
        "model": {
            "modelName": "Synthetic logistic sensor-window classifier",
            "modelVersion": "SYN-LR-0.1",
            "trainingRows": len(train_rows),
            "testRows": len(test_rows),
            "features": FEATURES,
            "seed": "caseId-derived deterministic seeds",
            "predictionHorizonMinutes": 30,
        },
        "metrics": evaluate(lambda row: int(predict_probability(model, row["features"]) >= 0.5)),
        "baselines": {
            "naiveCurrentTemperatureThreshold": evaluate(lambda row: int(row["features"]["maxTemperatureC"] > 8.0)),
            "rollingAverageThreshold": evaluate(lambda row: int(row["features"]["avgTemperatureC"] > 7.4)),
        },
        "claimsBoundary": "No real-world superiority claim; comparison is only against simple baselines on synthetic data.",
    }


def prediction_report(case: dict[str, Any], deterministic_result: dict[str, Any], all_cases: list[dict[str, Any]]) -> dict[str, Any]:
    bench = benchmark_model(all_cases)
    risk = sers_risk(case, deterministic_result)
    summary = aggregate(case)
    latest_zone = summary["impactedZones"][0] if summary["impactedZones"] else "none"
    return {
        "caseId": case["caseId"],
        "advisoryOnly": True,
        "predictionHorizonMinutes": 30,
        "sers": risk,
        "modelBenchmarkReference": bench["model"],
        "predictionSummary": {
            "label": "SYNTHETIC_ADVISORY_REVIEW_SIGNAL",
            "riskBand": risk["riskBand"],
            "impactedZone": latest_zone,
        },
        "deterministicResultUnchanged": deterministic_result,
    }
