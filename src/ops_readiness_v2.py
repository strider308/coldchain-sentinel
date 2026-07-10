from __future__ import annotations

import html
import json
from typing import Any

from audit_ledger_v2 import get_audit_ledger_payload
from demo_console_v2 import get_demo_console_payload
from final_validation_packet_v2 import get_final_validation_packet_payload
from fireworks_advisory_v2 import get_fireworks_advisory_payload
from gpu_research_lab_v2 import get_gpu_research_lab_payload
from integration_sandbox_v2 import get_integration_sandbox_payload
from reviewer_workspace_v3 import get_reviewer_workspace_payload
from scenario_lab_v2 import get_scenario_lab_payload


PHASE = "Phase 19 - Ops Readiness and Evidence Health"
STATUS = "READY"

ROUTE_HEALTH = (
    ("Command center", "/command-center"),
    ("Demo console", "/demo-console"),
    ("Final validation packet", "/final-validation"),
    ("Integration sandbox", "/integration-sandbox"),
    ("Evidence audit ledger", "/audit-ledger"),
    ("Reviewer workspace", "/reviewer-workspace"),
    ("Scenario lab", "/scenario-lab"),
    ("Fireworks advisory", "/fireworks-advisory"),
    ("GPU research lab", "/gpu-research-lab"),
)


def get_ops_readiness_payload() -> dict[str, Any]:
    gpu = get_gpu_research_lab_payload()
    fireworks = get_fireworks_advisory_payload()
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False,
        "productionMonitoringClaimed": False,
        "deterministicRulesAuthoritative": True,
        "evidenceHealth": {
            "gpuArtifactAvailable": gpu["artifactAvailable"],
            "fireworksConfigured": fireworks["fireworksConfigured"],
            "fireworksFallbackAvailable": True,
            "demoConsoleAvailable": bool(get_demo_console_payload()),
            "validationPacketAvailable": bool(get_final_validation_packet_payload()),
            "integrationSandboxAvailable": bool(get_integration_sandbox_payload()),
            "auditLedgerAvailable": bool(get_audit_ledger_payload()),
            "reviewerWorkspaceAvailable": bool(get_reviewer_workspace_payload()),
            "scenarioEvidenceAvailable": bool(get_scenario_lab_payload()),
        },
        "routeHealth": [
            {
                "label": label,
                "route": route,
                "expectedAvailable": True,
                "basis": "static expected availability; no HTTP probe",
            }
            for label, route in ROUTE_HEALTH
        ],
        "readinessSummary": {
            "demoEvidenceReady": True,
            "productionOpsReady": False,
            "externalDependenciesRequiredForBoot": False,
            "humanReviewRequiredForOperationalUse": True,
        },
    }


def render_ops_readiness_html() -> str:
    payload = get_ops_readiness_payload()
    cards = "".join(
        f'<article class="card"><h2>{html.escape(name)}</h2><p>{"available" if available else "not configured"}</p></article>'
        for name, available in payload["evidenceHealth"].items()
    )
    rows = "".join(
        f'<tr><th scope="row">{html.escape(row["label"])}</th><td><a href="{html.escape(row["route"])}">{html.escape(row["route"])}</a></td>'
        f'<td>{"expected available" if row["expectedAvailable"] else "not expected"}</td></tr>'
        for row in payload["routeHealth"]
    )
    preview = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ops Readiness and Evidence Health</title><style>
body{{margin:0;background:#07131b;color:#edf7f5;font:16px system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:28px 18px 48px}}
a{{color:#8ee8cb}}.badges,.grid{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}.badge{{border:1px solid #347263;border-radius:999px;padding:7px 11px}}
.card{{flex:1 1 220px;background:#102631;border:1px solid #244852;border-radius:12px;padding:16px}}table{{width:100%;border-collapse:collapse;background:#102631}}
th,td{{padding:11px;text-align:left;border-bottom:1px solid #244852}}pre{{white-space:pre-wrap;word-break:break-word;background:#041016;border-radius:12px;padding:16px;overflow:auto}}
@media(max-width:600px){{main{{padding:20px 12px}}table{{font-size:14px}}}}
</style></head><body><main><p><a href="/">ColdChain Sentinel</a> / <a href="/ops-readiness.json">JSON</a> / <a href="/evidence-health.json">Evidence JSON</a></p>
<h1>Ops Readiness and Evidence Health</h1><p>Evidence health only, not production monitoring.</p>
<div class="badges"><span class="badge">Synthetic-only</span><span class="badge">Advisory-only</span><span class="badge">No runtime GPU</span><span class="badge">No external dependency for boot</span></div>
<section class="grid" aria-label="Evidence health">{cards}</section>
<section><h2>Static route health</h2><table><thead><tr><th>Surface</th><th>Route</th><th>Expected status</th></tr></thead><tbody>{rows}</tbody></table></section>
<section><h2>Payload</h2><pre>{preview}</pre></section>
</main></body></html>"""
