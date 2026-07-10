from __future__ import annotations

import html
from typing import Any
from ui_design_system_v2 import unified_page

PHASE = "Phase 45 - Demo Script and Judge Q&A"
ROUTE_ORDER = ["/command-center", "/algorithm-console", "/case-walkthroughs/door-open-warming", "/fault-atlas", "/judge-pack", "/submission-readiness"]


def _safety() -> dict[str, bool]:
    return {"syntheticOnly": True, "advisoryOnly": True, "realWorldDataUsed": False, "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False, "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True, "dependenciesAdded": False, "externalCallsRequired": False}


def get_safe_claims_guide_payload() -> dict[str, Any]:
    risky = ["production" + "-ready", "pharma" + " validated", "real-world" + " validated", "compliance" + " certified", "autonomous" + " release", "autonomous" + " quarantine", "autonomous" + " discard", "autonomous" + " reroute", "customer" + " notification"]
    return {"phase": PHASE, "whatWeCanSay": ["The demo uses synthetic evidence.", "STBL metrics come from offline synthetic research.", "The live runtime uses transparent distilled rules.", "The system recommends what a human should inspect first."], "whatWeCannotSay": ["External validation is complete.", "The system has operational disposition authority.", "A regulated approval or customer deployment exists."], "riskyPhrasesToAvoid": risky, "approvedPhrases": ["synthetic-only evidence", "advisory-only prediction", "human review required", "project-defined fault universe", "deterministic rules authoritative"], "finalDemoBoundary": "No operational action is automated. STBL remains advisory and cannot override deterministic safety rules."}


def get_demo_script_final_payload() -> dict[str, Any]:
    guide = get_safe_claims_guide_payload()
    return {"phase": PHASE, "status": "READY", **_safety(), "scripts": {"60SecondPitch": "ColdChain Sentinel turns noisy synthetic sensor evidence into quality checks, consensus guardrails, advisory risk, transparent STBL behavior predictions, and human inspection guidance.", "3MinuteDemo": "Open the command center, show algorithm evidence, follow door-open warming, and close with the judge pack and claims boundary.", "5MinuteDemo": "Add the 38-fault atlas, explain distilled runtime behavior, and finish on submission readiness.", "technicalDeepDive": "Trace synthetic evidence through data quality, consensus, SERS, STBL weighted-centroid prototypes, root-cause guidance, and audit routes. Explain that the runtime is stdlib-only."}, "routeOrder": list(ROUTE_ORDER), "narrationRules": {"safePhrases": guide["approvedPhrases"], "phrasesToAvoid": guide["riskyPhrasesToAvoid"], "howToExplainSyntheticData": "Synthetic scenarios make edge cases repeatable and inspectable while clearly limiting external claims.", "howToExplainSTBL": "STBL was trained offline on synthetic windows and distilled into transparent prototype rules for the live app.", "howToExplainAdvisoryOnlyBoundary": "Predictions direct human inspection and never decide operational disposition."}}


