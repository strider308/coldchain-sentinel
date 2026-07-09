from __future__ import annotations

import html
import json
from typing import Any

PHASE = "Phase 13 - Judge Demo Evidence Console"
STATUS = "READY"

ROUTE_MAP = {
    "commandCenter": "/command-center",
    "rawSchema": "/raw-schema",
    "dataQuality": "/data-quality",
    "consensus": "/consensus",
    "sers": "/sers",
    "trainingLab": "/training-lab",
    "scenarioLab": "/scenario-lab",
    "reviewWorkbench": "/review-workbench",
    "incidentReplay": "/incident-replay",
    "integrationReadiness": "/integration-readiness",
    "gpuResearchLab": "/gpu-research-lab",
    "fireworksAdvisory": "/fireworks-advisory",
    "fireworksModelCard": "/fireworks-model-card",
    "demoConsole": "/demo-console",
    "judgeEvidence": "/judge-evidence",
}

CLAIM_BOUNDARIES = [
    "Synthetic-only.",
    "Advisory-only.",
    "No real customer data.",
    "No real shipment data.",
    "No real pharma, logistics, customer, patient, or sensor data.",
    "No production, pharma, real-world, or compliance validation claim.",
    "No autonomous operational action; release, quarantine, discard, reroute, and customer messaging remain outside the app.",
    "Deterministic rules remain authoritative.",
    "SERS remains advisory-only.",
    "Fireworks is optional explanation support only.",
    "GPU/Jupyter evidence is offline synthetic research evidence only.",
    "Live app boot does not require GPU, ROCm, CUDA, PyTorch, notebooks, Fireworks, or any external service.",
    "Deterministic fallback works when Fireworks is unavailable.",
]

EVIDENCE_SECTIONS = [
    ("Platform Command Center", "/command-center", "Unified synthetic demo dashboard and route map."),
    ("Sensor Data Model v2", "/raw-schema", "Synthetic raw and normalized sensor contracts."),
    ("Data Trust Pipeline", "/data-quality", "Quality flags reject or down-rank weak synthetic evidence."),
    ("Zone Consensus Engine", "/consensus", "Redundancy prevents overreaction to one bad sensor."),
    ("SERS v2", "/sers", "Advisory risk scoring with deterministic rules still authoritative."),
    ("Synthetic Training Benchmark Lab", "/training-lab", "Synthetic benchmark and model-card evidence."),
    ("Synthetic Scenario Lab", "/scenario-lab", "Replayable synthetic scenario families."),
    ("Human Review Workbench", "/review-workbench", "Human review blocks autonomous decisions."),
    ("Incident Replay Timeline", "/incident-replay", "Evidence chain replay for reviewers."),
    ("Integration Readiness", "/integration-readiness", "Demo-scoped integration contracts and safety checks."),
    ("GPU Synthetic Research Lab", "/gpu-research-lab", "Offline synthetic GPU/Jupyter artifact evidence."),
    ("Fireworks Advisory Explanation Layer", "/fireworks-advisory", "Optional safety-gated explanation with fallback."),
]

DEMO_NARRATIVE = [
    "Synthetic data enters.",
    "Data quality rejects or flags weak evidence.",
    "Consensus prevents overreaction to a single bad sensor.",
    "SERS gives advisory risk only.",
    "Human review workbench blocks autonomous decisions.",
    "Incident replay explains the chain of evidence.",
    "GPU/Jupyter artifact proves offline synthetic research evidence.",
    "Fireworks gives optional safety-gated explanation while deterministic fallback remains available.",
]

GO_NO_GO_SUMMARY = [
    {"phase": "Phase 1-5", "status": "GO", "scope": "synthetic platform evidence"},
    {"phase": "Phase 6", "status": "GO", "scope": "synthetic training benchmark lab"},
    {"phase": "Phase 7", "status": "GO", "scope": "synthetic scenario lab"},
    {"phase": "Phase 8-10", "status": "GO", "scope": "human review, replay, integration evidence"},
    {"phase": "Phase 11/11.1", "status": "GO", "scope": "offline synthetic GPU artifact evidence"},
    {"phase": "Phase 12/12.1", "status": "GO", "scope": "optional Fireworks advisory explanation with fallback"},
    {"phase": "Phase 13", "status": "GO", "scope": "judge demo evidence console"},
]


