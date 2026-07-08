"""Synthetic sensor adapter examples for Data Contract v2."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "fixtures" / "sensor-adapter-examples.json"
ADAPTER_VERSION = "sensor-adapter-v2-synthetic"
SUPPORTED_FORMATS = ["sentinel_native_v1", "vendor_flat_csv_v1", "vendor_nested_iot_v1"]
NORMALIZED_FIELDS = [
    "timestampUtc",
    "sensorId",
    "deviceId",
    "shipmentId",
    "containerId",
    "zoneId",
    "palletId",
    "temperatureC",
    "humidityPercent",
    "batteryPercent",
    "signalStrength",
    "doorOpen",
    "readingSequence",
    "firmwareVersion",
    "gatewayId",
    "ingestionDelaySeconds",
    "sourceFormat",
    "adapterVersion",
    "normalizationWarnings",
]


def load_examples() -> dict[str, list[dict[str, Any]]]:
    return json.loads(EXAMPLES.read_text(encoding="utf-8"))


def canonical_schema() -> dict[str, Any]:
    return {
        "version": "v2",
        "fields": NORMALIZED_FIELDS,
        "requiredFields": ["timestampUtc", "sensorId", "shipmentId", "temperatureC"],
        "optionalButWarnIfMissing": ["readingSequence", "zoneId", "shipmentId"],
        "syntheticOnly": True,
        "autonomousActionsAllowed": False,
    }


def first_example(source_format: str) -> dict[str, Any]:
    return load_examples()[source_format][0]["payload"]


def adapter_summary() -> dict[str, Any]:
    examples = load_examples()
    return {
        "dataContractVersion": "v2",
        "adapterVersion": ADAPTER_VERSION,
        "supportedSyntheticAdapterFormats": SUPPORTED_FORMATS,
        "exampleCounts": {key: len(value) for key, value in examples.items()},
        "schema": canonical_schema(),
        "syntheticOnly": True,
        "fireworksAuthoritative": False,
        "autonomousActionsAllowed": False,
    }


def normalize(source_format: str, payload: dict[str, Any]) -> dict[str, Any]:
    if source_format == "sentinel_native_v1":
        normalized = {
            "timestampUtc": payload.get("timestampUtc"),
            "sensorId": payload.get("sensorId"),
            "deviceId": payload.get("sensorId"),
            "shipmentId": payload.get("shipmentId"),
            "containerId": payload.get("containerId"),
            "zoneId": payload.get("zoneId"),
            "palletId": payload.get("palletId"),
            "temperatureC": number(payload.get("temperatureC")),
            "humidityPercent": number(payload.get("humidityPercent")),
            "batteryPercent": number(payload.get("batteryPercent")),
            "signalStrength": number(payload.get("signalStrength")),
            "doorOpen": bool_value(payload.get("doorOpen")),
            "readingSequence": int_value(payload.get("readingSequence")),
            "firmwareVersion": payload.get("firmwareVersion"),
            "gatewayId": payload.get("gatewayId"),
            "ingestionDelaySeconds": int_value(payload.get("ingestionDelaySeconds")) or 0,
        }
    elif source_format == "vendor_flat_csv_v1":
        normalized = {
            "timestampUtc": payload.get("ts"),
            "sensorId": payload.get("device"),
            "deviceId": payload.get("device"),
            "shipmentId": payload.get("shipment"),
            "containerId": payload.get("container"),
            "zoneId": payload.get("zone"),
            "palletId": payload.get("pallet"),
            "temperatureC": number(payload.get("temp_c")),
            "humidityPercent": number(payload.get("humidity")),
            "batteryPercent": number(payload.get("battery")),
            "signalStrength": number(payload.get("rssi")),
            "doorOpen": bool_value(payload.get("door")),
            "readingSequence": int_value(payload.get("seq")),
            "firmwareVersion": payload.get("firmware"),
            "gatewayId": payload.get("gateway"),
            "ingestionDelaySeconds": int_value(payload.get("delay_s")) or 0,
        }
    elif source_format == "vendor_nested_iot_v1":
        meta = payload.get("meta", {})
        shipment = payload.get("shipment", {})
        reading = payload.get("reading", {})
        temp = reading.get("temperature", {})
        temp_c = number(temp.get("value"))
        if temp_c is not None and str(temp.get("unit", "C")).upper() == "F":
            temp_c = round((temp_c - 32) * 5 / 9, 2)
        normalized = {
            "timestampUtc": reading.get("timestamp"),
            "sensorId": meta.get("deviceId"),
            "deviceId": meta.get("deviceId"),
            "shipmentId": shipment.get("id"),
            "containerId": shipment.get("containerId"),
            "zoneId": shipment.get("zoneId"),
            "palletId": shipment.get("palletId"),
            "temperatureC": temp_c,
            "humidityPercent": number(reading.get("humidity", {}).get("value")),
            "batteryPercent": number(reading.get("battery", {}).get("percent")),
            "signalStrength": number(reading.get("signal", {}).get("rssi")),
            "doorOpen": bool_value(reading.get("doorOpen")),
            "readingSequence": int_value(reading.get("sequence")),
            "firmwareVersion": meta.get("firmwareVersion"),
            "gatewayId": meta.get("gatewayId"),
            "ingestionDelaySeconds": int_value(reading.get("ingestionDelaySeconds")) or 0,
        }
    else:
        raise KeyError(source_format)
    normalized["sourceFormat"] = source_format
    normalized["adapterVersion"] = ADAPTER_VERSION
    normalized["normalizationWarnings"] = []
    return validation_result(normalized)


def validation_result(normalized: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    for field in ("timestampUtc", "sensorId", "shipmentId", "temperatureC"):
        if normalized.get(field) in (None, ""):
            errors.append(f"missing required field: {field}")
    if normalized.get("timestampUtc") and not parseable_timestamp(str(normalized["timestampUtc"])):
        errors.append("timestampUtc is not parseable UTC")
    temp = normalized.get("temperatureC")
    if temp is not None and not (-40 <= temp <= 40):
        errors.append("temperatureC outside synthetic adapter bounds")
    humidity = normalized.get("humidityPercent")
    if humidity is not None and not (0 <= humidity <= 100):
        errors.append("humidityPercent outside 0-100")
    battery = normalized.get("batteryPercent")
    if battery is not None and not (0 <= battery <= 100):
        errors.append("batteryPercent outside 0-100")
    if normalized.get("signalStrength") is not None and not isinstance(normalized["signalStrength"], (int, float)):
        errors.append("signalStrength must be numeric")
    for field in ("readingSequence", "zoneId", "shipmentId"):
        if normalized.get(field) in (None, ""):
            warnings.append(f"missing recommended field: {field}")
    normalized["normalizationWarnings"] = warnings
    return {"normalizedReading": normalized, "accepted": not errors, "warnings": warnings, "errors": errors}


def example_results(source_format: str | None = None) -> dict[str, Any]:
    examples = load_examples()
    selected = [source_format] if source_format else SUPPORTED_FORMATS
    return {
        "dataContractVersion": "v2",
        "adapterVersion": ADAPTER_VERSION,
        "formats": {
            fmt: [
                {"name": row["name"], "rawPayload": row["payload"], **normalize(fmt, row["payload"])}
                for row in examples[fmt]
            ]
            for fmt in selected
        },
        "syntheticOnly": True,
        "autonomousActionsAllowed": False,
    }


def parseable_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        return value.endswith("Z")
    except ValueError:
        return False


def number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def bool_value(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "open")
