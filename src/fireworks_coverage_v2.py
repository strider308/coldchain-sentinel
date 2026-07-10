"""Static Fireworks advisory route coverage for synthetic cases."""

import html
import json
import os
from typing import Any

from fireworks_advisory_v2 import CASE_IDS, DEFAULT_MODEL


PHASE = "Phase 18 - Fireworks Multi-Case Advisory Coverage"
STATUS = "READY"


def get_fireworks_coverage_payload() -> dict[str, Any]:
    """Describe single-case route coverage without calling Fireworks."""
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
        "runtimeGpuRequired": False,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
        "fireworksOptional": True,
        "configured": bool(os.environ.get("FIREWORKS_API_KEY")),
        "knownWorkingModel": os.environ.get("FIREWORKS_MODEL") or DEFAULT_MODEL,
        "defaultCoverageMode": "route-available-no-bulk-external-call",
        "bulkExternalCallsMade": False,
        "coverageRows": [
            {
                "caseId": case_id,
                "advisoryRoute": f"/cases/{case_id}/fireworks-advisory.json",
                "deterministicFallbackAvailable": True,
                "safetyGateRequired": True,
                "deterministicRulesAuthoritative": True,
                "expectedSourceWhenNoKey": "deterministic_fallback",
                "expectedSourceWhenAccepted": "fireworks_safety_gated_json",
            }
            for case_id in CASE_IDS
        ],
        "routeMap": {
            "fireworksAdvisory": "/fireworks-advisory",
            "fireworksModelCard": "/fireworks-model-card",
            "demoConsole": "/demo-console",
            "reviewerWorkspace": "/reviewer-workspace",
        },
    }


def render_fireworks_coverage_html() -> str:
    payload = get_fireworks_coverage_payload()
    rows = "\n".join(
        f"""<tr>
  <td>{html.escape(row["caseId"])}</td>
  <td><a href="{html.escape(row["advisoryRoute"])}">{html.escape(row["advisoryRoute"])}</a></td>
  <td>Available</td>
  <td>Required</td>
</tr>"""
        for row in payload["coverageRows"]
    )
    evidence = html.escape(json.dumps(payload, indent=2, sort_keys=True))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fireworks Multi-Case Advisory Coverage</title>
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #071014; color: #eef7f2; }}
    main {{ max-width: 1160px; margin: 0 auto; padding: 32px 20px 56px; }}
    a {{ color: #96e6b3; }}
    .card {{ background: #102129; border: 1px solid #21414d; border-radius: 18px; padding: 20px; margin: 18px 0; }}
    .badge {{ display: inline-block; border: 1px solid #315c6d; border-radius: 999px; padding: 5px 9px; margin: 4px 5px 4px 0; color: #c8f7dc; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #21414d; padding: 12px 8px; text-align: left; vertical-align: top; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #071014; border: 1px solid #21414d; border-radius: 14px; padding: 16px; overflow-x: auto; }}
  </style>
</head>
<body>
<main>
  <p><a href="/">ColdChain Sentinel</a> · <a href="/fireworks-coverage.json">JSON</a></p>
  <h1>Fireworks Multi-Case Advisory Coverage</h1>
  <p>Static synthetic advisory route coverage. Deterministic rules remain authoritative, and each advisory requires human review.</p>
  <section class="card" aria-label="Safety boundaries">
    <span class="badge">Synthetic-only</span>
    <span class="badge">Advisory-only</span>
    <span class="badge">Fireworks optional</span>
    <span class="badge">Fallback available</span>
    <span class="badge">No bulk external calls</span>
  </section>
  <section class="card">
    <h2>Single-case advisory routes</h2>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Case</th><th>Advisory route</th><th>Fallback</th><th>Safety gate</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </section>
  <section class="card">
    <h2>Machine-readable evidence</h2>
    <pre>{evidence}</pre>
  </section>
</main>
</body>
</html>"""