def _fireworks_case_status() -> dict[str, Any]:
    from fireworks_advisory_v2 import get_case_fireworks_advisory_payload

    def offline_requester(_api_key: str, _payload: dict[str, Any]) -> dict[str, Any]:
        raise TimeoutError("offline demo console summary")

    payload = get_case_fireworks_advisory_payload("no-excursion-control", requester=offline_requester)
    provider = payload["provider"]
    return {
        "caseId": payload["caseId"],
        "displayedAdvisorySource": provider["displayedAdvisorySource"],
        "fireworksCallSucceeded": provider["fireworksCallSucceeded"],
        "fireworksSafetyGatePassed": provider["fireworksSafetyGatePassed"],
        "runtimeExternalServiceRequired": provider["runtimeExternalServiceRequired"],
    }


def get_demo_console_payload() -> dict[str, Any]:
    from fireworks_advisory_v2 import get_fireworks_advisory_payload
    from gpu_research_lab_v2 import get_gpu_research_lab_payload

    gpu = get_gpu_research_lab_payload()
    fireworks = get_fireworks_advisory_payload()
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False,
        "deterministicRulesAuthoritative": True,
        "fireworksOptional": True,
        "artifactAvailable": gpu["artifactAvailable"],
        "gpuArtifactPath": gpu["artifactPath"],
        "fireworksStatus": {
            "phase": fireworks["phase"],
            "status": fireworks["status"],
            "fireworksConfigured": fireworks["fireworksConfigured"],
            "defaultModel": fireworks["defaultModel"],
            "caseCount": len(fireworks["cases"]),
            "caseSummary": _fireworks_case_status(),
        },
        "evidenceSections": [
            {"title": title, "route": route, "summary": summary}
            for title, route, summary in EVIDENCE_SECTIONS
        ],
        "routeMap": dict(ROUTE_MAP),
        "demoNarrative": list(DEMO_NARRATIVE),
        "goNoGoSummary": list(GO_NO_GO_SUMMARY),
        "claimBoundaries": list(CLAIM_BOUNDARIES),
    }


def _json_block(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def render_demo_console_html() -> str:
    payload = get_demo_console_payload()
    sections = "\n".join(
        f'<article class="card"><h2>{html.escape(item["title"])}</h2>'
        f'<p>{html.escape(item["summary"])}</p>'
        f'<a class="button" href="{html.escape(item["route"])}">Open</a></article>'
        for item in payload["evidenceSections"]
    )
    links = "\n".join(
        f'<a class="button" href="{html.escape(route)}">{html.escape(name)}</a>'
        for name, route in payload["routeMap"].items()
    )
    narrative = "\n".join(f"<li>{html.escape(step)}</li>" for step in payload["demoNarrative"])
    boundaries = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["claimBoundaries"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ColdChain Sentinel Demo Evidence Console</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #172026; background: #f6f8f8; line-height: 1.45; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px 16px 44px; }}
    header {{ background: #0d2624; color: #f3fffb; padding: 32px 16px; }}
    header > div {{ max-width: 1180px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(30px, 5vw, 48px); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; }}
    .card, .panel {{ background: #fff; border: 1px solid #d8e2df; border-radius: 16px; padding: 16px; margin: 14px 0; }}
    .badge {{ display: inline-block; margin: 4px 6px 4px 0; padding: 6px 10px; border-radius: 999px; background: #e8f6f1; color: #126354; font-weight: 700; }}
    .button {{ display: inline-block; margin: 5px 6px 5px 0; padding: 8px 12px; border-radius: 10px; background: #146c5f; color: #fff; text-decoration: none; font-weight: 700; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #0b1718; color: #d9fff2; border-radius: 14px; padding: 14px; overflow-x: auto; }}
  </style>
</head>
<body>
<header><div>
  <p><a class="button" href="/command-center">Command Center</a></p>
  <h1>Judge Demo Evidence Console</h1>
  <p>Phase 13 summary for the synthetic ColdChain Sentinel demo story.</p>
  <span class="badge">Synthetic-only</span>
  <span class="badge">Advisory-only</span>
  <span class="badge">Deterministic rules authoritative</span>
  <span class="badge">Fireworks optional</span>
  <span class="badge">Runtime GPU required: false</span>
  <span class="badge">Runtime external service required: false</span>
</div></header>
<main data-testid="demo-console-page">
  <section class="panel">
    <h2>Demo narrative</h2>
    <ol>{narrative}</ol>
  </section>
  <section class="grid">{sections}</section>
  <section class="panel">
    <h2>Routes</h2>
    {links}
  </section>
  <section class="panel">
    <h2>Claim boundaries</h2>
    <ul>{boundaries}</ul>
  </section>
  <section class="panel">
    <h2>Compact JSON evidence preview</h2>
    <pre>{_json_block(payload)}</pre>
  </section>
</main>
</body>
</html>"""
