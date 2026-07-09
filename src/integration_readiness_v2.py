from __future__ import annotations

import html
import json
from functools import lru_cache
from typing import Any

VERSION = "integration-readiness-v2.0.0"

PHASE2_FIELDS = [
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
    "shockVibrationFlag",
    "tiltFlag",
    "lightExposureFlag",
    "locationProxy",
    "readingSequence",
    "firmwareVersion",
    "calibrationProfileId",
    "gatewayId",
    "ingestionDelaySeconds",
]

SAFETY_CONTROLS = [
    "release action is not executed",
    "quarantine or hold action is not executed",
    "discard action is not executed",
    "reroute action is not executed",
    "outbound customer notice is not executed",
    "compliance signoff is not produced",
    "production readiness is not asserted",
]

BOUNDARY = {
    "syntheticOnly": True,
    "advisoryOnly": True,
    "externalCalls": "none",
    "webhookDelivery": "disabled",
    "dataScope": "synthetic sandbox samples only",
    "secrets": "no secrets or environment variables are introduced",
}


def _sample_inbound_contract() -> dict[str, Any]:
    return {
        "contractName": "Synthetic Sensor Window Inbound Contract",
        "schemaVersion": "synthetic-inbound-v2",
        "syntheticOnly": True,
        "fields": [
            {
                "name": field,
                "required": True,
                "description": f"Synthetic sample field aligned with Phase 2 data model: {field}.",
            }
            for field in PHASE2_FIELDS
        ],
        "sample": {
            "timestampUtc": "2026-07-09T12:00:00Z",
            "sensorId": "synthetic-sensor-001",
            "deviceId": "synthetic-device-001",
            "shipmentId": "synthetic-shipment-001",
            "containerId": "synthetic-container-001",
            "zoneId": "synthetic-zone-a",
            "palletId": "synthetic-pallet-001",
            "temperatureC": 4.8,
            "humidityPercent": 58.0,
            "batteryPercent": 92,
            "signalStrength": 87,
            "doorOpen": False,
            "shockVibrationFlag": False,
            "tiltFlag": False,
            "lightExposureFlag": False,
            "locationProxy": "synthetic-location-proxy",
            "readingSequence": 1001,
            "firmwareVersion": "synthetic-fw-1.0",
            "calibrationProfileId": "synthetic-calibration-profile",
            "gatewayId": "synthetic-gateway-001",
            "ingestionDelaySeconds": 12,
        },
    }


def _sample_outbound_contract() -> dict[str, Any]:
    return {
        "contractName": "Synthetic Advisory Review Outbound Contract",
        "schemaVersion": "synthetic-advisory-v2",
        "syntheticOnly": True,
        "advisoryOnly": True,
        "fields": [
            "reviewPacketId",
            "scenarioId",
            "riskBand",
            "riskScore",
            "confidenceLabel",
            "evidenceLinks",
            "humanReviewRequired",
            "blockedAutonomousActions",
            "advisoryOnly",
            "syntheticOnly",
        ],
        "sample": {
            "reviewPacketId": "review-no-excursion-control",
            "scenarioId": "no-excursion-control",
            "riskBand": "WATCH",
            "riskScore": 34,
            "confidenceLabel": "MEDIUM",
            "evidenceLinks": {
                "scenario": "/scenario-lab/no-excursion-control.json",
                "reviewPacket": "/review-workbench/no-excursion-control.json",
                "replay": "/incident-replay/no-excursion-control.json",
            },
            "humanReviewRequired": True,
            "blockedAutonomousActions": SAFETY_CONTROLS,
            "advisoryOnly": True,
            "syntheticOnly": True,
        },
    }


@lru_cache(maxsize=1)
def get_integration_readiness_payload() -> dict[str, Any]:
    return {
        "phase": "Phase 10 - Partner / Integration Readiness Layer",
        "version": VERSION,
        **BOUNDARY,
        "summary": "Static synthetic integration readiness surface for future sandbox planning.",
        "routes": {
            "readiness": "/integration-readiness.json",
            "contract": "/integration-contract.json",
            "safety": "/integration-safety.json",
        },
        "integrationReadinessChecklist": [
            "schema versioning planned",
            "authentication placeholder only",
            "rate-limit placeholder only",
            "audit logging placeholder only",
            "partner sandbox only",
            "privacy review required before actual external data",
            "legal and compliance review required before regulated use",
        ],
        "nonGoals": [
            "no webhook creation",
            "no email sending",
            "no external API call",
            "no secret storage",
            "no environment variable addition",
            "no autonomous operational workflow",
        ],
        "safetyControls": SAFETY_CONTROLS,
    }


@lru_cache(maxsize=1)
def get_integration_contract_payload() -> dict[str, Any]:
    return {
        "phase": "Phase 10 - Synthetic Integration Contract",
        "version": VERSION,
        **BOUNDARY,
        "sampleInboundContract": _sample_inbound_contract(),
        "sampleOutboundAdvisoryContract": _sample_outbound_contract(),
    }


@lru_cache(maxsize=1)
def get_integration_safety_payload() -> dict[str, Any]:
    return {
        "phase": "Phase 10 - Integration Safety Boundary",
        "version": VERSION,
        **BOUNDARY,
        "safetyControls": SAFETY_CONTROLS,
        "requiredBeforeAnyFutureActualData": [
            "privacy review",
            "security review",
            "legal review",
            "regulated-use review",
            "partner sandbox agreement",
            "audit logging design",
            "explicit human-review workflow",
        ],
        "blockedCapabilities": [
            "webhook delivery",
            "email delivery",
            "external partner API calls",
            "secret persistence",
            "operational action dispatch",
        ],
    }


def _json(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def _page(title: str, summary: str, payload: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ margin:0; font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#071014; color:#eef7f2; }}
main {{ max-width:1160px; margin:0 auto; padding:32px 20px 56px; }}
a {{ color:#96e6b3; }}
.card {{ background:#102129; border:1px solid #21414d; border-radius:18px; padding:20px; margin:18px 0; }}
.pill {{ display:inline-block; border:1px solid #315c6d; border-radius:999px; padding:5px 9px; margin:4px 5px 4px 0; color:#c8f7dc; }}
pre {{ white-space:pre-wrap; word-break:break-word; background:#071014; border:1px solid #21414d; border-radius:14px; padding:16px; }}
</style>
</head>
<body>
<main>
<p><a href="/">ColdChain Sentinel</a> · <a href="/integration-readiness.json">Readiness JSON</a> · <a href="/integration-contract.json">Contract JSON</a> · <a href="/integration-safety.json">Safety JSON</a></p>
<h1>{html.escape(title)}</h1>
<p>{html.escape(summary)}</p>
<section class="card">
<span class="pill">Synthetic sandbox only</span>
<span class="pill">Advisory-only</span>
<span class="pill">No external calls</span>
<span class="pill">No webhook delivery</span>
</section>
<section class="card">
<h2>Payload</h2>
<pre>{_json(payload)}</pre>
</section>
</main>
</body>
</html>"""


def render_integration_readiness_html() -> str:
    return _page(
        "Partner / Integration Readiness",
        "Static synthetic readiness layer for future sandbox planning.",
        get_integration_readiness_payload(),
    )


def render_integration_contract_html() -> str:
    return _page(
        "Synthetic Integration Contract",
        "Inbound synthetic sensor window and outbound advisory review contract.",
        get_integration_contract_payload(),
    )


def render_integration_safety_html() -> str:
    return _page(
        "Integration Safety Boundary",
        "Safety controls for future integration planning without external calls.",
        get_integration_safety_payload(),
    )