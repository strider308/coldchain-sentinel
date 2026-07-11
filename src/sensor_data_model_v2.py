"""Sensor Data Model v2 for ColdChain Sentinel.

Synthetic-only raw and normalized cold-chain sensor payloads.
No real shipment, customer, pharma, logistics, patient, or sensor data is used.
"""

from __future__ import annotations

import html
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs

from case_engine import get_case
from serve_dashboard import badge, global_nav, page

RAW_SENSOR_FIELDS: list[dict[str, str]] = [
    {"field": "timestampUtc", "type": "ISO-8601 UTC string", "required": "yes", "meaning": "Sensor reading time in UTC."},
    {"field": "sensorId", "type": "string", "required": "yes", "meaning": "Logical sensor identity inside the shipment/container."},
    {"field": "deviceId", "type": "string", "required": "yes", "meaning": "Physical device identifier."},
    {"field": "shipmentId", "type": "string", "required": "yes", "meaning": "Shipment identifier."},
    {"field": "containerId", "type": "string", "required": "yes", "meaning": "Cold-chain container or box identifier."},
    {"field": "zoneId", "type": "string", "required": "yes", "meaning": "Container zone being monitored."},
    {"field": "palletId", "type": "string|null", "required": "recommended", "meaning": "Known pallet mapping, if the reading can be mapped."},
    {"field": "temperatureC", "type": "number|null", "required": "yes", "meaning": "Temperature in Celsius after device-side measurement."},
    {"field": "humidityPercent", "type": "number|null", "required": "recommended", "meaning": "Relative humidity percentage."},
    {"field": "batteryPercent", "type": "number|null", "required": "recommended", "meaning": "Battery percentage reported by device."},
    {"field": "signalStrength", "type": "number|null", "required": "recommended", "meaning": "Gateway/device signal quality proxy."},
    {"field": "doorOpen", "type": "boolean", "required": "recommended", "meaning": "Door-open context flag."},
    {"field": "shockVibrationFlag", "type": "boolean", "required": "recommended", "meaning": "Shock or vibration event flag."},
    {"field": "tiltFlag", "type": "boolean", "required": "recommended", "meaning": "Tilt/orientation anomaly flag."},
    {"field": "lightExposureFlag", "type": "boolean", "required": "recommended", "meaning": "Light exposure flag indicating possible opening/tamper context."},
    {"field": "locationProxy", "type": "object|null", "required": "optional", "meaning": "Coarse GPS/location proxy. Synthetic demo uses non-real locations only."},
    {"field": "readingSequence", "type": "integer", "required": "yes", "meaning": "Monotonic per-device reading sequence."},
    {"field": "firmwareVersion", "type": "string", "required": "recommended", "meaning": "Device firmware version."},
    {"field": "calibrationProfileId", "type": "string", "required": "recommended", "meaning": "Calibration profile used for interpretation."},
    {"field": "gatewayId", "type": "string", "required": "recommended", "meaning": "Gateway that received the reading."},
    {"field": "ingestionDelaySeconds", "type": "integer", "required": "recommended", "meaning": "Delay between sensor timestamp and platform ingestion."},
]

ACCEPTED_FIELDS = [field["field"] for field in RAW_SENSOR_FIELDS]
REQUIRED_FIELDS = ["timestampUtc", "sensorId", "deviceId", "shipmentId", "containerId", "zoneId", "temperatureC", "readingSequence"]
REJECTION_REASONS = [
    "missing required identity field",
    "unparseable timestamp",
    "impossible temperature value",
    "invalid humidity/battery/signal range",
    "negative ingestion delay",
    "duplicate device sequence in the same case window",
]
NORMALIZATION_STEPS = [
    "coerce timestamps to UTC ISO-8601",
    "map vendor/device identifiers into canonical IDs",
    "preserve Celsius temperature as temperatureC",
    "normalize humidity, battery, and signal ranges",
    "normalize boolean event flags",
    "attach synthetic shipment/container/zone/pallet context",
    "derive evidenceCandidate and normalizationWarnings",
]
EVIDENCE_OUTPUTS = [
    "threshold-breach candidates",
    "door-open context near excursion windows",
    "shock/vibration context",
    "tilt context",
    "light exposure context",
    "low-battery and weak-signal context",
    "unresolved pallet mapping signals",
    "ingestion-delay warnings",
]


