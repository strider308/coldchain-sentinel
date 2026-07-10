from __future__ import annotations

import html
import json
from typing import Any


PHASE = "Phase 17 - Reviewer Workspace v3"
STATUS = "READY"
CASE_IDS = (
    "no-excursion-control",
    "single-sensor-spike",
    "multi-sensor-confirmed-warming",
    "unresolved-mapping-risk",
    "door-open-warming",
    "dropout-weak-signal",
)
REVIEWER_WORKFLOW_STATES = (
    "needs review",
    "evidence incomplete",
    "mapping review needed",
    "sensor trust review needed",
    "synthetic false alarm candidate",
    "synthetic escalation candidate",
)
ALLOWED_REVIEWER_ACTIONS = (
    "inspect",
    "annotate",
    "request evidence",
    "mark review status",
)
BLOCKED_ACTIONS = (
    "release",
    "quarantine",
    "discard",
    "reroute",
    "customer messaging",
)
CASE_REVIEW = {
    "no-excursion-control": ("synthetic false alarm candidate", "low"),
    "single-sensor-spike": ("sensor trust review needed", "medium"),
    "multi-sensor-confirmed-warming": ("synthetic escalation candidate", "high"),
    "unresolved-mapping-risk": ("mapping review needed", "high"),
    "door-open-warming": ("needs review", "medium"),
    "dropout-weak-signal": ("evidence incomplete", "medium"),
}


def _boundaries() -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
        "runtimeGpuRequired": False,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
        "databaseRequired": False,
    }


def _case_route(case_id: str) -> str:
    return f"/reviewer-workspace/{case_id}.json"


def _workspace(case_id: str) -> dict[str, Any]:
    review_status, priority = CASE_REVIEW[case_id]
    return {
        "caseId": case_id,
        "reviewStatus": review_status,
        "priority": priority,
        "evidenceTabs": [
            {"label": "Audit ledger", "route": f"/cases/{case_id}/audit-ledger.json"},
            {"label": "Incident replay", "route": f"/incident-replay/{case_id}.json"},
            {"label": "Human review packet", "route": f"/review-workbench/{case_id}.json"},
            {"label": "SERS advisory", "route": f"/cases/{case_id}/risk-timeline.json"},
            {"label": "Fireworks advisory", "route": f"/cases/{case_id}/fireworks-advisory.json"},
        ],
        "checklist": [
            {"item": "Inspect the synthetic evidence tabs", "status": "incomplete"},
            {"item": "Annotate conflicts or missing evidence", "status": "incomplete"},
            {"item": "Record a human review status", "status": "incomplete"},
        ],
        "suggestedReviewerNotes": [
            f"Review the deterministic evidence for {case_id}.",
            "Document uncertainty without changing deterministic findings.",
        ],
        "blockedActions": list(BLOCKED_ACTIONS),
        "allowedReviewerActions": list(ALLOWED_REVIEWER_ACTIONS),
        "routeLinks": {
            "auditLedger": f"/cases/{case_id}/audit-ledger.json",
            "incidentReplay": f"/incident-replay/{case_id}.json",
            "humanReviewWorkbench": f"/review-workbench/{case_id}.json",
            "sers": f"/cases/{case_id}/risk-timeline.json",
            "fireworksAdvisory": f"/cases/{case_id}/fireworks-advisory.json",
        },
    }


def get_case_reviewer_workspace_payload(case_id: str) -> dict[str, Any]:
    if case_id not in CASE_IDS:
        raise KeyError(case_id)
    return {
        **_boundaries(),
        "reviewerWorkflowStates": list(REVIEWER_WORKFLOW_STATES),
        "caseWorkspace": _workspace(case_id),
        "boundary": "Static synthetic reviewer workflow, no operational action.",
    }


def get_reviewer_workspace_payload() -> dict[str, Any]:
    workspaces = [_workspace(case_id) for case_id in CASE_IDS]
    return {
        **_boundaries(),
        "reviewerWorkflowStates": list(REVIEWER_WORKFLOW_STATES),
        "caseWorkspace": workspaces[0],
        "caseWorkspaces": workspaces,
        "routeMap": {
            "reviewerWorkspace": "/reviewer-workspace",
            "reviewerWorkspaceJson": "/reviewer-workspace.json",
            **{case_id: _case_route(case_id) for case_id in CASE_IDS},
        },
        "boundary": "Static synthetic reviewer workflow, no operational action.",
    }


def render_reviewer_workspace_html() -> str:
    payload = get_reviewer_workspace_payload()
    cards = "".join(
        f'<article class="card"><p class="priority">{html.escape(item["priority"])}</p>'
        f'<h2>{html.escape(item["caseId"])}</h2><p>{html.escape(item["reviewStatus"])}</p>'
        f'<a href="{html.escape(_case_route(item["caseId"]))}">Open case JSON</a></article>'
        for item in payload["caseWorkspaces"]
    )
    checklist = "".join(
        f'<li><span aria-hidden="true">&#9744;</span> {html.escape(item["item"])}</li>'
        for item in payload["caseWorkspace"]["checklist"]
    )
    preview = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reviewer Workspace v3</title><style>
body{{margin:0;background:#07131b;color:#edf7f5;font:16px system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:28px 18px 48px}}
a{{color:#8ee8cb}}.badges,.queue{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}.badge{{border:1px solid #347263;border-radius:999px;padding:7px 11px}}
.card{{flex:1 1 280px;background:#102631;border:1px solid #244852;border-radius:12px;padding:16px}}.priority{{color:#8ee8cb;text-transform:uppercase;font-weight:700}}
.checklist,.preview{{background:#041016;border-radius:12px;padding:16px}}.checklist li{{list-style:none;margin:10px 0}}pre{{white-space:pre-wrap;word-break:break-word;overflow:auto}}
@media(max-width:600px){{main{{padding:20px 12px}}}}
</style></head><body><main><p><a href="/">ColdChain Sentinel</a> / <a href="/reviewer-workspace.json">JSON</a></p>
<h1>Reviewer Workspace v3</h1><p>Static synthetic reviewer workflow, no operational action.</p>
<div class="badges"><span class="badge">Synthetic-only</span><span class="badge">Advisory-only</span><span class="badge">No database</span><span class="badge">Deterministic rules authoritative</span></div>
<section class="queue" aria-label="Reviewer queue">{cards}</section>
<section class="checklist"><h2>Reviewer checklist</h2><ul>{checklist}</ul></section>
<section class="preview"><h2>Workspace JSON preview</h2><pre>{preview}</pre></section>
</main></body></html>"""
