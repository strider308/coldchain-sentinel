from __future__ import annotations

import html
import json
from typing import Any

PHASE = "Phase 14 - Final Validation Evidence Packet"
STATUS = "DEMO_READY_NOT_PRODUCTION_VALIDATED"

REQUIRED_LOCAL_COMMANDS = [
    "python -m pytest -p no:cacheprovider tests/test_demo_console_v2.py tests/test_final_validation_packet_v2.py tests/test_fireworks_advisory_v2.py tests/test_gpu_research_lab_v2.py tests/test_human_review_workbench_v2.py tests/test_incident_replay_v2.py tests/test_integration_readiness_v2.py tests/test_scenario_lab_v2.py tests/test_training_lab_v2.py",
    "python tests/test_coldchain_validation.py",
    "python src/serve_dashboard_amd.py --check",
]

REQUIRED_LIVE_ROUTES = [
    "/demo-console",
    "/demo-console.json",
    "/judge-evidence",
    "/judge-evidence.json",
    "/final-validation",
    "/final-validation.json",
    "/validation-packet",
    "/validation-packet.json",
    "/gpu-research-lab.json",
    "/fireworks-advisory.json",
    "/cases/no-excursion-control/fireworks-advisory.json",
]


def get_final_validation_packet_payload() -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "productionValidated": False,
        "pharmaValidated": False,
        "realWorldValidated": False,
        "complianceCertified": False,
        "autonomousActionsAllowed": False,
        "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False,
        "deterministicRulesAuthoritative": True,
        "validationScope": [
            "local route smoke",
            "pytest-compatible suites",
            "script-style coldchain validation",
            "dashboard self-check",
            "live route smoke after manual Render deploy",
            "Fireworks optional safety-gated route",
            "GPU artifact ingestion",
        ],
        "requiredLocalCommands": list(REQUIRED_LOCAL_COMMANDS),
        "requiredLiveRoutes": list(REQUIRED_LIVE_ROUTES),
        "releaseReadiness": {
            "demoReady": True,
            "productionReady": False,
            "privateBetaReady": False,
            "needsOwnerManualRenderDeploy": True,
            "needsHumanReviewForOperationalUse": True,
        },
        "evidenceIntegrity": {
            "noSecretsExpected": True,
            "generatedArtifactAllowed": "artifacts/gpu_synthetic_research_summary.json",
            "rawDataCommitted": False,
            "notebookOutputsRequired": False,
        },
        "nonGoals": [
            "regulated pharma validation",
            "production deployment validation",
            "real shipment/customer validation",
            "compliance certification",
            "autonomous operational actioning",
            "customer messaging automation",
        ],
        "routeMap": {
            "demoConsole": "/demo-console",
            "commandCenter": "/command-center",
            "finalValidation": "/final-validation",
            "validationPacket": "/validation-packet",
        },
    }


def _json_block(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def render_final_validation_packet_html() -> str:
    payload = get_final_validation_packet_payload()
    commands = "\n".join(f"<li><code>{html.escape(command)}</code></li>" for command in payload["requiredLocalCommands"])
    routes = "\n".join(f'<li><a href="{html.escape(route)}">{html.escape(route)}</a></li>' for route in payload["requiredLiveRoutes"])
    scope = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["validationScope"])
    non_goals = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["nonGoals"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ColdChain Sentinel Final Validation Packet</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #162125; background: #fbfcfc; line-height: 1.45; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 28px 16px 46px; }}
    .hero, .panel {{ border: 1px solid #d8e2df; border-radius: 16px; padding: 18px; margin: 14px 0; background: #fff; }}
    .hero {{ background: #102129; color: #f3fffb; }}
    .badge {{ display: inline-block; margin: 4px 6px 4px 0; padding: 6px 10px; border-radius: 999px; background: #e8f6f1; color: #126354; font-weight: 700; }}
    .button {{ display: inline-block; margin: 5px 6px 5px 0; padding: 8px 12px; border-radius: 10px; background: #146c5f; color: #fff; text-decoration: none; font-weight: 700; }}
    code {{ word-break: break-word; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #0b1718; color: #d9fff2; border-radius: 14px; padding: 14px; overflow-x: auto; }}
  </style>
</head>
<body>
<main data-testid="final-validation-page">
  <section class="hero">
    <h1>Demo-ready evidence packet, not production validation</h1>
    <p>Phase 14 captures local and live-demo evidence requirements without expanding the claim boundary.</p>
    <span class="badge">Synthetic-only</span>
    <span class="badge">Advisory-only</span>
    <span class="badge">Production validated: false</span>
    <span class="badge">Pharma validation: false</span>
    <span class="badge">Real-world validation: false</span>
    <span class="badge">Compliance certification: false</span>
    <span class="badge">Autonomous actions allowed: false</span>
    <span class="badge">Runtime GPU required: false</span>
    <span class="badge">Runtime external service required: false</span>
  </section>
  <section class="panel">
    <a class="button" href="/demo-console">Demo Console</a>
    <a class="button" href="/command-center">Command Center</a>
  </section>
  <section class="panel"><h2>Validation scope</h2><ul>{scope}</ul></section>
  <section class="panel"><h2>Local validation commands</h2><ol>{commands}</ol></section>
  <section class="panel"><h2>Live routes after manual Render deploy</h2><ul>{routes}</ul></section>
  <section class="panel"><h2>Non-goals</h2><ul>{non_goals}</ul></section>
  <section class="panel"><h2>JSON evidence preview</h2><pre>{_json_block(payload)}</pre></section>
</main>
</body>
</html>"""
