from __future__ import annotations

import html
from typing import Any

from decision_simulator_v2 import get_decision_simulator_payload
from evaluation_matrix_v2 import get_evaluation_matrix_payload
from expanded_benchmark_v2 import get_expanded_benchmark_payload
from fireworks_coverage_v2 import get_fireworks_coverage_payload
from route_reliability_v2 import get_route_reliability_payload
from scenario_library_v4 import get_scenario_library_payload


PHASE = "Phase 33 - Screenshot-Worthy Command Center Upgrade"


def _readiness_score() -> dict[str, Any]:
    scenarios = get_scenario_library_payload()
    matrix = get_evaluation_matrix_payload()
    reliability = get_route_reliability_payload()
    simulator = get_decision_simulator_payload()
    benchmark = get_expanded_benchmark_payload()
    fireworks = get_fireworks_coverage_payload()
    inputs = {
        "scenarioCoverage": scenarios["scenarioCount"] >= 14,
        "evidenceCompleteness": len(matrix["matrixRows"]) >= scenarios["scenarioCount"],
        "fallbackReadiness": reliability["safeModeAvailable"],
        "humanReviewCoverage": len(simulator["simulatorCases"]) >= scenarios["scenarioCount"],
        "gpuArtifactAvailability": benchmark["artifactAvailable"],
        "fireworksSafetyPosture": all(row["deterministicFallbackAvailable"] for row in fireworks["coverageRows"]),
    }
    weights = (24, 18, 17, 16, 11, 9)
    score = sum(weight for weight, ready in zip(weights, inputs.values()) if ready)
    return {
        "label": "Sentinel Readiness Score",
        "score": score,
        "band": "READY" if score >= 85 else "WATCH" if score >= 70 else "REVIEW",
        "meaning": "Weighted synthetic evidence coverage, fallback posture, and human-review readiness.",
        "inputs": inputs,
        "notOperationalScore": True,
        "syntheticOnly": True,
        "advisoryOnly": True,
    }