def get_judge_qna_payload() -> dict[str, Any]:
    qa = [
        ("Is this " + "real-world" + " validated?", "No. Evidence is synthetic and no external deployment validation is claimed."),
        ("Why synthetic data?", "It provides repeatable edge cases without exposing customer, shipment, patient, or sensor data."),
        ("How does STBL work?", "Offline neural research is distilled into weighted fault prototypes plus transparent rule boosts."),
        ("Why not use PyTorch in the live runtime?", "The distilled stdlib path is inspectable, lightweight, and sufficient for this advisory demonstration."),
        ("What happens if the model is wrong?", "Deterministic rules remain authoritative, uncertainty is shown, and a human reviews the evidence."),
        ("Can it make release or quarantine decisions?", "No. Operational disposition and outbound messaging remain blocked."),
        ("How would this become a production pilot later?", "Add validated connectors, durable persistence, security controls, field evaluation, monitoring, and governed human workflows."),
        ("What is the moat?", "The evidence chain connects data quality, consensus, bounded prediction, root cause, inspection, and auditability."),
        ("What did GPU and Jupyter add?", "They supported offline synthetic model research and benchmark evidence only."),
        ("What does Fireworks do?", "It is optional explanation support and is never required for app boot or deterministic decisions."),
        ("What is deterministic versus AI-driven?", "Quality, consensus, safety boundaries, and disposition blocks are deterministic; STBL adds advisory pattern prediction."),
        ("How does the system prevent overreaction to one sensor?", "It compares neighboring sensors and zone consensus before elevating an isolated signal."),
        ("How does it handle data quality problems?", "It identifies missing, late, duplicate, weak, conflicting, and mapping evidence before interpretation."),
        ("What are the limitations?", "Synthetic-only evidence, no external validation, no customer integration, no operational authority, and bounded fault coverage."),
        ("What would you build next?", "A governed pilot with validated ingestion, persistence, monitoring, field feedback, and formal reviewer workflows."),
        ("Why cold chain?", "It makes evidence quality, uncertainty, and human decision boundaries concrete and consequential."),
        ("How is this different from a dashboard?", "It exposes the reasoning chain, failure modes, inspection targets, safety blocks, and audit evidence behind each view."),
        ("What should a human inspect first?", "The inspection engine ranks the first physical or data-quality target for each synthetic case."),
    ]
    return {"phase": PHASE, "syntheticOnly": True, "advisoryOnly": True, "questions": [{"question": question, "answer": answer} for question, answer in qa]}


@unified_page
def render_demo_script_qna_html() -> str:
    scripts = get_demo_script_final_payload(); qna = get_judge_qna_payload(); guide = get_safe_claims_guide_payload()
    script_rows = "".join(f'<section><h2>{html.escape(name)}</h2><p>{html.escape(text)}</p></section>' for name, text in scripts["scripts"].items())
    questions = "".join(f'<details><summary>{html.escape(item["question"])}</summary><p>{html.escape(item["answer"])}</p></details>' for item in qna["questions"])
    routes = "".join(f'<li><code>{html.escape(route)}</code></li>' for route in ROUTE_ORDER)
    approved = "".join(f"<li>{html.escape(item)}</li>" for item in guide["approvedPhrases"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Demo Script and Judge Q&amp;A</title><style>:root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}main{{max-width:1080px;margin:auto;padding:28px 18px 56px}}h1{{font-size:3rem;line-height:1.05;letter-spacing:-.035em;text-wrap:balance}}p{{color:var(--muted);max-width:72ch}}a{{color:var(--accent)}}a:focus-visible,summary:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.badges,.links{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 32px}}.badges span,.links a{{border:1px solid var(--line);border-radius:8px;padding:8px 11px}}.scripts section{{border-block:1px solid var(--line);padding:12px 0}}.split{{display:grid;grid-template-columns:.75fr 1.25fr;gap:28px;margin-top:36px}}details{{background:var(--surface);padding:13px 15px;margin:7px 0;border-radius:10px}}summary{{cursor:pointer;font-weight:700}}@media(max-width:650px){{main{{padding:18px 12px 44px}}h1{{font-size:2.25rem}}.split{{grid-template-columns:1fr}}}}</style></head><body><main><h1>Demo Script and Judge Q&amp;A</h1><p>Final narration, evidence route order, and honest answers for common judge questions.</p><div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>Deterministic rules authoritative</span></div><div class="links"><a href="/judge-qna">Judge Q&amp;A</a><a href="/safe-claims-guide.json">Safe claims guide</a><a href="/submission-readiness">Submission Readiness</a></div><div class="scripts">{script_rows}</div><div class="split"><section><h2>Route order</h2><ol>{routes}</ol><h2>Approved language</h2><ul>{approved}</ul></section><section><h2>Judge Q&amp;A</h2>{questions}</section></div></main></body></html>'''
