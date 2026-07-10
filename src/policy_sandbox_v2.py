from __future__ import annotations
import html
from typing import Any
PHASE="Phase 25 - SOP Policy Knowledge Sandbox"
SOP="""# Synthetic Temperature Review SOP

When synthetic evidence is incomplete or conflicting, request more evidence and keep the case in human review. Advisory scores never change deterministic facts.
"""
MAPPING={"policyId":"SYN-SOP-001","syntheticPolicyText":"Incomplete or conflicting evidence requires review.","mappedReviewRule":"block workflow completion until a human reviews evidence quality","relatedEvidenceRoute":"/evaluation-matrix-v2","humanReviewerMeaning":"inspect quality, consensus, and missing evidence","automationBoundary":"static advisory mapping only; no operational action"}
def get_policy_sandbox_payload()->dict[str,Any]:
 return {"phase":PHASE,"status":"READY","syntheticOnly":True,"advisoryOnly":True,"runtimeGpuRequired":False,"runtimeExternalServiceRequired":False,"deterministicRulesAuthoritative":True,"autonomousActionsAllowed":False,"realSopUsed":False,"vectorDatabaseRequired":False,"retrievalRuntimeRequired":False,"sampleSyntheticSopMarkdown":SOP,"policyMapping":MAPPING,"policyBoundaries":["synthetic SOP only","no real customer policy","no legal/compliance certification","no automatic operational action"],"routeMap":{"reviewerWorkspace":"/reviewer-workspace","auditLedger":"/audit-ledger","evaluationMatrixV2":"/evaluation-matrix-v2","productionGapAnalysis":"/production-gap-analysis","policySandbox":"/policy-sandbox"}}
def get_policy_mapping_payload()->dict[str,Any]: return {"syntheticOnly":True,"policyMapping":MAPPING}
def render_policy_sandbox_html()->str:
 rows=f'<tr><th>{html.escape(MAPPING["policyId"])}</th><td>{html.escape(MAPPING["mappedReviewRule"])}</td><td>{html.escape(MAPPING["humanReviewerMeaning"])}</td></tr>'
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Policy Sandbox</title><style>body{{font:16px system-ui;background:#07131b;color:#eef;padding:24px}}pre,table{{background:#102631;padding:16px}}th,td{{padding:10px;text-align:left}}</style></head><body><h1>SOP Policy Knowledge Sandbox</h1><p>Policy sandbox only, no real SOP ingestion.</p><pre>{html.escape(SOP)}</pre><table><tbody>{rows}</tbody></table></body></html>'''