def _table(headers: list[str], rows: list[list[Any]], testid: str) -> str:
    head = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f'<table data-testid="{html.escape(testid)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _items(values: list[str], test_prefix: str) -> str:
    return "\n".join(
        f'<li data-testid="{html.escape(test_prefix)}-{index}">{html.escape(value)}</li>'
        for index, value in enumerate(values, start=1)
    )


def _safe_case_value(case: dict[str, Any], key: str, fallback: str) -> str:
    value = case.get(key)
    return str(value) if value is not None else fallback


def _seed(case_id: str) -> int:
    return sum(ord(char) for char in case_id)


def _base_time() -> datetime:
    return datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _bounded_window_params(query: dict[str, list[str]]) -> tuple[int, int]:
    try:
        offset = int(query.get("offset", ["0"])[0])
        limit = int(query.get("limit", ["100"])[0])
    except ValueError as exc:
        raise ValueError("offset and limit must be integers") from exc
    if offset < 0 or limit < 1:
        raise ValueError("offset must be non-negative and limit must be positive")
    return offset, min(limit, 250)


def raw_schema_json() -> dict[str, Any]:
    return {
        "schemaName": "ColdChain Sentinel Raw Sensor Reading v2",
        "schemaVersion": "raw-sensor-reading-v2",
        "mode": "synthetic_demo_schema",
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "acceptedFields": ACCEPTED_FIELDS,
        "requiredFields": REQUIRED_FIELDS,
        "fields": RAW_SENSOR_FIELDS,
        "rejectionReasons": REJECTION_REASONS,
        "normalizationSteps": NORMALIZATION_STEPS,
        "evidenceOutputs": EVIDENCE_OUTPUTS,
        "safetyBoundary": [
            "Synthetic demo data only.",
            "No real customer, pharma, logistics, shipment, patient, or sensor data.",
            "No autonomous operational action.",
            "Deterministic rules remain authoritative.",
            "SERS remains advisory only.",
        ],
    }


def data_contract_v2_json() -> dict[str, Any]:
    return {
        "contractName": "ColdChain Sentinel Data Contract v2",
        "contractVersion": "v2",
        "whatSensorsSend": {
            "description": "Raw device/vendor readings with timing, identity, environmental, event, quality, gateway, calibration, and ingestion-delay fields.",
            "fields": ACCEPTED_FIELDS,
        },
        "whatPlatformAccepts": {
            "required": REQUIRED_FIELDS,
            "recommended": [
                "humidityPercent",
                "batteryPercent",
                "signalStrength",
                "doorOpen",
                "shockVibrationFlag",
                "tiltFlag",
                "lightExposureFlag",
                "firmwareVersion",
                "calibrationProfileId",
                "gatewayId",
                "ingestionDelaySeconds",
            ],
            "optional": ["palletId", "locationProxy"],
        },
        "whatGetsRejected": REJECTION_REASONS,
        "whatGetsNormalized": NORMALIZATION_STEPS,
        "whatBecomesEvidence": EVIDENCE_OUTPUTS,
        "exampleRoutes": [
            "/raw-schema",
            "/raw-schema.json",
            "/cases/blocked-unresolved-pallet/raw-sensor-window.json?offset=0&limit=25",
            "/cases/blocked-unresolved-pallet/normalized-sensor-window.json?offset=0&limit=25",
        ],
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "sersAdvisoryOnly": True,
        "autonomousActionsAllowed": False,
    }


