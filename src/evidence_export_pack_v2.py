from __future__ import annotations
import html
from typing import Any

PHASE="Phase 24 - Evidence Export Pack"
ROUTES=["/","/command-center","/sensor-lab","/data-pipeline","/consensus","/sers","/training-lab","/scenario-lab","/review-workbench","/incident-replay","/integration-readiness","/gpu-research-lab","/fireworks-advisory","/demo-console","/final-validation","/integration-sandbox","/audit-ledger","/reviewer-workspace","/fireworks-coverage","/ops-readiness","/production-gap-analysis","/expanded-benchmark","/scenario-library-v4","/evaluation-matrix-v2"]
SUMMARY="""# ColdChain Sentinel Evidence Export

Completed phases expose synthetic, advisory evidence through static routes.

## Boundaries
Deterministic rules remain authoritative. Human review is required. Evidence does not establish real deployment validation.

## Key routes
"""+"\n".join(f"- `{r}`" for r in ROUTES)+"\n\n## Known non-goals\nNo real data, secrets, raw datasets, or operational automation.\n"

def get_evidence_export_payload()->dict[str,Any]:
 return {"phase":PHASE,"status":"READY","syntheticOnly":True,"advisoryOnly":True,"runtimeGpuRequired":False,"runtimeExternalServiceRequired":False,"deterministicRulesAuthoritative":True,"autonomousActionsAllowed":False,"exportFormats":["html","json","markdown","route-manifest"],"summaryMarkdown":SUMMARY,"routeManifest":[{"route":r,"expectedAvailable":True} for r in ROUTES],"evidenceSections":["command center","expanded benchmark","scenario library","evaluation matrix","integration sandbox","audit ledger","reviewer workspace","Fireworks advisory","ops readiness","gap analysis","final validation"],"exportBoundaries":["no secrets","no raw data","no notebook outputs required","no real data"],"routeMap":{"evidenceExport":"/evidence-export","summaryMarkdown":"/evidence-export/summary.md","routeManifest":"/evidence-export/routes.json"}}

def get_evidence_route_manifest_payload()->dict[str,Any]: return {"syntheticOnly":True,"routes":get_evidence_export_payload()["routeManifest"]}
def render_evidence_export_html()->str:
 p=get_evidence_export_payload(); routes="".join(f'<li>{html.escape(x["route"])}</li>' for x in p["routeManifest"])
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence Export</title><style>body{{font:16px system-ui;background:#07131b;color:#eef;padding:24px}}a{{color:#9ed}}pre,.card{{background:#102631;padding:16px;border-radius:12px;white-space:pre-wrap}}</style></head><body><h1>Evidence Export Pack</h1><p>Synthetic-only advisory evidence; deterministic rules remain authoritative.</p><p><a href="/evidence-export.json">JSON</a> <a href="/evidence-export/summary.md">Markdown</a> <a href="/evidence-export/routes.json">Route manifest</a></p><pre>{html.escape(p["summaryMarkdown"])}</pre><section class="card"><ul>{routes}</ul></section></body></html>'''
