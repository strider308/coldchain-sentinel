from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


PHASE = "Phase 21 - Expanded Synthetic Benchmark Refresh"
ARTIFACT_PATH = "artifacts/expanded_synthetic_benchmark_phase21.json"
ARTIFACT_FILE = Path(__file__).resolve().parents[1] / ARTIFACT_PATH


def validate_expanded_benchmark_artifact(payload: Any) -> bool:
    return bool(
        isinstance(payload, dict)
        and payload.get("phase") == PHASE
        and isinstance(payload.get("status"), str)
        and payload.get("syntheticOnly") is True
        and payload.get("advisoryOnly") is True
        and payload.get("runtimeGpuRequired") is False
        and payload.get("runtimeExternalServiceRequired") is False
        and payload.get("deterministicRulesAuthoritative") is True
        and payload.get("autonomousActionsAllowed") is False
        and isinstance(payload.get("dataset"), dict)
        and isinstance(payload.get("benchmarkComparison"), list)
        and isinstance(payload.get("trainingBenchmark"), dict)
        and isinstance(payload.get("scenarioCoverage"), list)
        and len(payload["scenarioCoverage"]) >= 14
        and isinstance(payload.get("safetyBoundaries"), dict)
    )


def load_expanded_benchmark_artifact() -> dict[str, Any] | None:
    try:
        with ARTIFACT_FILE.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if validate_expanded_benchmark_artifact(payload) else None


def get_expanded_benchmark_payload() -> dict[str, Any]:
    artifact = load_expanded_benchmark_artifact()
    available = artifact is not None
    artifact = artifact or {}
    return {
        "phase": PHASE,
        "status": artifact.get("status", "ARTIFACT_UNAVAILABLE"),
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
        "artifactAvailable": available,
        "artifactPath": ARTIFACT_PATH,
        "dataset": artifact.get("dataset", {}),
        "benchmarkComparison": artifact.get("benchmarkComparison", []),
        "trainingBenchmark": artifact.get("trainingBenchmark", {}),
        "scenarioCoverage": artifact.get("scenarioCoverage", []),
        "safetyBoundaries": artifact.get("safetyBoundaries", {}),
        "routeMap": {
            "expandedBenchmark": "/expanded-benchmark",
            "benchmarkRefresh": "/benchmark-refresh",
            "opsReadiness": "/ops-readiness",
            "productionGapAnalysis": "/production-gap-analysis",
            "demoConsole": "/demo-console",
            "gpuResearchLab": "/gpu-research-lab",
        },
    }


def render_expanded_benchmark_html() -> str:
    payload = get_expanded_benchmark_payload()
    dataset = payload["dataset"]
    training = payload["trainingBenchmark"]
    cpu = training.get("cpuResult") or {}
    gpu = training.get("gpuResult") or {}
    scenarios = "".join(
        "<tr>"
        f'<th scope="row">{html.escape(str(row.get("scenario", "")))}</th>'
        f'<td>{html.escape(str(row.get("rows", "")))}</td>'
        f'<td>{html.escape(str(row.get("positiveRate", "")))}</td>'
        f'<td>{html.escape(str(row.get("avgSersStyleScore", "")))}</td>'
        "</tr>"
        for row in payload["scenarioCoverage"]
    )
    comparisons = "".join(
        f'<li><strong>{html.escape(str(row.get("name", "")))}</strong>: accuracy {html.escape(str(row.get("accuracy", "")))}, F1 {html.escape(str(row.get("f1", "")))}</li>'
        for row in payload["benchmarkComparison"]
    )
    timing = (
        f'CPU: {html.escape(str(cpu.get("trainSeconds")))} seconds; '
        f'GPU: {html.escape(str(gpu.get("trainSeconds")))} seconds; '
        f'synthetic timing ratio: {html.escape(str(training.get("speedupRatio")))}x.'
        if cpu and gpu
        else "CPU/GPU timing is not present in the validated artifact."
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Expanded Synthetic Benchmark</title><style>
body{{margin:0;background:#07131b;color:#edf7f5;font:16px system-ui,sans-serif}}main{{max-width:1150px;margin:auto;padding:28px 18px 48px}}a{{color:#8ee8cb}}
.badges,.grid{{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}}.badge{{border:1px solid #347263;border-radius:999px;padding:7px 11px}}.card{{flex:1 1 260px;background:#102631;border:1px solid #244852;border-radius:12px;padding:16px}}
table{{width:100%;border-collapse:collapse;background:#102631}}th,td{{padding:11px;text-align:left;border-bottom:1px solid #244852}}.table-wrap{{overflow-x:auto}}@media(max-width:600px){{main{{padding:20px 12px}}}}
</style></head><body><main><p><a href="/">ColdChain Sentinel</a> / <a href="/expanded-benchmark.json">JSON</a> / <a href="/benchmark-refresh">Refresh alias</a></p>
<h1>Expanded Synthetic Benchmark Refresh</h1><p>GPU/Jupyter was used offline only. The live app reads a committed JSON summary and has no runtime GPU or notebook dependency.</p>
<div class="badges"><span class="badge">Synthetic-only</span><span class="badge">Advisory-only</span><span class="badge">Runtime GPU required: false</span><span class="badge">Runtime external service required: false</span><span class="badge">Deterministic rules authoritative</span></div>
<section class="grid"><article class="card"><h2>Dataset summary</h2><p>{html.escape(str(dataset.get("syntheticRows", 0)))} synthetic rows across {len(dataset.get("scenarioFamilies", []))} scenario families.</p></article>
<article class="card"><h2>Training timing</h2><p>{timing}</p></article><article class="card"><h2>Artifact</h2><p>Status: {html.escape(str(payload["status"]))}</p><p>Available: {str(payload["artifactAvailable"]).lower()}</p></article></section>
<section class="card"><h2>Benchmark comparison</h2><ul>{comparisons}</ul></section>
<section><h2>Scenario coverage</h2><div class="table-wrap"><table><thead><tr><th>Scenario</th><th>Rows</th><th>Positive rate</th><th>Average advisory score</th></tr></thead><tbody>{scenarios}</tbody></table></div></section>
</main></body></html>"""
