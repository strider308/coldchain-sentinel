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
            if dropout_sensor and 36 <= step % 288 <= 38:
                readings.append(reading(ts, sensor_id, zone_id, None, "SENSOR_DROPOUT", ""))
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
                quality = "SENSOR_DRIFT_POSSIBLE" if temp <= threshold else "SENSOR_READING_ABOVE_THRESHOLD"
            if sensor_index == 8 and step in (80, 260, 430):
                temp = threshold + 6.5
                quality = "SENSOR_OUTLIER_REJECTED"
                evidence_id = f"E-SENSOR-{case['caseId']}-{sensor_id}-{step:04d}"
            readings.append(reading(ts, sensor_id, zone_id, round(temp, 2), quality, evidence_id))
    return sorted(readings, key=lambda row: (row["timestampUtc"], row["sensorId"]))


def reading(
    ts: datetime, sensor_id: str, zone_id: str, temperature: float | None, quality: str, evidence_id: str
) -> dict[str, Any]:
    return {
        "timestampUtc": iso_utc(ts),
        "sensorId": sensor_id,
        "zoneId": zone_id,
        "temperatureC": temperature,
        "qualityLabel": quality,
        "evidenceId": evidence_id,
    }


def valid_temperature(reading_row: dict[str, Any]) -> bool:
    return reading_row["temperatureC"] is not None and reading_row["qualityLabel"] != "SENSOR_OUTLIER_REJECTED"


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
