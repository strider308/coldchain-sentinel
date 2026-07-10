from __future__ import annotations

import html
import json
from typing import Any

from integration_readiness_v2 import get_integration_contract_payload


PHASE = "Phase 15 - Integration Sandbox"
STATUS = "READY"

ROUTE_MAP = {
    "integrationSandbox": "/integration-sandbox",
    "integrationSandboxJson": "/integration-sandbox.json",
    "sampleRequest": "/integration-sandbox/sample-request.json",
    "sampleResponse": "/integration-sandbox/sample-response.json",
    "rejectionExample": "/integration-sandbox/rejection-example.json",
    "integrationReadiness": "/integration-readiness",
    "dataQuality": "/data-quality",
    "consensus": "/consensus",
    "sers": "/sers",
    "demoConsole": "/demo-console",
    "finalValidation": "/final-validation",
}


def _samples() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = get_integration_contract_payload()
    return (
        dict(contract["sampleInboundContract"]["sample"]),
        dict(contract["sampleOutboundAdvisoryContract"]["sample"]),
    )


def get_sample_request_payload() -> dict[str, Any]:
    inbound, _ = _samples()
    return inbound


def get_sample_response_payload() -> dict[str, Any]:
    _, outbound = _samples()
    return outbound


def get_rejection_example_payload() -> dict[str, Any]:
    return {
        "accepted": False,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "received": {
            "timestampUtc": "not-a-timestamp",
            "sensorId": "",
            "temperatureC": "hot",
            "requestedCapability": "dispatch operational action",
        },
        "errors": [
            "missing required field: sensorId",
            "missing required field: shipmentId",
            "timestampUtc must be UTC ISO-8601",
            "temperatureC must be numeric",
            "operational action requests are rejected",
        ],
    }


def get_integration_sandbox_payload() -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
        "runtimeGpuRequired": False,
        "deterministicRulesAuthoritative": True,
        "externalCallsMade": False,
        "webhooksEnabled": False,
        "secretsRequired": False,
        "inboundSample": get_sample_request_payload(),
        "outboundSample": get_sample_response_payload(),
        "rejectionExample": get_rejection_example_payload(),
        "validationRules": [
            "required Phase 2 fields must be present",
            "timestampUtc must be UTC ISO-8601",
            "temperatureC must be numeric and within synthetic adapter bounds",
            "only synthetic sample identifiers are accepted",
            "operational action requests are rejected",
        ],
        "integrationBoundaries": [
            "Synthetic-only sample contracts.",
            "Advisory-only responses require human review.",
            "No external calls or webhook delivery.",
            "No secrets or environment configuration required.",
            "No real customer, shipment, pharma, logistics, patient, or sensor data.",
            "Deterministic rules remain authoritative.",
            "SERS remains advisory-only.",
        ],
        "routeMap": dict(ROUTE_MAP),
    }


def _json(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def render_integration_sandbox_html() -> str:
    payload = get_integration_sandbox_payload()
    links = "\n".join(
        f'<a class="button" href="{html.escape(route)}">{html.escape(name)}</a>'
        for name, route in payload["routeMap"].items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ColdChain Sentinel Integration Sandbox</title>
  <style>
    body {{ margin:0; font-family:Arial,Helvetica,sans-serif; background:#f4f8f7; color:#172321; line-height:1.45; }}
    main {{ max-width:1100px; margin:0 auto; padding:24px 16px 44px; }}
    h1 {{ font-size:clamp(30px,6vw,48px); margin:0 0 8px; }}
    .hero,.panel {{ background:#fff; border:1px solid #d4e2de; border-radius:16px; padding:18px; margin:14px 0; }}
    .hero {{ background:#102b27; color:#f2fffb; }}
    .badge {{ display:inline-block; margin:4px 5px 4px 0; padding:6px 10px; border-radius:999px; background:#dff5ed; color:#125c4f; font-weight:700; }}
    .button {{ display:inline-block; margin:5px 6px 5px 0; padding:8px 12px; border-radius:10px; background:#146c5f; color:#fff; text-decoration:none; font-weight:700; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }}
    pre {{ white-space:pre-wrap; word-break:break-word; overflow-x:auto; background:#091918; color:#d9fff2; border-radius:12px; padding:14px; }}
  </style>
</head>
<body>
<main data-testid="integration-sandbox-page">
  <section class="hero">
    <h1>Integration Sandbox</h1>
    <p>Static synthetic contracts and rejection evidence. Nothing leaves this process.</p>
    <span class="badge">Synthetic-only</span>
    <span class="badge">Advisory-only</span>
    <span class="badge">No external calls</span>
    <span class="badge">No webhooks</span>
    <span class="badge">Deterministic rules authoritative</span>
  </section>
  <section class="panel">
    <a class="button" href="/integration-readiness">Integration Readiness</a>
    <a class="button" href="/demo-console">Demo Console</a>
  </section>
  <section class="grid">
    <article class="panel"><h2>Sample request</h2><pre>{_json(payload["inboundSample"])}</pre></article>
    <article class="panel"><h2>Sample response</h2><pre>{_json(payload["outboundSample"])}</pre></article>
    <article class="panel"><h2>Rejection example</h2><pre>{_json(payload["rejectionExample"])}</pre></article>
  </section>
  <section class="panel"><h2>Routes</h2>{links}</section>
</main>
</body>
</html>"""