def get_dashboard_strategy_payload() -> dict[str, Any]:
    score = _readiness_score()
    return {
        "phase": PHASE,
        "status": "READY",
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
        "dashboardRole": "product-home-screen",
        "polishOnly": False,
        "architectureChanged": False,
        "dependenciesAdded": False,
        "sentinelReadinessScore": score,
        "evidenceConfidencePulse": {
            "label": "Evidence Confidence Pulse",
            "value": "HIGH" if score["score"] >= 85 else "REVIEW",
            "meaning": "Coverage and completeness of committed synthetic evidence, not certainty about real conditions.",
            "syntheticOnly": True,
            "notRealWorldConfidence": True,
        },
        "whatNext": [
            {"title": "Start the final demo flow", "priority": "primary", "action": "Open guided flow", "targetRoute": "/demo-flow", "whyItMatters": "Presents the evidence story in a repeatable order.", "ownerMeaning": "Use this as the default presentation path."},
            {"title": "Review scenario coverage", "priority": "high", "action": "Open scenario library", "targetRoute": "/scenario-library-v4", "whyItMatters": "Shows breadth across fourteen deterministic synthetic families.", "ownerMeaning": "Confirm the audience sees edge-case coverage."},
            {"title": "Inspect evaluation matrix", "priority": "high", "action": "Compare outcomes", "targetRoute": "/evaluation-matrix-v2", "whyItMatters": "Connects data quality, consensus, risk, and review behavior.", "ownerMeaning": "Use it to answer cross-scenario questions."},
            {"title": "Check decision simulator", "priority": "supporting", "action": "Open simulator", "targetRoute": "/decision-simulator", "whyItMatters": "Makes the human-review boundary tangible.", "ownerMeaning": "Show what reviewers can and cannot do."},
            {"title": "Open final validation packet", "priority": "supporting", "action": "Inspect evidence", "targetRoute": "/final-validation", "whyItMatters": "Summarizes local validation and explicit limitations.", "ownerMeaning": "Use before the final QA gate."},
            {"title": "Inspect production gap analysis", "priority": "supporting", "action": "Review gaps", "targetRoute": "/production-gap-analysis", "whyItMatters": "Keeps deployment claims bounded and honest.", "ownerMeaning": "Close with what remains before real use."},
        ],
        "syntheticLiveView": {
            "description": "Deterministic synthetic activity, not live shipment telemetry.",
            "liveDataClaimed": False,
            "syntheticActivityOnly": True,
            "activityDots": [
                {"region": "Zone A", "scenario": "multi-sensor confirmed warming", "signal": "agreement rising", "currentState": "review priority", "linkedRoute": "/scenario-library-v4/multi-sensor-confirmed-warming.json"},
                {"region": "Zone B", "scenario": "single-sensor spike", "signal": "isolated outlier", "currentState": "guardrail active", "linkedRoute": "/scenario-library-v4/single-sensor-spike.json"},
                {"region": "Gateway East", "scenario": "late-arriving data", "signal": "arrival lag", "currentState": "evidence incomplete", "linkedRoute": "/scenario-library-v4/late-arriving-data.json"},
                {"region": "Zone C", "scenario": "no-excursion control", "signal": "stable consensus", "currentState": "watch", "linkedRoute": "/scenario-library-v4/no-excursion-control.json"},
            ],
        },
        "demoHighlights": [
            {"title": "Expanded scenarios covered", "highlightType": "coverage", "value": "14", "route": "/scenario-library-v4", "whyItMatters": "Broad deterministic scenario evidence."},
            {"title": "Evaluation rows available", "highlightType": "evidence", "value": "14", "route": "/evaluation-matrix-v2", "whyItMatters": "Comparable behavior across the full library."},
            {"title": "Safety fallback posture", "highlightType": "safety", "value": "AVAILABLE", "route": "/route-reliability", "whyItMatters": "Optional services do not block the evidence path."},
            {"title": "Fireworks safety posture", "highlightType": "explanation", "value": "GATED", "route": "/llm-advisory-eval", "whyItMatters": "Unsafe or unavailable output falls back deterministically."},
            {"title": "GPU artifact", "highlightType": "research", "value": "INGESTED", "route": "/expanded-benchmark", "whyItMatters": "Offline benchmark evidence is visible without runtime GPU."},
            {"title": "Runtime external service", "highlightType": "runtime", "value": "NOT REQUIRED", "route": "/ops-readiness", "whyItMatters": "The live app boots from committed static evidence."},
        ],
        "whyLayer": {
            "title": "Why this needs review",
            "diagnosticPrompt": "Explain the strongest evidence, uncertainty, and next human-review question.",
            "deterministicExplanation": "Quality, consensus, and mapping evidence determine the review posture. Optional explanation never changes those facts.",
            "fireworksOptional": True,
            "fallbackAvailable": True,
            "route": "/llm-advisory-eval",
            "noExternalCallFromDashboard": True,
        },
        "narrativeCards": [
            "Messy synthetic sensor data becomes a clear advisory signal.",
            "A single-sensor spike does not trigger overreaction.",
            "Human review blocks operational action.",
            "Fireworks explains but does not decide.",
            "GPU and Jupyter evidence supports offline benchmarking only.",
            "Production gap analysis keeps claims honest.",
        ],
        "screenshotWorthyChecklist": {
            "utilityCheck": {"passed": True, "evidence": "Clear next actions and internal routes.", "route": "/demo-flow"},
            "identityCheck": {"passed": True, "evidence": "Sentinel Readiness Score names the product posture.", "route": "/dashboard-strategy"},
            "visualCheck": {"passed": True, "evidence": "Asymmetric hero, highlights, activity, and recap hierarchy.", "route": "/screenshot-worthy-dashboard"},
            "formatCheck": {"passed": True, "evidence": "Highlights and narratives replace a raw data dump.", "route": "/evaluation-matrix-v2"},
            "whyCheck": {"passed": True, "evidence": "Deterministic diagnostic explanation with optional AI link.", "route": "/llm-advisory-eval"},
        },
        "routeMap": {
            "commandCenter": "/command-center", "dashboardStrategy": "/dashboard-strategy", "screenshotWorthyDashboard": "/screenshot-worthy-dashboard",
            "demoFlow": "/demo-flow", "demoNavigation": "/demo-navigation", "demoFreeze": "/demo-freeze", "scenarioLibraryV4": "/scenario-library-v4",
            "evaluationMatrixV2": "/evaluation-matrix-v2", "expandedBenchmark": "/expanded-benchmark", "fireworksAdvisory": "/fireworks-advisory",
            "llmAdvisoryEval": "/llm-advisory-eval", "decisionSimulator": "/decision-simulator", "partnerApiContract": "/partner-api-contract",
            "finalValidation": "/final-validation", "productionGapAnalysis": "/production-gap-analysis",
            "algorithmConsole": "/algorithm-console", "commandCenterAlgorithm": "/command-center-algorithm",
            "behaviorPredictor": "/behavior-predictor", "inspectionEngine": "/inspection-engine",
            "judgePack": "/judge-pack", "largeScaleDataLab": "/large-scale-data-lab",
            "faultAtlas": "/fault-atlas", "caseWalkthroughs": "/case-walkthroughs",
        },
    }