def render_raw_schema_page() -> str:
    schema = raw_schema_json()
    rows = [[field["field"], field["type"], field["required"], field["meaning"]] for field in schema["fields"]]
    body = f"""
  <header data-testid="raw-schema-page">
    {global_nav()}
    <h1>Raw Sensor Schema v2</h1>
    <p>Canonical synthetic raw sensor payload fields for ColdChain Sentinel.</p>
    {badge("Synthetic only", "warn")}{badge("No production validation", "warn")}
  </header>
  <main>
    <section class="panel">
      <h2>Raw fields</h2>
      {_table(["Field", "Type", "Required", "Meaning"], rows, "raw-schema-fields")}
      <div class="toolbar"><a class="button" href="/raw-schema.json">Raw schema JSON</a><a class="button" href="/data-contract">Data Contract</a></div>
    </section>
  </main>
"""
    return page("ColdChain Sentinel Raw Sensor Schema v2", body)


def render_data_contract_v2_page() -> str:
    contract = data_contract_v2_json()
    body = f"""
  <header data-testid="data-contract-v2-page">
    {global_nav()}
    <h1>Data Contract v2</h1>
    <p>What sensors send, what ColdChain Sentinel accepts, what gets rejected, what gets normalized, and what becomes evidence.</p>
    {badge("Synthetic only", "warn")}{badge("Deterministic rules authoritative", "good")}
  </header>
  <main>
    <section class="grid">
      <article class="panel" data-testid="what-sensors-send"><h2>What sensors send</h2><p>{html.escape(contract["whatSensorsSend"]["description"])}</p><ul>{_items(contract["whatSensorsSend"]["fields"], "sensor-sends")}</ul></article>
      <article class="panel" data-testid="what-platform-accepts"><h2>What the platform accepts</h2><p>Required identity/timing/environment fields plus recommended quality, gateway, calibration, and event context.</p><ul>{_items(contract["whatPlatformAccepts"]["required"], "platform-required")}</ul></article>
      <article class="panel status-block" data-testid="what-gets-rejected"><h2>What gets rejected</h2><ul>{_items(contract["whatGetsRejected"], "rejected-rule")}</ul></article>
      <article class="panel" data-testid="what-gets-normalized"><h2>What gets normalized</h2><ul>{_items(contract["whatGetsNormalized"], "normalized-rule")}</ul></article>
      <article class="panel" data-testid="what-becomes-evidence"><h2>What becomes evidence</h2><ul>{_items(contract["whatBecomesEvidence"], "evidence-output")}</ul></article>
    </section>
    <section class="panel"><div class="toolbar"><a class="button" href="/data-contract.json">Data Contract JSON</a><a class="button" href="/raw-schema">Raw Schema</a><a class="button" href="/cases/blocked-unresolved-pallet/raw-sensor-window.json?offset=0&limit=25">Raw window JSON</a><a class="button" href="/cases/blocked-unresolved-pallet/normalized-sensor-window.json?offset=0&limit=25">Normalized window JSON</a></div></section>
  </main>
"""
    return page("ColdChain Sentinel Data Contract v2", body)