def render_dashboard_strategy_html() -> str:
    payload = get_dashboard_strategy_payload()
    score = payload["sentinelReadinessScore"]
    actions = "".join(f'<a class="action" href="{html.escape(x["targetRoute"])}"><strong>{html.escape(x["title"])}</strong><span>{html.escape(x["whyItMatters"])}</span></a>' for x in payload["whatNext"])
    activity = "".join(f'<a class="activity" href="{html.escape(x["linkedRoute"])}"><small>{html.escape(x["region"])}</small><strong>{html.escape(x["scenario"])}</strong><span>{html.escape(x["signal"])} / {html.escape(x["currentState"])}</span></a>' for x in payload["syntheticLiveView"]["activityDots"])
    highlights = "".join(f'<a class="highlight" href="{html.escape(x["route"])}"><strong>{html.escape(x["value"])}</strong><span>{html.escape(x["title"])}</span><small>{html.escape(x["whyItMatters"])}</small></a>' for x in payload["demoHighlights"])
    narratives = "".join(f'<article>{html.escape(x)}</article>' for x in payload["narrativeCards"])
    checks = "".join(f'<a href="{html.escape(x["route"])}"><strong>{html.escape(name.replace("Check", ""))}</strong><span>{html.escape(x["evidence"])}</span></a>' for name, x in payload["screenshotWorthyChecklist"].items())
    routes = "".join(f'<a href="{html.escape(route)}">{html.escape(name)}</a>' for name, route in payload["routeMap"].items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ColdChain Sentinel Command Center</title><style>
:root{{--bg:#07110f;--surface:#0d1c19;--surface-2:#122722;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:14px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1220px,100%);margin:auto;padding:22px 18px 64px}}a{{color:inherit;text-decoration:none}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}a:active{{transform:translateY(1px)}}.hero{{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(280px,.7fr);gap:18px;min-height:430px;align-items:stretch}}.hero-copy,.score-card,.panel,.why{{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}}.hero-copy{{display:flex;flex-direction:column;justify-content:space-between;padding:clamp(24px,5vw,58px)}}.hero h1{{font-size:clamp(42px,7vw,78px);line-height:.96;letter-spacing:-.055em;max-width:780px;margin:0}}.hero p{{max-width:55ch;color:var(--muted);font-size:18px;margin:18px 0 0}}.hero-nav{{display:flex;flex-wrap:wrap;gap:10px;margin-top:28px}}.button,.hero-nav a,.routes a{{display:inline-block;border:1px solid var(--line);border-radius:10px;padding:10px 14px;color:var(--ink);white-space:nowrap}}.button.primary,.hero-nav a:first-child{{background:var(--accent);border-color:var(--accent);color:#06110e;font-weight:800}}.score-card{{padding:28px;display:flex;flex-direction:column;justify-content:space-between;background:var(--accent);color:#06110e}}.score-card .number{{font-size:clamp(88px,13vw,156px);font-weight:850;letter-spacing:-.08em;line-height:.8}}.score-card h2{{font-size:22px;margin:28px 0 4px}}.score-card p{{color:#173c31;font-size:15px}}.badges{{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0 30px}}.badges span{{border:1px solid var(--line);border-radius:10px;padding:6px 9px;color:var(--muted);font-size:13px}}section{{margin-top:52px}}section>h2{{font-size:clamp(27px,4vw,44px);letter-spacing:-.035em;margin:0 0 8px}}.section-note{{color:var(--muted);max-width:62ch;margin:0 0 20px}}.actions{{display:grid;grid-template-columns:1.2fr .8fr;gap:10px}}.action{{padding:18px;border-radius:var(--radius);background:var(--surface);border:1px solid var(--line);display:flex;flex-direction:column;min-height:124px}}.action:first-child{{grid-row:span 2;background:var(--surface-2);min-height:258px;justify-content:flex-end}}.action strong{{font-size:19px}}.action span,.activity span,.highlight small,.checklist span{{color:var(--muted);margin-top:8px}}.live-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.activity{{padding:16px;border-left:3px solid var(--accent);background:var(--surface);min-height:140px;display:flex;flex-direction:column}}.activity small{{color:var(--accent)}}.activity strong{{margin-top:auto}}.highlights{{display:grid;grid-template-columns:repeat(6,1fr);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}}.highlight{{padding:20px;border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:170px}}.highlight:last-child{{border:0}}.highlight strong{{font-size:24px;color:var(--accent)}}.why{{padding:28px;display:grid;grid-template-columns:1fr 1.5fr;gap:28px}}.why h2{{margin:0;font-size:34px}}.why p{{margin:0;color:var(--muted)}}.stories{{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px}}.stories article{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:22px;min-height:125px;font-size:18px}}.stories article:first-child{{grid-row:span 2;font-size:28px;display:flex;align-items:flex-end;background:var(--surface-2)}}.checklist{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.checklist a{{border-top:3px solid var(--accent);padding:16px;background:var(--surface);display:flex;flex-direction:column;min-height:130px}}.routes{{display:flex;flex-wrap:wrap;gap:8px}}@media(max-width:850px){{.hero,.why{{grid-template-columns:1fr}}.hero{{min-height:auto}}.actions,.live-grid,.highlights,.stories,.checklist{{grid-template-columns:1fr 1fr}}.action:first-child,.stories article:first-child{{grid-row:auto;min-height:160px}}.highlight{{border:0;border-bottom:1px solid var(--line)}}}}@media(max-width:560px){{main{{padding:14px 12px 44px}}.hero-copy,.score-card{{padding:22px}}.actions,.live-grid,.highlights,.stories,.checklist{{grid-template-columns:1fr}}.hero h1{{font-size:46px}}}}
</style></head><body><main><section class="hero"><div class="hero-copy"><div><h1>ColdChain Sentinel</h1><p>Turn noisy synthetic sensor evidence into clear advisory signals, safe fallbacks, and human-review next steps.</p></div><nav class="hero-nav"><a href="/demo-flow">Start demo</a><a href="/command-center">Command center</a></nav></div><aside class="score-card"><div class="number">{score["score"]}</div><div><h2>{score["label"]}</h2><strong>{score["band"]}</strong><p>{html.escape(score["meaning"])}</p></div></aside></section><div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>Deterministic rules authoritative</span><span>Runtime GPU required: false</span><span>Runtime external service required: false</span><span>Fireworks optional</span><span>Not production validation</span></div>
<section><h2>What Next?</h2><p class="section-note">The shortest paths to the strongest evidence.</p><div class="actions">{actions}</div></section>
<section><h2>Synthetic Live View</h2><p class="section-note">{html.escape(payload["syntheticLiveView"]["description"])}</p><div class="live-grid">{activity}</div></section>
<section><h2>Demo highlights</h2><p class="section-note">A recap of the strongest committed evidence.</p><div class="highlights">{highlights}</div></section>
<section class="why"><div><h2>{html.escape(payload["whyLayer"]["title"])}</h2><a class="button" href="{html.escape(payload["whyLayer"]["route"])}">Inspect safety eval</a></div><p>{html.escape(payload["whyLayer"]["deterministicExplanation"])} Fireworks optional. Fallback available.</p></section>
<section><h2>How the story holds together</h2><div class="stories">{narratives}</div></section>
<section><h2>Screenshot-worthy checklist</h2><div class="checklist">{checks}</div></section>
<section><h2>Evidence routes</h2><div class="routes">{routes}</div></section></main></body></html>'''