def _generate_raw_readings(case_id: str, total: int = 288) -> list[dict[str, Any]]:
    case = get_case(case_id)
    seed = _seed(case_id)
    base = _base_time()
    shipment_id = _safe_case_value(case, "shipmentId", f"SYN-SHIP-{case_id.upper()}")
    container_id = _safe_case_value(case, "containerId", "CONT-SYN-001")
    threshold = float(case.get("thresholdMaxC", 8.0))
    zones = ["Z1", "Z2", "Z3"]
    zone_pallets = {
        "Z1": ["PAL-SYN-1001", "PAL-SYN-1002", "PAL-SYN-1003", None],
        "Z2": ["PAL-SYN-2001", "PAL-SYN-2002"],
        "Z3": ["PAL-SYN-3001"],
    }
    readings: list[dict[str, Any]] = []

    for sequence in range(total):
        timestamp = base + timedelta(minutes=10 * sequence)
        zone_id = zones[(sequence + seed) % len(zones)]
        sensor_number = ((sequence // len(zones)) % 4) + 1
        sensor_id = f"SYN-{zone_id}-TEMP-{sensor_number:02d}"
        device_id = f"DEV-{zone_id}-{sensor_number:02d}"
        pallet_options = zone_pallets[zone_id]
        pallet_id = pallet_options[(sequence + sensor_number) % len(pallet_options)]

        wave = math.sin((sequence + seed) / 9.0)
        temperature = 4.3 + wave * 0.9 + (0.15 * sensor_number)
        if case_id == "blocked-unresolved-pallet" and zone_id == "Z1" and 63 <= sequence <= 69:
            temperature = threshold + 0.7 + (0.08 * (sequence - 63))
            pallet_id = None if sequence % 2 == 0 else pallet_id
        elif case_id == "excursion-fully-mapped" and zone_id == "Z2" and 72 <= sequence <= 78:
            temperature = threshold + 0.5 + (0.05 * (sequence - 72))
        elif case_id == "no-excursion-control":
            temperature = min(temperature, threshold - 1.1)

        humidity = 58.0 + math.sin(sequence / 11.0) * 7.0
        battery = max(5.0, 96.0 - (sequence * 0.13) - sensor_number)
        signal = -54.0 - ((sequence + sensor_number) % 28)
        door_open = bool(zone_id == "Z1" and sequence in (62, 63, 64, 70))
        shock = bool(sequence in (66, 141))
        tilt = bool(sequence in (67, 142))
        light = bool(door_open or sequence in (68, 143))
        ingestion_delay = int(3 + ((sequence * 7 + seed) % 95))

        # Synthetic quality edge cases for schema/normalization demonstration only.
        if sequence == 37:
            temperature = 999.0
        if sequence == 121:
            battery = 2.0
            signal = -96.0

        readings.append(
            {
                "timestampUtc": _iso(timestamp),
                "sensorId": sensor_id,
                "deviceId": device_id,
                "shipmentId": shipment_id,
                "containerId": container_id,
                "zoneId": zone_id,
                "palletId": pallet_id,
                "temperatureC": round(temperature, 2),
                "humidityPercent": round(humidity, 1),
                "batteryPercent": round(battery, 1),
                "signalStrength": round(signal, 1),
                "doorOpen": door_open,
                "shockVibrationFlag": shock,
                "tiltFlag": tilt,
                "lightExposureFlag": light,
                "locationProxy": {
                    "type": "synthetic_geofence",
                    "routeSegment": f"SYN-ROUTE-{1 + ((sequence + seed) % 5)}",
                    "gpsPrecision": "coarse_demo_only",
                },
                "readingSequence": sequence,
                "firmwareVersion": "synthetic-fw-2.0.0",
                "calibrationProfileId": f"CAL-SYN-{zone_id}-2026Q2",
                "gatewayId": f"GW-SYN-{1 + ((sequence + seed) % 3):02d}",
                "ingestionDelaySeconds": ingestion_delay,
            }
        )

    return readings


def _normalize_reading(reading: dict[str, Any], threshold: float) -> dict[str, Any]:
    warnings: list[str] = []
    rejection_reasons: list[str] = []

    for required in REQUIRED_FIELDS:
        if reading.get(required) is None:
            rejection_reasons.append(f"missing required field: {required}")

    temperature = reading.get("temperatureC")
    if not isinstance(temperature, (int, float)) or temperature < -50 or temperature > 80:
        rejection_reasons.append("impossible temperature value")

    humidity = reading.get("humidityPercent")
    if humidity is not None and (not isinstance(humidity, (int, float)) or humidity < 0 or humidity > 100):
        rejection_reasons.append("invalid humidity range")

    battery = reading.get("batteryPercent")
    if battery is not None and battery < 10:
        warnings.append("LOW_BATTERY_CONTEXT")

    signal = reading.get("signalStrength")
    if signal is not None and signal <= -90:
        warnings.append("WEAK_SIGNAL_CONTEXT")

    if reading.get("ingestionDelaySeconds", 0) > 60:
        warnings.append("INGESTION_DELAY_GT_60_SECONDS")

    threshold_breach = isinstance(temperature, (int, float)) and temperature > threshold and not rejection_reasons
    event_context = [
        label
        for label, active in [
            ("DOOR_OPEN_CONTEXT", reading.get("doorOpen")),
            ("SHOCK_VIBRATION_CONTEXT", reading.get("shockVibrationFlag")),
            ("TILT_CONTEXT", reading.get("tiltFlag")),
            ("LIGHT_EXPOSURE_CONTEXT", reading.get("lightExposureFlag")),
        ]
        if active
    ]
    warnings.extend(event_context)

    status = "REJECTED" if rejection_reasons else "ACCEPTED"
    evidence_candidate = threshold_breach or bool(event_context)

    normalized = dict(reading)
    normalized.update(
        {
            "schemaVersion": "raw-sensor-reading-v2",
            "normalizationVersion": "normalized-sensor-reading-v2",
            "temperatureUnit": "C",
            "signalQualityLabel": "WEAK_SIGNAL" if signal is not None and signal <= -90 else "SIGNAL_OK",
            "batteryQualityLabel": "LOW_BATTERY" if battery is not None and battery < 10 else "BATTERY_OK",
            "normalizationStatus": status,
            "rejectionReasons": rejection_reasons,
            "normalizationWarnings": warnings,
            "thresholdMaxC": threshold,
            "thresholdBreachCandidate": threshold_breach,
            "evidenceCandidate": evidence_candidate and status == "ACCEPTED",
            "evidenceType": "TEMPERATURE_EXCURSION_CANDIDATE" if threshold_breach else ("CONTEXT_EVENT" if event_context else "NONE"),
            "evidenceId": f'E-SDMV2-{reading["readingSequence"]:04d}' if evidence_candidate and status == "ACCEPTED" else None,
            "autonomousActionsAllowed": False,
            "syntheticOnly": True,
        }
    )
    return normalized


def raw_sensor_window_json(case_id: str, offset: int = 0, limit: int = 100) -> dict[str, Any]:
    readings = _generate_raw_readings(case_id)
    window = readings[offset : offset + limit]
    return {
        "caseId": case_id,
        "schemaVersion": "raw-sensor-reading-v2",
        "offset": offset,
        "limit": limit,
        "totalReadings": len(readings),
        "returnedReadings": len(window),
        "readings": window,
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
    }


def normalized_sensor_window_json(case_id: str, offset: int = 0, limit: int = 100) -> dict[str, Any]:
    case = get_case(case_id)
    threshold = float(case.get("thresholdMaxC", 8.0))
    raw = _generate_raw_readings(case_id)
    normalized = [_normalize_reading(reading, threshold) for reading in raw]
    window = normalized[offset : offset + limit]
    accepted = sum(1 for reading in normalized if reading["normalizationStatus"] == "ACCEPTED")
    rejected = len(normalized) - accepted
    evidence_candidates = sum(1 for reading in normalized if reading["evidenceCandidate"])
    return {
        "caseId": case_id,
        "schemaVersion": "normalized-sensor-reading-v2",
        "offset": offset,
        "limit": limit,
        "totalReadings": len(normalized),
        "returnedReadings": len(window),
        "acceptedReadings": accepted,
        "rejectedReadings": rejected,
        "evidenceCandidateCount": evidence_candidates,
        "readings": window,
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
    }


def parse_window_query(raw_query: str) -> tuple[int, int]:
    return _bounded_window_params(parse_qs(raw_query, keep_blank_values=True))
