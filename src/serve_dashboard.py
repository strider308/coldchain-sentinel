"""Stdlib-only ColdChain Sentinel dashboard and review packet."""

from __future__ import annotations

import argparse
import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from ai_review_assistant import build_ai_review
from case_engine import audit_markdown, case_packet, evidence_json, export_markdown, get_case, load_cases, trace_json
from coldchain_baseline import build_review_packet, evaluate_case, load_fixture
from sensor_adapters import adapter_summary, canonical_schema, example_results
from sensor_engine import benchmark_model, cleaning_report, consensus_report, prediction_report, sensor_summary, sensor_window, sers_risk

HOST = "127.0.0.1"
PORT = 8080
AGGREGATION_CAPABILITIES = [
    "zone min/max/average temperature",
    "threshold breaches",
    "excursion windows",
    "noisy/outlier/dropout readings",
    "impacted zones",
    "pallet mapping",
    "review blockers",
]
QUALITY_LABELS = [
    "SENSOR_OK",
    "SENSOR_READING_ABOVE_THRESHOLD",
    "SENSOR_DROPOUT",
    "SENSOR_DRIFT_POSSIBLE",
    "SENSOR_OUTLIER_REJECTED",
    "SENSOR_WINDOW_ESCALATED",
]


def fmt_time(value: str) -> str:
    return value.replace("T", " ").replace(":00Z", " UTC")


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="badge badge-{tone}">{html.escape(text)}</span>'


def global_nav() -> str:
    return (
        '<nav class="global-nav" data-testid="global-nav">'
        '<a href="/">Home</a><a href="/command-center">Command Center</a><a href="/cases">Cases</a><a href="/review" data-testid="review-packet-link">Baseline Review</a>'
        '<a href="/sensor-lab">Sensor Lab</a><a href="/data-pipeline">Pipeline</a><a href="/model-benchmark">Benchmark</a><a href="/roadmap">Roadmap</a><a href="/ai-review" data-testid="ai-review-link">AI Review</a><a href="/health">Health</a>'
        '<a href="https://github.com/strider308/coldchain-sentinel">GitHub repo</a>'
        "</nav>"
    )


def status_badges(result: dict[str, Any], extra: list[str] | None = None) -> str:
    disposition = result["finalDisposition"]
    if disposition == "NO_EXCURSION_CONTROL":
        disposition = "DEMO_CONTROL_NO_EXCURSION"
    labels = [
        disposition,
        result["reviewStatus"],
        "AUTONOMOUS_ACTIONS_DISABLED",
        "SYNTHETIC_ONLY",
    ]
    labels.extend(extra or [])
    return "".join(badge(label, "danger" if label == "BLOCKED" else "warn") for label in labels)


def render_not_found(case_id: str | None = None) -> str:
    case_ids = [case["caseId"] for case in load_cases()]
    body = f"""
  <header data-testid="not-found-page">
    {global_nav()}
    <h1>Case not found</h1>
    <p>No synthetic case matched: {html.escape(case_id or "unknown")}.</p>
  </header>
  <main>
    <section class="panel">
      <h2>Available synthetic cases</h2>
      <ul>{items(case_ids, "available-case")}</ul>
      <p><a class="button" href="/cases">Back to cases</a></p>
    </section>
  </main>
"""
    return page("Case not found", body)


def items(values: list[str], test_prefix: str) -> str:
    return "\n".join(
        f'<li data-testid="{html.escape(test_prefix)}-{html.escape(value)}">{html.escape(value)}</li>' for value in values
    )


def timeline_items(values: list[dict[str, str]]) -> str:
    return "\n".join(
        f'<li data-testid="timeline-{html.escape(row["time"])}"><strong>{html.escape(row["time"])}</strong> - {html.escape(row["event"])}</li>'
        for row in values
    )


def trace_table(values: list[dict[str, Any]]) -> str:
    return table(
        ["Status", "Rule", "Input", "Output", "Evidence IDs", "Safety impact"],
        [
            [
                row["status"],
                row["ruleName"],
                row["inputSummary"],
                row["outputSummary"],
                ", ".join(row["evidenceIds"]) or "None",
                row["safetyImpact"],
            ]
            for row in values
        ],
        "deterministic-rule-trace",
    )


def telemetry_table(values: list[dict[str, Any]], threshold: float) -> str:
    return table(
        ["Timestamp", "Temperature", "Threshold", "Zone", "State", "Evidence ID"],
        [
            [
                row["timestampUtc"],
                f'{row["temperatureC"]} C',
                f"{threshold} C",
                row["zoneId"],
                "Above threshold - review signal" if row["thresholdExceeded"] else "Within synthetic threshold",
                row["evidenceId"],
            ]
            for row in values
        ],
        "telemetry-timeline",
    )


def sensor_preview_table(readings: list[dict[str, Any]]) -> str:
    return table(
        ["Timestamp", "Sensor", "Zone", "Temperature", "Quality label", "Evidence ID"],
        [
            [
                row["timestampUtc"],
                row["sensorId"],
                row["zoneId"],
                "missing" if row["temperatureC"] is None else f'{row["temperatureC"]} C',
                row["qualityLabel"],
                row["evidenceId"] or "None",
            ]
            for row in readings
        ],
        "sensor-window-preview",
    )


def sensor_summary_panel(case_id: str, summary: dict[str, Any]) -> str:
    return f"""
      <article class="panel" data-testid="large-sensor-data-summary">
        <h2>Large Sensor Data Summary</h2>
        <p>ColdChain Sentinel does not ask reviewers to inspect every reading. It compresses high-volume synthetic telemetry into deterministic evidence, rule traces, and human-review packets.</p>
        <p>Total readings represented: {summary["generatedReadingCount"]}</p>
        <p>Sensor count: {summary["sensorCount"]}. Zone count: {summary["zoneCount"]}. Threshold: {summary["thresholdMaxC"]} C.</p>
        <p>Detected excursion count: {len(summary["excursionWindows"])}. Above-threshold readings: {summary["aggregationSummary"]["aboveThresholdReadingCount"]}.</p>
        <p>Noisy/dropped readings: {summary["aggregationSummary"]["rejectedNoisyReadingCount"]}. Impacted zones: {html.escape(", ".join(summary["impactedZones"]) or "None")}.</p>
        <p>Evidence IDs: {html.escape(", ".join(eid for window in summary["excursionWindows"] for eid in window["evidenceIds"]) or "None")}.</p>
        <div class="toolbar"><a class="button" href="/cases/{html.escape(case_id)}/sensor-summary.json">Sensor summary JSON</a><a class="button" href="/cases/{html.escape(case_id)}/sensor-window.json?offset=0&limit=100">First 100 readings</a></div>
      </article>
"""


def sensor_intelligence_panel(case_id: str, clean: dict[str, Any], consensus: dict[str, Any], risk: dict[str, Any]) -> str:
    zone_scores = ", ".join(
        f'{zone["zoneId"]}: {zone["zoneConsensusScore"]} ({zone["consensusLabel"]})' for zone in consensus["zones"]
    )
    return f"""
      <article class="panel" data-testid="sensor-intelligence-panel">
        <h2>Sensor Intelligence</h2>
        <p>Accepted readings: {clean["acceptedReadingCount"]}. Rejected readings: {clean["rejectedReadingCount"]}. Duplicates: {clean["duplicateCount"]}.</p>
        <p>Dropouts: {clean["flagCounts"]["FLAGGED_DROPOUT"]}. Outliers: {clean["flagCounts"]["FLAGGED_OUTLIER"]}. Consensus: {html.escape(zone_scores)}</p>
        <p>SERS risk score: {risk["riskScore"]}. Risk band: {risk["riskBand"]}. Prediction horizon: 30 minutes.</p>
        <p>Advisory only. SERS and model predictions do not alter deterministic review facts.</p>
        <div class="toolbar"><a class="button" href="/cases/{html.escape(case_id)}/cleaning-report.json">Cleaning report</a><a class="button" href="/cases/{html.escape(case_id)}/prediction.json">Prediction JSON</a><a class="button" href="/model-benchmark">Model benchmark</a><a class="button" href="/data-pipeline">Data pipeline</a></div>
      </article>
"""


def all_sensor_summaries() -> list[dict[str, Any]]:
    return [sensor_summary(case, case_packet(case)["result"]) for case in load_cases()]


def beta_sensor_totals() -> dict[str, Any]:
    summaries = all_sensor_summaries()
    first = summaries[0]
    return {
        "caseCount": len(summaries),
        "betaTotalGeneratedReadings": sum(summary["generatedReadingCount"] for summary in summaries),
        "readingsPerCase": first["generatedReadingCount"],
        "sensorCount": first["sensorCount"],
        "zoneCount": first["zoneCount"],
        "timeRangeHours": 48,
        "readingIntervalMinutes": 5,
    }


def command_center_payload() -> dict[str, Any]:
    case = get_case("blocked-unresolved-pallet")
    packet = case_packet(case)
    result = packet["result"]
    totals = beta_sensor_totals()
    clean = cleaning_report(case)
    consensus = consensus_report(case)
    risk = sers_risk(case, result)
    benchmark = model_benchmark_json()
    return {
        "appName": "ColdChain Sentinel",
        "mode": "synthetic_hackathon_beta",
        "betaTotalGeneratedReadings": totals["betaTotalGeneratedReadings"],
        "caseCount": totals["caseCount"],
        "sensorAdapterSummary": {
            "sensorAdaptersAvailable": True,
            "dataContractVersion": "v2",
            "supportedSyntheticAdapterFormats": adapter_summary()["supportedSyntheticAdapterFormats"],
        },
        "sensorSummary": {
            "readingsPerCase": totals["readingsPerCase"],
            "sensorCount": totals["sensorCount"],
            "zoneCount": totals["zoneCount"],
            "timeRangeHours": totals["timeRangeHours"],
            "readingIntervalMinutes": totals["readingIntervalMinutes"],
            "syntheticOnly": True,
        },
        "cleaningSummary": {
            "acceptedReadings": clean["acceptedReadingCount"],
            "rejectedReadings": clean["rejectedReadingCount"],
            "duplicateCount": clean["duplicateCount"],
            "dropoutCount": clean["flagCounts"]["FLAGGED_DROPOUT"],
            "outlierCount": clean["flagCounts"]["FLAGGED_OUTLIER"],
            "driftCount": clean["flagCounts"]["FLAGGED_DRIFT"],
            "lowBatteryCount": clean["flagCounts"]["FLAGGED_LOW_BATTERY"],
            "weakSignalCount": clean["flagCounts"]["FLAGGED_WEAK_SIGNAL"],
        },
        "consensusSummary": consensus["zones"][0],
        "sersSummary": {
            "riskScore": risk["riskScore"],
            "riskBand": risk["riskBand"],
            "topContributingFactors": risk["topContributingFactors"],
            "predictionHorizonMinutes": 30,
            "advisoryOnly": True,
        },
        "benchmarkSummary": {
            "benchmarkScope": benchmark["benchmarkScope"],
            "trainingRows": benchmark["model"]["trainingRows"],
            "testRows": benchmark["model"]["testRows"],
            "metrics": benchmark["metrics"],
            "baselines": list(benchmark["baselines"].keys()),
        },
        "modelGovernanceSummary": {
            "sersModelCardAvailable": True,
            "benchmarkExplainabilityAvailable": True,
            "sersModelCard": "/sers-model-card",
            "benchmarkExplainability": "/benchmark-explainability",
        },
        "publicDatasetReadinessSummary": {
            "externalDatasetsIngested": False,
            "publicBenchmarkPlanAvailable": True,
            "licenseTosReviewRequired": True,
        },
        "deterministicReviewSummary": {
            "shipmentId": result["shipmentId"],
            "finalDisposition": result["finalDisposition"],
            "reviewStatus": result["reviewStatus"],
            "unresolvedPalletIds": result["unresolvedPalletIds"],
            "blockers": result["blockers"],
            "autonomousActionsAllowed": result["autonomousActionsAllowed"],
        },
        "fireworksSafetySummary": {
            "fireworksConfigured": bool(os.environ.get("FIREWORKS_API_KEY")),
            "fireworksAuthoritative": False,
            "handling": "model output is validated, sanitized, or rejected; deterministic fallback remains authoritative",
        },
        "readinessSummary": {
            "realDataUsed": False,
            "autonomousActionsAllowed": False,
            "productionValidated": False,
            "deterministicRulesAuthoritative": True,
        },
        "routeMap": {
            "sensorLab": "/sensor-lab",
            "sensorAdapters": "/sensor-adapters",
            "dataContract": "/data-contract",
            "dataPipeline": "/data-pipeline",
            "cleaningReport": "/cases/blocked-unresolved-pallet/cleaning-report.json",
            "prediction": "/cases/blocked-unresolved-pallet/prediction.json",
            "modelBenchmark": "/model-benchmark",
            "sersModelCard": "/sers-model-card",
            "benchmarkExplainability": "/benchmark-explainability",
            "datasetAdapters": "/dataset-adapters",
            "datasetLicenseChecklist": "/dataset-license-checklist",
            "publicDatasetBenchmarkPlan": "/public-dataset-benchmark-plan",
            "reviewWorkspace": "/cases/blocked-unresolved-pallet/review",
            "ruleTrace": "/cases/blocked-unresolved-pallet/trace.json",
            "auditPacket": "/cases/blocked-unresolved-pallet/audit.md",
            "aiReview": "/ai-review",
            "systemStatus": "/system-status.json",
            "validationEvidence": "/validation-evidence",
            "roadmap": "/roadmap",
        },
        "safetyDisclaimers": [
            "Synthetic data only.",
            "No autonomous operational action.",
            "Deterministic rules remain authoritative.",
            "Predictions and SERS are advisory only.",
            "Not production, medical, pharma, or compliance validated.",
        ],
    }


def table(headers: list[str], rows: list[list[str]], testid: str) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>" for row in rows
    )
    return f'<table data-testid="{html.escape(testid)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172026;
      --muted: #5c6870;
      --line: #d9e0e5;
      --panel: #f7f9fa;
      --accent: #146c5f;
      --warn: #9a4f00;
      --danger: #a32626;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: #fff; line-height: 1.45; }}
    header {{ padding: 28px clamp(16px, 4vw, 48px); border-bottom: 1px solid var(--line); background: var(--panel); }}
    main {{ width: min(1120px, 100%); margin: 0 auto; padding: 24px clamp(16px, 4vw, 32px) 40px; }}
    nav a {{ color: var(--accent); font-weight: 700; margin-right: 16px; }}
    .global-nav {{ display: flex; flex-wrap: wrap; gap: 10px 16px; margin-bottom: 14px; }}
    .global-nav a {{ margin-right: 0; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(28px, 4vw, 42px); }}
    h2 {{ margin: 0 0 12px; font-size: 20px; }}
    p {{ margin: 0 0 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 16px 0; }}
    .panel {{ border: 1px solid var(--line); border-radius: 8px; padding: 16px; background: #fff; }}
    .metric {{ font-size: 30px; font-weight: 700; margin: 4px 0; }}
    .muted {{ color: var(--muted); }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 13px; font-weight: 700; border: 1px solid var(--line); margin: 2px 4px 2px 0; }}
    .badge-good {{ color: var(--accent); background: #e9f7f4; }}
    .badge-warn {{ color: var(--warn); background: #fff3df; }}
    .badge-danger {{ color: var(--danger); background: #ffecec; }}
    ul {{ padding-left: 20px; margin: 8px 0 0; }}
    .status-block {{ border-left: 4px solid var(--danger); background: #fff6f6; }}
    .timeline {{ display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; }}
    .line {{ height: 3px; background: var(--line); }}
    .button {{ display: inline-block; border: 1px solid var(--accent); border-radius: 6px; padding: 8px 12px; color: #fff; background: var(--accent); text-decoration: none; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ text-align: left; border-bottom: 1px solid var(--line); padding: 8px 6px; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 13px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }}
    .check-row {{ display: flex; gap: 8px; align-items: flex-start; margin: 8px 0; }}
    .check-row input {{ margin-top: 4px; }}
    @media (max-width: 640px) {{
      header {{ padding: 18px 14px; }}
      main {{ padding: 16px 12px 28px; }}
      .grid {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
      .button {{ width: 100%; text-align: center; }}
    }}
  </style>
</head>
<body>{body}</body>
</html>
"""


def render_dashboard(case: dict[str, Any] | None = None) -> str:
    case = case or load_fixture()
    result = evaluate_case(case)
    excursion = result["excursion"]
    mapped = result["mappedPalletIds"]
    unresolved = result["unresolvedPalletIds"]
    forbidden = case["reviewPolicy"]["autonomousActionsForbidden"]

    mapped_items = items(mapped, "mapped")
    unresolved_items = "\n".join(
        f'<li data-testid="unresolved-{html.escape(pallet_id)}">{html.escape(pallet_id)} because zone mapping is missing.</li>'
        for pallet_id in unresolved
    )
    forbidden_items = "\n".join(
        f'<li data-testid="forbidden-{html.escape(action)}">{html.escape(action.replace("_", " "))}</li>'
        for action in forbidden
    )
    blocker_items = "\n".join(
        f'<li data-testid="blocker-{html.escape(blocker)}">{html.escape(blocker.replace("_", " ").title())}</li>'
        for blocker in result["blockers"]
    )

    body = f"""
  <header data-testid="demo-overview">
    {global_nav()}
    <h1>ColdChain Sentinel</h1>
    <p data-testid="synthetic-scope-note">Synthetic demo data only. Deterministic rules are authoritative.</p>
    {badge("Track 3 demo", "good")}{badge("Fireworks optional", "warn")}{badge("No production validation", "warn")}
  </header>
  <main>
    <section class="panel" data-testid="command-center-cta">
      <h2>Platform Command Center</h2>
      <p>One page connects sensor telemetry, cleaning, consensus, SERS advisory risk, model benchmark, deterministic review facts, Fireworks safety gates, and readiness checks.</p>
      <div class="toolbar"><a class="button" href="/command-center">Open Command Center</a><a class="button" href="/cases">Cases</a><a class="button" href="/sensor-lab">Sensor Lab</a><a class="button" href="/data-pipeline">Data Pipeline</a><a class="button" href="/model-benchmark">Model Benchmark</a><a class="button" href="/ai-review">AI Review</a></div>
    </section>
    <section class="grid" aria-label="Shipment summary">
      <article class="panel" data-testid="shipment-dashboard">
        <h2>Shipment overview</h2>
        <p class="muted">Synthetic shipment</p>
        <p class="metric" data-testid="shipment-id">{html.escape(result["shipmentId"])}</p>
        <p>Temperature range: {case["shipment"]["temperatureRangeC"]["min"]} C to {case["shipment"]["temperatureRangeC"]["max"]} C.</p>
      </article>
      <article class="panel" data-testid="excursion-summary">
        <h2>Excursion</h2>
        <p data-testid="excursion-window">{fmt_time(excursion["startUtc"])} to {fmt_time(excursion["endUtc"])}</p>
        <p class="metric" data-testid="duration-45">{excursion["durationMinutes"]} minutes</p>
        <p class="muted">Calculated by deterministic threshold comparison.</p>
      </article>
      <article class="panel status-block" data-testid="decision-status">
        <h2>Decision status</h2>
        <p class="metric" data-testid="final-disposition-blocked">{html.escape(result["finalDisposition"].title())}</p>
        <p data-testid="human-review-required">Human review required.</p>
      </article>
    </section>

    <section class="panel" data-testid="excursion-timeline">
      <h2>Excursion timeline</h2>
      <div class="timeline"><strong>{fmt_time(excursion["startUtc"])}</strong><div class="line" aria-hidden="true"></div><strong>{fmt_time(excursion["endUtc"])}</strong></div>
      <p class="muted">Affected zone: {html.escape(excursion["zoneId"])}. Evidence: {", ".join(map(html.escape, excursion["evidenceIds"]))}.</p>
    </section>

    <section class="grid" aria-label="Pallet mapping">
      <article class="panel" data-testid="mapping-status"><h2>Mapped pallets</h2><ul>{mapped_items}</ul></article>
      <article class="panel status-block" data-testid="unresolved-mapping"><h2>Unresolved pallet</h2><ul>{unresolved_items}</ul></article>
    </section>

    <section class="grid" aria-label="Safety boundary">
      <article class="panel status-block" data-testid="safety-boundary"><h2>Safety boundary</h2><p>No autonomous release, quarantine, discard, reroute, or customer notification.</p><ul>{forbidden_items}</ul></article>
      <article class="panel" data-testid="blockers"><h2>Blockers</h2><ul>{blocker_items}</ul></article>
      <article class="panel" data-testid="review-packet-card"><h2>Review packet</h2><p>Human-readable packet generated from deterministic status.</p><a class="button" href="/review" data-testid="open-review-packet">Open review packet</a></article>
    </section>
  </main>
"""
    return page("ColdChain Sentinel", body)


def render_command_center() -> str:
    payload = command_center_payload()
    cleaning = payload["cleaningSummary"]
    consensus = payload["consensusSummary"]
    sers = payload["sersSummary"]
    benchmark = payload["benchmarkSummary"]
    governance = payload["modelGovernanceSummary"]
    dataset_readiness = payload["publicDatasetReadinessSummary"]
    review = payload["deterministicReviewSummary"]
    fireworks = payload["fireworksSafetySummary"]
    readiness = payload["readinessSummary"]
    factors = items([str(value) for value in sers["topContributingFactors"]], "command-center-factor")
    blockers = items([str(value) for value in review["blockers"]], "command-center-blocker")
    body = f"""
  <header data-testid="command-center-page">
    {global_nav()}
    <h1>Platform Command Center</h1>
    <p>ColdChain Sentinel turns noisy high-volume synthetic cold-chain sensor telemetry into cleaned evidence, redundancy consensus, advisory risk scores, deterministic rule traces, and human-review audit packets.</p>
    {badge("Synthetic investor beta", "warn")}{badge("Deterministic rules authoritative", "good")}{badge("No autonomous action", "warn")}
  </header>
  <main>
    <section class="grid">
      <article class="panel" data-testid="command-adapter-summary"><h2>Sensor Adapter status</h2><p>Data Contract v2 is available for synthetic vendor-style payload normalization.</p><p>Supported synthetic formats: {html.escape(", ".join(payload["sensorAdapterSummary"]["supportedSyntheticAdapterFormats"]))}.</p><div class="toolbar"><a class="button" href="/sensor-adapters">Sensor Adapters</a><a class="button" href="/data-contract">Data Contract</a></div></article>
      <article class="panel" data-testid="command-sensor-summary"><h2>Sensor telemetry summary</h2><p class="metric">{payload["betaTotalGeneratedReadings"]}</p><p>Total synthetic readings represented across beta. Readings per case: {payload["sensorSummary"]["readingsPerCase"]}. Sensors: {payload["sensorSummary"]["sensorCount"]}. Zones: {payload["sensorSummary"]["zoneCount"]}. Time range: {payload["sensorSummary"]["timeRangeHours"]} hours. Interval: {payload["sensorSummary"]["readingIntervalMinutes"]} minutes.</p><p>Synthetic data only.</p><div class="toolbar"><a class="button" href="/sensor-lab">Sensor Lab</a><a class="button" href="/sensor-lab.json">Sensor JSON</a></div></article>
      <article class="panel" data-testid="command-cleaning-summary"><h2>Data cleaning summary</h2><p>Accepted readings: {cleaning["acceptedReadings"]}. Rejected readings: {cleaning["rejectedReadings"]}. Duplicates: {cleaning["duplicateCount"]}. Dropouts: {cleaning["dropoutCount"]}. Outliers: {cleaning["outlierCount"]}. Drift: {cleaning["driftCount"]}. Low battery: {cleaning["lowBatteryCount"]}. Weak signal: {cleaning["weakSignalCount"]}.</p><div class="toolbar"><a class="button" href="/data-pipeline">Data Pipeline</a><a class="button" href="/cases/blocked-unresolved-pallet/cleaning-report.json">Cleaning JSON</a></div></article>
      <article class="panel" data-testid="command-consensus-summary"><h2>Redundancy and consensus summary</h2><p>Sensor trust score: {consensus["sensorTrustScore"]}. Zone consensus score: {consensus["zoneConsensusScore"]}. Consensus label: {html.escape(consensus["consensusLabel"])}.</p><p>Redundancy compares neighboring synthetic sensors so one bad sensor is treated as a review signal, not a final conclusion.</p></article>
      <article class="panel" data-testid="command-sers-summary"><h2>SERS advisory risk summary</h2><p class="metric">{sers["riskScore"]}</p><p>Risk band: {html.escape(sers["riskBand"])}. Prediction horizon: {sers["predictionHorizonMinutes"]} minutes.</p><ul>{factors}</ul><p>Advisory only; predictions do not alter deterministic review facts.</p><div class="toolbar"><a class="button" href="/cases/blocked-unresolved-pallet/prediction.json">Prediction JSON</a></div></article>
      <article class="panel" data-testid="command-benchmark-summary"><h2>Model benchmark summary</h2><p>{html.escape(benchmark["benchmarkScope"])}</p><p>Training rows: {benchmark["trainingRows"]}. Test rows: {benchmark["testRows"]}. Accuracy: {benchmark["metrics"]["accuracy"]}. Compared baselines: {html.escape(", ".join(benchmark["baselines"]))}.</p><p>Benchmarked on deterministic synthetic data against simple baselines.</p><div class="toolbar"><a class="button" href="/model-benchmark">Benchmark</a><a class="button" href="/model-benchmark.json">Benchmark JSON</a></div></article>
      <article class="panel" data-testid="command-model-governance"><h2>Model governance</h2><p>SERS Model Card and Benchmark Explainability are available for the synthetic advisory model.</p><p>SERS advisory only: true. Deterministic rules authoritative: true.</p><div class="toolbar"><a class="button" href="{html.escape(governance["sersModelCard"])}">SERS Model Card</a><a class="button" href="{html.escape(governance["benchmarkExplainability"])}">Benchmark Explainability</a></div></article>
      <article class="panel" data-testid="command-public-dataset-readiness"><h2>Public Dataset Readiness</h2><p>External datasets ingested: {str(dataset_readiness["externalDatasetsIngested"]).lower()}. Public benchmark plan available: {str(dataset_readiness["publicBenchmarkPlanAvailable"]).lower()}.</p><p>License/TOS review is required before any ingestion.</p><div class="toolbar"><a class="button" href="/dataset-adapters">Dataset Adapters</a><a class="button" href="/dataset-license-checklist">License Checklist</a><a class="button" href="/public-dataset-benchmark-plan">Benchmark Plan</a></div></article>
      <article class="panel status-block" data-testid="command-review-summary"><h2>Deterministic review packet summary</h2><p>Shipment ID: {html.escape(review["shipmentId"])}. finalDisposition: {html.escape(review["finalDisposition"])}. reviewStatus: {html.escape(review["reviewStatus"])}.</p><p>Unresolved pallet IDs: {html.escape(", ".join(review["unresolvedPalletIds"]) or "None")}. autonomousActionsAllowed: {str(review["autonomousActionsAllowed"]).lower()}.</p><ul>{blockers}</ul><div class="toolbar"><a class="button" href="/cases/blocked-unresolved-pallet/review">Review</a><a class="button" href="/cases/blocked-unresolved-pallet/trace.json">Trace JSON</a><a class="button" href="/cases/blocked-unresolved-pallet/audit.md">Audit packet</a></div></article>
      <article class="panel" data-testid="command-fireworks-summary"><h2>Fireworks safety-gate summary</h2><p>Fireworks configured: {str(fireworks["fireworksConfigured"]).lower()}. Fireworks authoritative: false.</p><p>Model output is validated, sanitized, or rejected. Deterministic fallback remains authoritative.</p><div class="toolbar"><a class="button" href="/ai-review">AI Review</a><a class="button" href="/ai-review.json">AI JSON</a></div></article>
      <article class="panel status-block" data-testid="command-readiness-summary"><h2>Readiness and safety summary</h2><p>No real data: {str(not readiness["realDataUsed"]).lower()}. No autonomous operational actions: {str(not readiness["autonomousActionsAllowed"]).lower()}. Not production/compliance validated: {str(not readiness["productionValidated"]).lower()}.</p><p>Synthetic hackathon/investor beta. Deterministic rules remain authoritative.</p><div class="toolbar"><a class="button" href="/beta-readiness">Beta Readiness</a><a class="button" href="/system-status.json">System Status</a><a class="button" href="/public-data-readiness">Public Data Readiness</a></div></article>
    </section>
    <section class="panel" data-testid="final-demo-flow">
      <h2>Final demo flow</h2>
      <p>Use this path to validate the beta without inspecting every route manually.</p>
      <div class="toolbar"><a class="button" href="/sensor-lab">Sensor Lab</a><a class="button" href="/data-pipeline">Data Pipeline</a><a class="button" href="/model-benchmark">Model Benchmark</a><a class="button" href="/cases/blocked-unresolved-pallet/review">Review Workspace</a><a class="button" href="/cases/blocked-unresolved-pallet/audit.md">Audit Packet</a><a class="button" href="/ai-review">AI Review</a><a class="button" href="/system-status.json">System Status</a><a class="button" href="/validation-evidence">Validation Evidence</a></div>
    </section>
  </main>
"""
    return page("ColdChain Sentinel Command Center", body)


def render_cases() -> str:
    cases = load_cases()
    cards = "\n".join(
        f"""
      <article class="panel" data-testid="case-{html.escape(case["caseId"])}">
        <h2>{html.escape(case["caseTitle"])}</h2>
        <p>{html.escape(case["scenarioSummary"])}</p>
        {status_badges(case_packet(case)["result"])}
        <p>Blockers: {len(case["blockers"])}. Unresolved pallets: {len(case["unresolvedPalletIds"])}.</p>
        <div class="toolbar">
          <a class="button" href="/cases/{html.escape(case["caseId"])}">Open case</a>
          <a class="button" href="/cases/{html.escape(case["caseId"])}/review">Review workspace</a>
          <a class="button" href="/cases/{html.escape(case["caseId"])}/trace.json">Trace JSON</a>
          <a class="button" href="/cases/{html.escape(case["caseId"])}/evidence.json">Evidence JSON</a>
          <a class="button" href="/cases/{html.escape(case["caseId"])}/export.md">Export</a>
          <a class="button" href="/cases/{html.escape(case["caseId"])}/audit.md">Audit packet</a>
          <a class="button" href="/ai-review?caseId={html.escape(case["caseId"])}">Fireworks brief</a>
        </div>
      </article>
"""
        for case in cases
    )
    comparison = table(
        ["Case", "Excursion?", "Pallet mapping complete?", "Human review?", "Autonomous actions allowed?", "Demo-only limitation"],
        [
            [
                case["caseId"],
                "yes" if case["excursion"] else "no",
                "yes" if not case["unresolvedPalletIds"] else "no",
                "yes" if "HUMAN_REVIEW" in case["reviewStatus"] or "REVIEW" in case["reviewStatus"] else "yes",
                str(case["autonomousActionsAllowed"]).lower(),
                "Synthetic only; no operational action.",
            ]
            for case in cases
        ],
        "case-comparison",
    )
    body = f"""
  <header data-testid="cases-page">
    {global_nav()}
    <h1>Synthetic Case Workspace</h1>
    <p>Synthetic demo data only. No operational action is authorized.</p>
  </header>
  <main>
    <section class="grid" aria-label="Synthetic cases">{cards}</section>
    <section class="panel" data-testid="scenario-comparison"><h2>Scenario comparison</h2>{comparison}</section>
  </main>
"""
    return page("ColdChain Sentinel Cases", body)


def sensor_lab_payload() -> dict[str, Any]:
    summaries = all_sensor_summaries()
    totals = beta_sensor_totals()
    return {
        "syntheticOnly": True,
        **totals,
        "summary": "Large synthetic sensor stream is deterministically aggregated into review evidence.",
        "aggregationCapabilities": AGGREGATION_CAPABILITIES,
        "qualityLabels": QUALITY_LABELS,
        "safetyDisclaimers": [
            "Synthetic data only.",
            "No real customer, patient, logistics, sensor, or shipment data.",
            "Fireworks is optional and non-authoritative.",
            "No autonomous operational action.",
        ],
        "realDataUsed": False,
        "autonomousActionsAllowed": False,
        "fireworksAuthoritative": False,
        "optionalSyntheticScaleProfile": {
            "label": "Optional synthetic scale profile - generated summary only.",
            "sensorCount": 100,
            "days": 7,
            "readingIntervalMinutes": 5,
            "generatedReadingCount": 201600,
            "renderedByDefault": False,
        },
        "cases": summaries,
    }


def render_sensor_lab() -> str:
    cases = load_cases()
    totals = beta_sensor_totals()
    capabilities = "".join(f"<li>{html.escape(value)}</li>" for value in AGGREGATION_CAPABILITIES)
    cards = []
    for case in cases:
        packet = case_packet(case)
        summary = sensor_summary(case, packet["result"])
        cards.append(
            f"""
      <article class="panel" data-testid="sensor-lab-case-{html.escape(case["caseId"])}">
        <h2>{html.escape(case["caseTitle"])}</h2>
        <p>{html.escape(case["scenarioSummary"])}</p>
        <p>Total synthetic readings: {summary["generatedReadingCount"]}. Sensors: {summary["sensorCount"]}. Zones: {summary["zoneCount"]}.</p>
        <p>Time range: {summary["timeRange"]["startUtc"]} to {summary["timeRange"]["endUtc"]}. Threshold: {summary["thresholdMaxC"]} C.</p>
        <p>Above-threshold readings: {summary["aggregationSummary"]["aboveThresholdReadingCount"]}. Excursion windows: {len(summary["excursionWindows"])}.</p>
        <p>Dropout/noisy readings: {summary["aggregationSummary"]["rejectedNoisyReadingCount"]}. Impacted zones: {html.escape(", ".join(summary["impactedZones"]) or "None")}.</p>
        <p>Mapped pallets: {html.escape(", ".join(summary["mappedPalletIds"]) or "None")}. Unresolved pallets: {html.escape(", ".join(summary["unresolvedPalletIds"]) or "None")}.</p>
        <div class="toolbar"><a class="button" href="/cases/{html.escape(case["caseId"])}/review">Review workspace</a><a class="button" href="/cases/{html.escape(case["caseId"])}/trace.json">Rule trace</a><a class="button" href="/cases/{html.escape(case["caseId"])}/audit.md">Audit packet</a><a class="button" href="/cases/{html.escape(case["caseId"])}/sensor-summary.json">Sensor summary JSON</a></div>
      </article>
"""
        )
    preview_case = get_case("blocked-unresolved-pallet")
    preview = sensor_window(preview_case, 0, 12)
    body = f"""
  <header data-testid="sensor-lab-page">
    {global_nav()}
    <h1>Sensor Lab</h1>
    <p>Synthetic-only high-volume telemetry demonstration.</p>
  </header>
  <main>
    <section class="panel">
      <h2>High-volume synthetic telemetry</h2>
      <p class="metric" data-testid="beta-total-readings">{totals["betaTotalGeneratedReadings"]} synthetic readings represented</p>
      <p>Readings per case: {totals["readingsPerCase"]}. Cases: {totals["caseCount"]}. Sensors per case: {totals["sensorCount"]}. Zones per case: {totals["zoneCount"]}. Time range: {totals["timeRangeHours"]} hours. Reading interval: {totals["readingIntervalMinutes"]} minutes.</p>
      <p>Judges do not need to inspect every reading. ColdChain Sentinel compresses high-volume synthetic telemetry into deterministic evidence, rule traces, and human-review packets.</p>
      <p>Flow: large synthetic sensor stream to aggregation to threshold and excursion detection to sensor quality filtering to zone impact to pallet mapping to deterministic rule trace to human-review packet.</p>
    </section>
    <section class="panel" data-testid="sensor-lab-next-links"><h2>Investor-grade beta checks</h2><div class="toolbar"><a class="button" href="/data-pipeline">Data pipeline</a><a class="button" href="/model-benchmark">Model benchmark</a><a class="button" href="/public-data-readiness">Public data readiness</a></div></section>
    <section class="panel" data-testid="aggregation-capabilities"><h2>What is aggregated</h2><ul>{capabilities}</ul></section>
    <section class="panel" data-testid="optional-scale-profile"><h2>Optional synthetic scale profile</h2><p>Optional synthetic scale profile - generated summary only.</p><p>100 sensors, 7 days, 5-minute interval, about 201,600 synthetic readings. Not rendered by default and not a production-scale claim.</p></section>
    <section class="grid" aria-label="Sensor lab cases">{"".join(cards)}</section>
    <section class="panel" data-testid="sensor-window-preview-panel"><h2>Sensor window preview</h2><p>Showing 12 readings from a capped window, not the full generated stream.</p>{sensor_preview_table(preview["readings"])}</section>
  </main>
"""
    return page("ColdChain Sentinel Sensor Lab", body)


def system_status_json() -> dict[str, Any]:
    totals = beta_sensor_totals()
    return {
        "appName": "ColdChain Sentinel",
        "mode": "synthetic_hackathon_beta",
        "caseCount": totals["caseCount"],
        "sensorLabAvailable": True,
        "sensorAdaptersAvailable": True,
        "dataContractVersion": "v2",
        "supportedSyntheticAdapterFormats": adapter_summary()["supportedSyntheticAdapterFormats"],
        "sersModelCardAvailable": True,
        "benchmarkExplainabilityAvailable": True,
        "sersAdvisoryOnly": True,
        "betaTotalGeneratedReadings": totals["betaTotalGeneratedReadings"],
        "deterministicEngineAvailable": True,
        "rulesTraceAvailable": True,
        "auditPacketsAvailable": True,
        "reviewWorkspaceAvailable": True,
        "fireworksConfigured": bool(os.environ.get("FIREWORKS_API_KEY")),
        "fireworksAuthoritative": False,
        "autonomousActionsAllowed": False,
        "realDataUsed": False,
        "productionValidated": False,
    }


def render_beta_readiness() -> str:
    status = system_status_json()
    checklist = [
        ("Live app route available", "check manually after deploy"),
        ("Public repo available", "yes"),
        ("Synthetic cases available", "yes"),
        ("Sensor lab available", "yes"),
        ("Rule trace available", "yes"),
        ("Review workspace available", "yes"),
        ("Audit packets available", "yes"),
        ("Fireworks safety gate available", "yes"),
        ("No real data", "yes"),
        ("No autonomous actions", "yes"),
        ("Not production/compliance validated", "yes"),
    ]
    rows = table(
        ["Capability", "Status"],
        checklist + [[key, str(value).lower() if isinstance(value, bool) else str(value)] for key, value in status.items()],
        "beta-readiness-table",
    )
    body = f"""
  <header data-testid="beta-readiness-page">
    {global_nav()}
    <h1>Beta Readiness</h1>
    <p>Synthetic hackathon beta status. No real-world operational decision is made.</p>
  </header>
  <main><section class="panel">{rows}</section></main>
"""
    return page("ColdChain Sentinel Beta Readiness", body)


def validation_evidence_json() -> dict[str, Any]:
    return {
        "appName": "ColdChain Sentinel",
        "mode": "synthetic_hackathon_investor_beta",
        "routeChecklist": [
            "/",
            "/command-center",
            "/sensor-lab",
            "/data-pipeline",
            "/model-benchmark",
            "/public-data-readiness",
            "/cases/blocked-unresolved-pallet/review",
            "/cases/blocked-unresolved-pallet/audit.md",
            "/system-status.json",
            "/validation-evidence",
            "/roadmap",
            "/ai-review",
            "/health",
        ],
        "validationChecklist": [
            "python src/coldchain_baseline.py",
            "python src/ai_review_assistant.py",
            "python src/serve_dashboard.py --check",
            "python tests/test_coldchain_validation.py",
            "docker build -t coldchain-sentinel-release-hardening:local .",
            "Docker route smoke checklist",
        ],
        "securityChecklist": ["Gitleaks", "TruffleHog", "unsafe-claim scan"],
        "safetyDisclaimers": [
            "Synthetic data only.",
            "No real customer, patient, pharma, logistics, sensor, or shipment data.",
            "Deterministic rules are authoritative.",
            "Fireworks is optional and non-authoritative.",
            "SERS predictions are advisory only.",
            "No autonomous operational action.",
            "Not production, medical, pharma, or compliance validated.",
        ],
        "deterministicRulesAuthoritative": True,
        "fireworksAuthoritative": False,
        "sersAdvisoryOnly": True,
        "realDataUsed": False,
        "autonomousActionsAllowed": False,
        "productionValidated": False,
    }


def render_validation_evidence() -> str:
    payload = validation_evidence_json()
    rows = table(
        ["Evidence", "Status"],
        [
            ["App mode", payload["mode"]],
            ["Public repo", "https://github.com/strider308/coldchain-sentinel"],
            ["Live app", "https://coldchain-sentinel-35ex.onrender.com"],
            ["Local Python validation", "passed before commit"],
            ["Docker route smoke", "passed locally before commit"],
            ["Gitleaks filesystem scan", "passed before commit"],
            ["TruffleHog filesystem scan", "passed before commit"],
            ["Unsafe-claim scan", "passed with only test/safety-filter matches"],
            ["Fireworks safety gate", "optional, validated/sanitized/rejected, non-authoritative"],
            ["Deterministic rules authoritative", str(payload["deterministicRulesAuthoritative"]).lower()],
            ["SERS advisory-only", str(payload["sersAdvisoryOnly"]).lower()],
            ["No real data", str(not payload["realDataUsed"]).lower()],
            ["No autonomous action", str(not payload["autonomousActionsAllowed"]).lower()],
            ["Known limitations", "synthetic beta; no external datasets, database, auth, or production/compliance validation"],
            ["Live route smoke", "run manually after Render deploy"],
        ],
        "validation-evidence-table",
    )
    body = f"""
  <header data-testid="validation-evidence-page">
    {global_nav()}
    <h1>Validation Evidence</h1>
    <p>Non-secret validation evidence for the synthetic hackathon beta. Live validation is not claimed until the deployed service is checked.</p>
  </header>
  <main><section class="panel">{rows}<div class="toolbar"><a class="button" href="/validation-evidence.json">Validation JSON</a><a class="button" href="/command-center">Command Center</a></div></section></main>
"""
    return page("ColdChain Sentinel Validation Evidence", body)


def render_roadmap() -> str:
    rows = table(
        ["Phase", "Focus", "Adoption status"],
        [
            ["Current synthetic beta", "Command Center, Sensor Lab, deterministic trace, SERS advisory scoring, Fireworks safety gate", "implemented with synthetic data"],
            ["Data contract v2", "Richer schema adapters after source licensing review", "planned"],
            ["Cleaning pipeline v2", "More robust quality rules and reviewer-facing explanations", "planned"],
            ["SERS v2", "Calibrated advisory scoring with stronger evaluation", "planned"],
            ["Public dataset readiness", "License/TOS, schema, and provenance review before ingestion", "gated"],
            ["FastAPI/Pydantic migration", "Typed API boundary when stdlib server becomes limiting", "planned"],
            ["DuckDB/Polars analytics", "Local analytical processing evaluation", "planned"],
            ["TimescaleDB evaluation", "Time-series persistence evaluation", "planned"],
            ["MLflow/Evidently evaluation", "Experiment and drift reporting evaluation", "planned"],
            ["Public data calibration", "Real dataset benchmark branch after license/TOS/provenance review", "planned"],
            ["Adapter plan", "Define candidate adapters without ingesting external data", "documented"],
            ["License/TOS review", "Confirm source rights, attribution, privacy, and provenance", "required"],
            ["Schema mapping", "Map reviewed fields into Data Contract v2", "planned"],
            ["Isolated benchmark sandbox", "Run cleaning and benchmark evaluation away from production claims", "planned"],
            ["Model card update", "Record public benchmark evidence and limitations", "planned"],
            ["Model monitoring", "Drift, calibration, and model-card updates after real-world evaluation", "planned"],
            ["Pilot calibration", "No production validation until real-world evaluation is complete", "future"],
            ["Pilot readiness", "Customer-specific pilots after legal/compliance review", "future"],
        ],
        "roadmap-table",
    )
    body = f"""
  <header data-testid="roadmap-page">
    {global_nav()}
    <h1>Platform Roadmap</h1>
    <p>Sustained platform roadmap for the synthetic beta. Planned items are not production claims.</p>
  </header>
  <main><section class="panel">{rows}</section></main>
"""
    return page("ColdChain Sentinel Roadmap", body)


def data_contract_json() -> dict[str, Any]:
    return {
        "appName": "ColdChain Sentinel",
        "dataContractVersion": "v2",
        "schema": canonical_schema(),
        "supportedSyntheticAdapterFormats": adapter_summary()["supportedSyntheticAdapterFormats"],
        "fieldsAffectingCleaningConsensusSers": [
            "timestampUtc",
            "sensorId",
            "zoneId",
            "temperatureC",
            "humidityPercent",
            "batteryPercent",
            "signalStrength",
            "doorOpen",
            "readingSequence",
        ],
        "evidenceFields": ["timestampUtc", "sensorId", "shipmentId", "zoneId", "temperatureC", "sourceFormat"],
        "neverAuthorizesAutonomousAction": True,
        "syntheticOnly": True,
    }


def render_data_contract() -> str:
    schema = canonical_schema()
    rows = table(
        ["Field", "Role"],
        [[field, "required" if field in schema["requiredFields"] else "optional"] for field in schema["fields"]],
        "data-contract-fields",
    )
    body = f"""
  <header data-testid="data-contract-page">
    {global_nav()}
    <h1>Data Contract v2</h1>
    <p>Synthetic sensor payloads are normalized into one internal schema before cleaning, consensus, SERS, and deterministic review packet generation.</p>
  </header>
  <main>
    <section class="panel"><h2>Contract boundary</h2><p>Raw sensors may send native, flat logistics, or nested IoT-style payloads. ColdChain Sentinel normalizes timestamps, device identity, shipment context, zone, temperature, humidity, battery, signal, door state, sequence, firmware, gateway, and adapter provenance.</p><p>Required fields are validated. Optional context can produce warnings. No field can authorize autonomous operational action.</p></section>
    <section class="panel"><h2>Normalized fields</h2>{rows}</section>
    <section class="panel"><h2>Route links</h2><div class="toolbar"><a class="button" href="/sensor-adapters">Sensor Adapters</a><a class="button" href="/data-contract.json">Contract JSON</a><a class="button" href="/data-pipeline">Data Pipeline</a></div></section>
  </main>
"""
    return page("ColdChain Sentinel Data Contract", body)


def sensor_adapters_json(source_format: str | None = None) -> dict[str, Any]:
    payload = adapter_summary()
    payload["examples"] = example_results(source_format)["formats"]
    return payload


def render_sensor_adapters() -> str:
    results = example_results()
    rows = []
    cards = []
    for source_format, examples in results["formats"].items():
        clean = examples[0]
        rows.append([source_format, str(len(examples)), str(clean["accepted"]).lower(), ", ".join(clean["warnings"]) or "None"])
        cards.append(
            f"""
      <article class="panel" data-testid="adapter-{html.escape(source_format)}">
        <h2>{html.escape(source_format)}</h2>
        <p>Raw example:</p><pre>{html.escape(json.dumps(clean["rawPayload"], sort_keys=True, indent=2))}</pre>
        <p>Normalized output example:</p><pre>{html.escape(json.dumps(clean["normalizedReading"], sort_keys=True, indent=2))}</pre>
        <p>Accepted: {str(clean["accepted"]).lower()}. Warnings: {html.escape(", ".join(clean["warnings"]) or "None")}. Errors: {html.escape(", ".join(clean["errors"]) or "None")}.</p>
        <div class="toolbar"><a class="button" href="/sensor-adapters/example.json?format={html.escape(source_format)}">Example JSON</a></div>
      </article>
"""
        )
    body = f"""
  <header data-testid="sensor-adapters-page">
    {global_nav()}
    <h1>Sensor Adapters</h1>
    <p>Deterministic synthetic adapters normalize vendor-style payloads into Data Contract v2 before cleaning pipeline checks.</p>
  </header>
  <main>
    <section class="panel"><h2>Supported synthetic adapter formats</h2>{table(["Format", "Examples", "Clean accepted", "Clean warnings"], rows, "adapter-summary-table")}</section>
    <section class="grid">{"".join(cards)}</section>
    <section class="panel status-block"><h2>Safety boundary</h2><p>Adapters normalize synthetic payloads only. They do not call external sensor APIs and cannot change deterministic review facts or allow autonomous action.</p></section>
  </main>
"""
    return page("ColdChain Sentinel Sensor Adapters", body)


def sers_model_card_json() -> dict[str, Any]:
    benchmark = model_benchmark_json()
    return {
        "modelName": "Sentinel Excursion Risk Score",
        "modelShortName": "SERS",
        "modelVersion": "SERS-0.1-synthetic",
        "mode": "deterministic_synthetic_beta_only",
        "predictionTarget": "Advisory risk of near-future threshold breach or review escalation.",
        "predictionHorizonMinutes": benchmark["model"]["predictionHorizonMinutes"],
        "featureGroups": [
            "temperature distance to threshold",
            "rolling temperature slope",
            "rolling max/mean",
            "humidity trend",
            "door-open events",
            "dropout/outlier/duplicate counts",
            "battery/signal quality",
            "zone consensus score",
            "unresolved pallet penalty",
            "evidence completeness",
        ],
        "outputs": ["riskScore", "riskBand", "confidenceLabel", "topContributingFactors"],
        "intendedUse": [
            "help reviewers prioritize inspection",
            "explain why risk is rising",
            "support audit packet context",
        ],
        "prohibitedUse": [
            "not for autonomous release, quarantine, discard, reroute, or customer notification",
            "not production validated",
            "not pharma/compliance certified",
        ],
        "trainingDataSummary": {
            "source": "deterministic synthetic sensor windows",
            "trainingRows": benchmark["model"]["trainingRows"],
            "testRows": benchmark["model"]["testRows"],
            "realDataUsed": False,
        },
        "benchmarkSummary": {
            "scope": benchmark["benchmarkScope"],
            "baselines": list(benchmark["baselines"].keys()),
            "metrics": benchmark["metrics"],
        },
        "limitations": [
            "trained and evaluated on synthetic data",
            "public or real data ingestion deferred pending license/TOS/provenance review",
            "needs calibration against real sensor/vendor data before pilots",
        ],
        "safetyDisclaimers": [
            "SERS is advisory only.",
            "Deterministic rules remain authoritative.",
            "No autonomous operational action.",
            "No production, pharma, or compliance validation.",
        ],
        "advisoryOnly": True,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
        "realDataUsed": False,
        "productionValidated": False,
    }


def render_sers_model_card() -> str:
    card = sers_model_card_json()
    body = f"""
  <header data-testid="sers-model-card-page">
    {global_nav()}
    <h1>SERS Model Card</h1>
    <p>{html.escape(card["modelName"])} ({html.escape(card["modelShortName"])}) version {html.escape(card["modelVersion"])}.</p>
    {badge("Advisory only", "warn")}{badge("Synthetic beta only", "warn")}{badge("Deterministic rules authoritative", "good")}
  </header>
  <main>
    <section class="grid">
      <article class="panel"><h2>Prediction target</h2><p>{html.escape(card["predictionTarget"])}</p><p>Horizon: {card["predictionHorizonMinutes"]} minutes. Supported mode: deterministic synthetic beta only.</p></article>
      <article class="panel"><h2>Outputs</h2><ul>{items(card["outputs"], "sers-output")}</ul></article>
      <article class="panel"><h2>Input feature groups</h2><ul>{items(card["featureGroups"], "sers-feature")}</ul></article>
      <article class="panel"><h2>Intended use</h2><ul>{items(card["intendedUse"], "sers-use")}</ul></article>
      <article class="panel status-block"><h2>Prohibited use</h2><ul>{items(card["prohibitedUse"], "sers-prohibited")}</ul></article>
      <article class="panel status-block"><h2>Known limitations</h2><ul>{items(card["limitations"], "sers-limitation")}</ul></article>
    </section>
    <section class="panel"><div class="toolbar"><a class="button" href="/sers-model-card.json">Model card JSON</a><a class="button" href="/benchmark-explainability">Benchmark Explainability</a><a class="button" href="/model-benchmark">Model Benchmark</a></div></section>
  </main>
"""
    return page("ColdChain Sentinel SERS Model Card", body)


def benchmark_explainability_json() -> dict[str, Any]:
    benchmark = model_benchmark_json()
    return {
        "benchmarkMode": "On deterministic synthetic benchmark data, SERS is compared against simple baselines.",
        "datasetSummary": {
            "trainingRows": benchmark["model"]["trainingRows"],
            "testRows": benchmark["model"]["testRows"],
            "predictionHorizonMinutes": benchmark["model"]["predictionHorizonMinutes"],
            "features": benchmark["model"]["features"],
        },
        "baselineComparisons": {
            "SERS/model": benchmark["metrics"],
            "current-temperature threshold": benchmark["baselines"]["naiveCurrentTemperatureThreshold"],
            "rolling-average threshold": benchmark["baselines"]["rollingAverageThreshold"],
        },
        "metricDefinitions": {
            "accuracy": "share of synthetic test windows classified correctly",
            "precision": "share of predicted positive synthetic windows that were positive",
            "recall": "share of positive synthetic windows found by the model",
            "false positives": "synthetic windows flagged without a future breach label",
            "false negatives": "synthetic future breach windows missed",
            "confusion matrix": "true/false positives and true/false negatives",
        },
        "strengths": [
            "combines temperature, quality, consensus, door, and unresolved-pallet signals",
            "shows contributing factors for reviewer context",
            "keeps deterministic review facts unchanged",
        ],
        "knownFailureModes": [
            "synthetic labels may not match real vendor behavior",
            "low positive-label counts can make precision or recall uninformative",
            "sensor/vendor calibration is needed before pilots",
        ],
        "claimsBoundary": benchmark["claimsBoundary"],
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
    }


def render_benchmark_explainability() -> str:
    payload = benchmark_explainability_json()
    rows = []
    for name, metrics in payload["baselineComparisons"].items():
        rows.append([
            name,
            str(metrics["accuracy"]),
            str(metrics["precision"]),
            str(metrics["recall"]),
            str(metrics["falsePositives"]),
            str(metrics["falseNegatives"]),
            json.dumps(metrics["confusionMatrix"], sort_keys=True),
        ])
    body = f"""
  <header data-testid="benchmark-explainability-page">
    {global_nav()}
    <h1>Benchmark Explainability</h1>
    <p>On deterministic synthetic benchmark data, SERS is compared against simple baselines.</p>
    {badge("Synthetic only", "warn")}{badge("No real-world superiority claim", "warn")}
  </header>
  <main>
    <section class="panel"><h2>Dataset summary</h2><p>Training rows: {payload["datasetSummary"]["trainingRows"]}. Test rows: {payload["datasetSummary"]["testRows"]}. Horizon: {payload["datasetSummary"]["predictionHorizonMinutes"]} minutes.</p></section>
    <section class="panel"><h2>Metrics</h2>{table(["Method", "Accuracy", "Precision", "Recall", "False positives", "False negatives", "Confusion matrix"], rows, "benchmark-explainability-table")}</section>
    <section class="panel"><h2>What SERS adds on synthetic data</h2><ul>{items(payload["strengths"], "benchmark-strength")}</ul><p>Measured differences are shown above; no advantage is claimed when metrics do not support it.</p></section>
    <section class="panel status-block"><h2>Known failure modes and limitations</h2><ul>{items(payload["knownFailureModes"], "benchmark-failure")}</ul><p>{html.escape(payload["claimsBoundary"])}</p></section>
    <section class="panel"><div class="toolbar"><a class="button" href="/benchmark-explainability.json">Explainability JSON</a><a class="button" href="/model-benchmark">Model Benchmark</a><a class="button" href="/model-benchmark.json">Benchmark JSON</a><a class="button" href="/sers-model-card">SERS Model Card</a></div></section>
  </main>
"""
    return page("ColdChain Sentinel Benchmark Explainability", body)


def data_pipeline_json() -> dict[str, Any]:
    return {
        "syntheticOnly": True,
        "stages": [
            "raw vendor payload",
            "adapter normalization",
            "schema validation",
            "cleaning",
            "redundancy consensus",
            "SERS advisory risk score",
            "deterministic rule trace",
            "human-review packet",
        ],
        "fireworksAuthoritative": False,
        "autonomousActionsAllowed": False,
    }


def render_data_pipeline() -> str:
    rows = table(
        ["Stage", "Purpose"],
        [
            ["Raw vendor payload", "Synthetic native, flat logistics, or nested IoT-style sensor payload."],
            ["Adapter normalization", "Map source fields into Data Contract v2."],
            ["Schema validation", "Validate required fields and emit warnings for missing recommended context."],
            ["Cleaning", "Reject duplicates and impossible values; flag dropout, drift, outlier, low-battery, and weak-signal readings."],
            ["Redundancy consensus", "Compare neighboring sensors in a zone/time window for trust and conflict signals."],
            ["SERS risk score", "Advisory proprietary score from excursion severity, consensus, quality issues, door state, humidity, and evidence completeness."],
            ["Deterministic rule trace", "Authoritative rules derive excursion, pallet impact, blockers, and review status."],
            ["Human-review packet", "Reviewer workspace and audit exports; no autonomous action."],
        ],
        "data-pipeline-table",
    )
    body = f"""
  <header data-testid="data-pipeline-page">
    {global_nav()}
    <h1>Data Pipeline</h1>
    <p>raw vendor payload -> adapter normalization -> schema validation -> cleaning -> redundancy consensus -> SERS risk score -> deterministic rule trace -> review packet</p>
  </header>
  <main><section class="panel">{rows}</section><section class="panel"><div class="toolbar"><a class="button" href="/sensor-adapters">Sensor Adapters</a><a class="button" href="/data-contract">Data Contract v2</a></div></section></main>
"""
    return page("ColdChain Sentinel Data Pipeline", body)


def model_benchmark_json() -> dict[str, Any]:
    return benchmark_model(load_cases())


def render_model_benchmark() -> str:
    benchmark = model_benchmark_json()
    baseline_rows = [[name, str(values["accuracy"]), str(values["precision"]), str(values["recall"])] for name, values in benchmark["baselines"].items()]
    metric_rows = [["SYN-LR-0.1", str(benchmark["metrics"]["accuracy"]), str(benchmark["metrics"]["precision"]), str(benchmark["metrics"]["recall"])]]
    body = f"""
  <header data-testid="model-benchmark-page">
    {global_nav()}
    <h1>Model Benchmark</h1>
    <p>On deterministic synthetic benchmark data only. Predictions are advisory and never alter deterministic review facts.</p>
  </header>
  <main>
    <section class="panel"><h2>Model</h2><p>{html.escape(benchmark["model"]["modelName"])}. Training rows: {benchmark["model"]["trainingRows"]}. Test rows: {benchmark["model"]["testRows"]}. Horizon: {benchmark["model"]["predictionHorizonMinutes"]} minutes.</p>{table(["Model", "Accuracy", "Precision", "Recall"], metric_rows, "model-metrics")}</section>
    <section class="panel"><h2>Simple baselines</h2>{table(["Baseline", "Accuracy", "Precision", "Recall"], baseline_rows, "baseline-metrics")}</section>
    <section class="panel status-block"><h2>Claims boundary</h2><p>{html.escape(benchmark["claimsBoundary"])}</p></section>
    <section class="panel"><h2>Model governance</h2><div class="toolbar"><a class="button" href="/sers-model-card">SERS Model Card</a><a class="button" href="/benchmark-explainability">Benchmark Explainability</a></div></section>
  </main>
"""
    return page("ColdChain Sentinel Model Benchmark", body)


def render_public_data_readiness() -> str:
    rows = [[item["category"], item["possibleUse"], ", ".join(item["statuses"]), item["reasonNotIngested"]] for item in dataset_adapters_json()["adapterCandidates"]]
    body = f"""
  <header data-testid="public-data-readiness-page">
    {global_nav()}
    <h1>Public Data Readiness</h1>
    <p>No public dataset is currently ingested. The synthetic benchmark remains the only active benchmark; public data validation is planned, not claimed.</p>
  </header>
  <main><section class="panel">{table(["Candidate category", "Possible use", "Readiness statuses", "Reason not ingested"], rows, "public-data-readiness-table")}<div class="toolbar"><a class="button" href="/dataset-adapters">Dataset Adapters</a><a class="button" href="/dataset-license-checklist">License Checklist</a><a class="button" href="/public-dataset-benchmark-plan">Benchmark Plan</a></div></section></main>
"""
    return page("ColdChain Sentinel Public Data Readiness", body)


def dataset_adapters_json() -> dict[str, Any]:
    categories = [
        ("cold-chain/vaccine temperature datasets", "Excursion and calibration benchmarking"),
        ("IoT sensor anomaly datasets", "Cleaning and anomaly-rule evaluation"),
        ("environmental time-series datasets", "Time-series robustness evaluation"),
        ("warehouse/logistics telemetry datasets", "Schema and zone-mapping evaluation"),
        ("public API discovery directories", "Source discovery only; directories are not datasets"),
    ]
    return {
        "currentMode": "synthetic_only",
        "externalDatasetsIngested": False,
        "adapterCandidates": [
            {
                "category": category,
                "possibleUse": use,
                "requiredSchemaMapping": "Data Contract v2 normalized reading fields",
                "licenseTosStatus": "LICENSE_REVIEW_REQUIRED",
                "provenanceRequirements": "Source, version, collection method, and lineage must be documented.",
                "privacyRiskReview": "PRIVACY_RISK_REVIEW_REQUIRED",
                "ingestionStatus": "INGESTION_DEFERRED",
                "reasonNotIngested": "License/TOS, schema, provenance, and privacy review are incomplete.",
                "statuses": [
                    "SYNTHETIC_ONLY_CURRENTLY",
                    "LICENSE_REVIEW_REQUIRED",
                    "SCHEMA_MAPPING_REQUIRED",
                    "PROVENANCE_REVIEW_REQUIRED",
                    "PRIVACY_RISK_REVIEW_REQUIRED",
                    "INGESTION_DEFERRED",
                    "EXPERIMENTAL_ADAPTER_PLANNED",
                ],
            }
            for category, use in categories
        ],
        "requiredReviewSteps": [item["item"] for item in dataset_license_checklist_json()["checklist"]],
        "schemaMappingTargets": [
            "timestampUtc", "sensorId", "shipmentId", "zoneId", "temperatureC",
            "humidityPercent", "batteryPercent", "signalStrength", "readingSequence",
        ],
        "claimsBoundary": "No public dataset validation is claimed; deterministic synthetic benchmarks remain the only active benchmarks.",
        "safetyDisclaimers": ["No external datasets ingested.", "SERS remains advisory only.", "Deterministic rules remain authoritative."],
    }


def dataset_license_checklist_json() -> dict[str, Any]:
    items_list = [
        "source URL recorded", "license identified", "TOS checked", "commercial use checked",
        "redistribution rights checked", "attribution requirements checked", "data provenance documented",
        "privacy/PII risk reviewed", "schema mapped", "data quality profiled",
        "benchmark isolated from production claims", "claims boundary documented",
    ]
    return {"currentMode": "synthetic_only", "checklist": [{"item": item, "status": "required"} for item in items_list], "externalDatasetsIngested": False}


def public_dataset_benchmark_plan_json() -> dict[str, Any]:
    return {
        "currentMode": "synthetic_only",
        "externalDatasetsIngested": False,
        "steps": [
            "import reviewed dataset into isolated benchmark sandbox",
            "map fields to ColdChain normalized schema",
            "run cleaning pipeline",
            "generate quality report",
            "run SERS benchmark",
            "compare against simple baselines",
            "report metrics and failure modes",
            "update model card",
            "avoid production claims until real pilot validation",
        ],
        "claimsBoundary": "Future public benchmarks will remain isolated from production claims.",
        "sersAdvisoryOnly": True,
        "deterministicRulesAuthoritative": True,
    }


def render_dataset_adapters() -> str:
    payload = dataset_adapters_json()
    rows = [[item["category"], item["possibleUse"], item["licenseTosStatus"], item["ingestionStatus"], item["reasonNotIngested"]] for item in payload["adapterCandidates"]]
    body = f"""<header>{global_nav()}<h1>Public Dataset Adapters</h1><p>Synthetic data is the only active dataset. These adapter categories are plans, not ingested integrations.</p></header><main><section class="panel">{table(["Category", "Possible use", "License/TOS", "Ingestion", "Reason deferred"], rows, "dataset-adapters-table")}<div class="toolbar"><a class="button" href="/dataset-adapters.json">Adapter JSON</a><a class="button" href="/dataset-license-checklist">License Checklist</a></div></section></main>"""
    return page("ColdChain Sentinel Public Dataset Adapters", body)


def render_dataset_license_checklist() -> str:
    payload = dataset_license_checklist_json()
    rows = [[item["item"], item["status"]] for item in payload["checklist"]]
    body = f"""<header>{global_nav()}<h1>Dataset License Checklist</h1><p>Every item is required before external dataset ingestion.</p></header><main><section class="panel">{table(["Review item", "Status"], rows, "dataset-license-checklist")}<a class="button" href="/dataset-license-checklist.json">Checklist JSON</a></section></main>"""
    return page("ColdChain Sentinel Dataset License Checklist", body)


def render_public_dataset_benchmark_plan() -> str:
    payload = public_dataset_benchmark_plan_json()
    body = f"""<header>{global_nav()}<h1>Public Dataset Benchmark Plan</h1><p>Public data validation is planned, not claimed. No external dataset is currently ingested.</p></header><main><section class="panel"><ol>{items(payload["steps"], "benchmark-plan-step")}</ol><p>{html.escape(payload["claimsBoundary"])}</p><a class="button" href="/public-dataset-benchmark-plan.json">Plan JSON</a></section></main>"""
    return page("ColdChain Sentinel Public Dataset Benchmark Plan", body)


def render_case_detail(case_id: str) -> str:
    case = get_case(case_id)
    packet = case_packet(case)
    result = packet["result"]
    body = f"""
  <header data-testid="case-detail">
    {global_nav()}
    <h1>{html.escape(case["caseTitle"])}</h1>
    <p>{html.escape(case["scenarioSummary"])}</p>
    <nav><a href="/cases">Cases</a><a href="/cases/{html.escape(case_id)}/review">Reviewer workspace</a><a href="/cases/{html.escape(case_id)}/trace.json">Trace JSON</a><a href="/cases/{html.escape(case_id)}/evidence.json">Evidence JSON</a><a href="/cases/{html.escape(case_id)}/export.md">Export packet</a><a href="/cases/{html.escape(case_id)}/audit.md">Audit packet</a><a href="/ai-review?caseId={html.escape(case_id)}">AI Review</a><a href="/ai-review.json?caseId={html.escape(case_id)}">AI JSON</a></nav>
    {status_badges(result)}
  </header>
  <main>
    <section class="grid">
      <article class="panel"><h2>Shipment</h2><p class="metric">{html.escape(result["shipmentId"])}</p></article>
      <article class="panel"><h2>Review status</h2><p>{html.escape(result["reviewStatus"])}</p></article>
      <article class="panel"><h2>Final disposition</h2><p>{html.escape(result["finalDisposition"])}</p></article>
      <article class="panel status-block"><h2>Autonomous actions allowed</h2><p>{str(result["autonomousActionsAllowed"]).lower()}</p></article>
    </section>
  </main>
"""
    return page(case["caseTitle"], body)


def render_case_review(case_id: str, simulate_resolved: bool = False) -> str:
    case = get_case(case_id)
    packet = case_packet(case, simulate_resolved)
    before_packet = case_packet(case)
    result = packet["result"]
    sensors = sensor_summary(case, result)
    clean = cleaning_report(case)
    consensus = consensus_report(case)
    risk = sers_risk(case, result)
    sensor_preview = sensor_window(case, 0, 8)
    excursion = result["excursion"]
    mapped_table = table(
        ["Pallet", "Mapping state"],
        [[pallet_id, "synthetically mapped"] for pallet_id in result["mappedPalletIds"]],
        "mapped-pallet-table",
    )
    unresolved_table = table(
        ["Pallet", "Review state"],
        [[pallet_id, "missing synthetic zone mapping"] for pallet_id in result["unresolvedPalletIds"]]
        or [["None", "no unresolved synthetic pallet mapping"]],
        "unresolved-pallet-table",
    )
    blocker_table = table(
        ["Blocker", "Meaning"],
        [[blocker, blocker.replace("_", " ").title()] for blocker in result["blockers"]]
        or [["None", "review packet completion simulated"]],
        "blocker-table",
    )
    checklist = "\n".join(
        f"""
        <label class="check-row">
          <input type="checkbox" data-check-index="{index}">
          <span>{html.escape(item)}</span>
        </label>
"""
        for index, item in enumerate(packet["reviewerChecklist"])
    )
    disclaimers = items(packet["limitations"], "case-safety")
    timeline = timeline_items(packet["evidenceTimeline"])
    trace = trace_table(packet["ruleTrace"])
    telemetry = telemetry_table(packet["telemetryTimeline"], case["thresholdMaxC"])
    excursion_html = (
        f'<p data-testid="case-excursion">{fmt_time(excursion["startUtc"])} to {fmt_time(excursion["endUtc"])}. Duration: {excursion["durationMinutes"]} minutes. Zone: {html.escape(excursion["zoneId"])}.</p>'
        if excursion
        else '<p data-testid="case-excursion">No temperature excursion in this synthetic control fixture.</p>'
    )
    can_simulate = case_id == "blocked-unresolved-pallet" and not simulate_resolved
    simulation_link = (
        f'<a class="button" href="/cases/{html.escape(case_id)}/review?simulateResolved=true">Simulate resolving missing mapping</a>'
        if can_simulate
        else ""
    )
    sim_note = ""
    comparison = ""
    if simulate_resolved and case_id == "blocked-unresolved-pallet":
        before = before_packet["result"]
        comparison = table(
            ["Field", "Before", "After simulation"],
            [
                ["unresolvedPalletIds", ", ".join(before["unresolvedPalletIds"]), "None; PAL-SYN-1004 synthetically mapped"],
                ["finalDisposition", before["finalDisposition"], result["finalDisposition"]],
                ["reviewStatus", before["reviewStatus"], result["reviewStatus"]],
                ["autonomousActionsAllowed", str(before["autonomousActionsAllowed"]).lower(), str(result["autonomousActionsAllowed"]).lower()],
            ],
            "simulation-comparison",
        )
        sim_note = (
            '<section class="panel status-block" data-testid="simulated-resolution">'
            "<h2>Simulated mapping resolution</h2>"
            "<p>PAL-SYN-1004 is synthetically mapped for review packet completion.</p>"
            "<p>This is a synthetic review packet completion, not an operational decision.</p>"
            f"{comparison}</section>"
        )
    checklist_count = len(packet["reviewerChecklist"])
    sim_key = "simulated" if simulate_resolved else "standard"
    unresolved_count = len(result["unresolvedPalletIds"])
    checklist_script = f"""
  <script>
    (() => {{
      const caseId = "{html.escape(case_id)}";
      const simState = "{sim_key}";
      const key = "coldchain-checklist:" + caseId + ":" + simState;
      const notesKey = "coldchain-notes:" + caseId + ":" + simState;
      const boxes = Array.from(document.querySelectorAll("[data-check-index]"));
      const progress = document.querySelector("[data-check-progress]");
      const summaryProgress = document.querySelector("[data-session-progress]");
      const notes = document.querySelector("[data-local-notes]");
      const notesPresent = document.querySelector("[data-notes-present]");
      const packetStatus = document.querySelector("[data-packet-completeness]");
      const copyStatus = document.querySelector("[data-copy-status]");
      const saved = JSON.parse(localStorage.getItem(key) || "{{}}");
      function render() {{
        const reviewed = boxes.filter((box) => box.checked).length;
        const progressText = reviewed + "/{checklist_count} reviewed";
        progress.textContent = progressText;
        summaryProgress.textContent = progressText;
        notesPresent.textContent = notes.value.trim() ? "yes" : "no";
        packetStatus.textContent = reviewed === 0
          ? "DEMO_PACKET_INCOMPLETE"
          : (reviewed === boxes.length && {unresolved_count} === 0 ? "DEMO_PACKET_READY_FOR_HUMAN_REVIEW_ARCHIVE" : "DEMO_PACKET_REVIEWING");
        const state = Object.fromEntries(boxes.map((box) => [box.dataset.checkIndex, box.checked]));
        localStorage.setItem(key, JSON.stringify(state));
        localStorage.setItem(notesKey, notes.value);
      }}
      boxes.forEach((box) => {{
        box.checked = Boolean(saved[box.dataset.checkIndex]);
        box.addEventListener("change", render);
      }});
      notes.value = localStorage.getItem(notesKey) || "";
      notes.addEventListener("input", render);
      document.querySelector("[data-clear-local-session]").addEventListener("click", () => {{
        boxes.forEach((box) => {{ box.checked = false; }});
        notes.value = "";
        localStorage.removeItem(key);
        localStorage.removeItem(notesKey);
        render();
      }});
      document.querySelector("[data-copy-session-summary]").addEventListener("click", async () => {{
        const text = [
          "ColdChain Sentinel local demo review session",
          "caseId: " + caseId,
          "simulationMode: " + simState,
          "checklistProgress: " + progress.textContent,
          "localNotesPresent: " + notesPresent.textContent,
          "autonomousActionsAllowed: false",
          "localNotes:",
          notes.value || "(none)"
        ].join("\\n");
        try {{
          await navigator.clipboard.writeText(text);
          copyStatus.textContent = "Local session summary copied.";
        }} catch (_error) {{
          copyStatus.textContent = text;
        }}
      }});
      render();
    }})();
  </script>
"""
    ai_href = f"/ai-review?caseId={html.escape(case_id)}"
    ai_json_href = f"/ai-review.json?caseId={html.escape(case_id)}"
    export_href = f"/cases/{html.escape(case_id)}/export.md"
    if simulate_resolved:
        export_href += "?simulateResolved=true"
    audit_href = f"/cases/{html.escape(case_id)}/audit.md"
    if simulate_resolved:
        audit_href += "?simulateResolved=true"
    evidence_href = f"/cases/{html.escape(case_id)}/evidence.json"
    if simulate_resolved:
        evidence_href += "?simulateResolved=true"
    fireworks_panel = (
        f'<section class="panel" data-testid="fireworks-panel"><h2>Fireworks assistant</h2>'
        "<p>Optional reviewer explanation only. Deterministic rules remain authoritative.</p>"
        f'<div class="toolbar"><a class="button" href="{ai_href}">Open AI review</a><a class="button" href="{ai_json_href}">AI JSON</a></div></section>'
    )
    trace_href = f"/cases/{html.escape(case_id)}/trace.json"
    if simulate_resolved:
        trace_href += "?simulateResolved=true"
    export_panel = (
        f'<section class="panel" data-testid="export-panel"><h2>Export packet</h2>'
        "<p>Markdown and JSON exports contain synthetic review evidence only.</p>"
        f'<div class="toolbar"><a class="button" href="{trace_href}">Trace JSON</a><a class="button" href="{evidence_href}">Evidence JSON</a><a class="button" href="{export_href}">Export markdown</a><a class="button" href="{audit_href}">Audit packet</a>'
        + (
            f'<a class="button" href="/cases/{html.escape(case_id)}/audit.md?simulateResolved=true">Simulated audit packet</a>'
            if case_id == "blocked-unresolved-pallet" and not simulate_resolved
            else ""
        )
        + "</div></section>"
    )
    body = f"""
  <header data-testid="case-review">
    {global_nav()}
    <h1>{html.escape(case["caseTitle"])}</h1>
    <p>{html.escape(case["scenarioSummary"])}</p>
    <nav><a href="/cases">Cases</a><a href="{trace_href}">Trace JSON</a><a href="{evidence_href}">Evidence JSON</a><a href="{export_href}">Export packet</a><a href="{audit_href}">Audit packet</a><a href="{ai_href}">AI Review Assistant</a><a href="{ai_json_href}">AI JSON</a></nav>
    {status_badges(result)}
  </header>
  <main>
    {sim_note}
    <section class="grid" data-testid="case-header">
      <article class="panel"><h2>Shipment facts</h2><p class="metric">{html.escape(result["shipmentId"])}</p><p>Case ID: {html.escape(case_id)}</p></article>
      <article class="panel status-block" data-testid="deterministic-status-card"><h2>Deterministic status</h2><p>finalDisposition: {html.escape(result["finalDisposition"])}</p><p>reviewStatus: {html.escape(result["reviewStatus"])}</p><p>autonomousActionsAllowed: {str(result["autonomousActionsAllowed"]).lower()}</p><p>Synthetic demo only. Not a real-world operational decision. No autonomous action.</p></article>
      <article class="panel" data-testid="review-session-summary"><h2>Review session summary</h2><p>Selected case: {html.escape(case_id)}</p><p>Simulation mode: {html.escape(sim_key)}</p><p>Checklist progress: <span data-session-progress>0/{checklist_count} reviewed</span></p><p>Local notes present: <span data-notes-present>no</span></p><p>Trace status: available</p><p>Evidence packet: available</p><p>Export packet: available</p><p>autonomousActionsAllowed: false</p></article>
      <article class="panel" data-testid="packet-completeness-meter"><h2>Packet completeness</h2><p class="metric" data-packet-completeness>DEMO_PACKET_INCOMPLETE</p><p>Demo archive readiness only; not a regulatory or operational status.</p></article>
    </section>
    <section class="panel" data-testid="manual-resolution-panel"><h2>Manual resolution simulation</h2><p>Current unresolved pallet: {html.escape(", ".join(before_packet["result"]["unresolvedPalletIds"]) or "None")}</p><div class="toolbar">{simulation_link}</div></section>
    <section class="panel" data-testid="case-excursion-panel"><h2>Excursion</h2>{excursion_html}</section>
    {sensor_summary_panel(case_id, sensors)}
    {sensor_intelligence_panel(case_id, clean, consensus, risk)}
    <section class="panel" data-testid="sensor-window-preview-panel"><h2>Sensor window preview</h2><p>Small deterministic sample window only; use JSON route with offset and capped limit for paging.</p>{sensor_preview_table(sensor_preview["readings"])}</section>
    <section class="panel" data-testid="synthetic-telemetry-timeline"><h2>Synthetic temperature timeline</h2><p>Threshold: {case["thresholdMaxC"]} C. Above-threshold readings are labeled as review signals.</p>{excursion_html}{telemetry}</section>
    <section class="panel" data-testid="evidence-timeline"><h2>Evidence timeline</h2><ul>{timeline}</ul></section>
    <section class="panel" data-testid="rule-trace-panel"><h2>Deterministic Rule Trace</h2><p>Rule trace is deterministic and does not depend on Fireworks.</p>{trace}</section>
    <section class="grid">
      <article class="panel"><h2>Mapped pallet table</h2>{mapped_table}</article>
      <article class="panel status-block"><h2>Unresolved pallet table</h2>{unresolved_table}</article>
      <article class="panel status-block"><h2>Blocker explanation</h2>{blocker_table}</article>
      <article class="panel" data-testid="reviewer-checklist-workspace"><h2>Reviewer checklist</h2><p data-check-progress>0/{checklist_count} reviewed</p><p>Local demo checklist only. Stored in browser localStorage and not sent to the server.</p>{checklist}<button class="button" type="button" data-clear-local-session>Clear local checklist and notes</button></article>
      <article class="panel" data-testid="local-reviewer-notes"><h2>Reviewer notes</h2><p>Local demo notes only. Not uploaded, not persisted server-side.</p><textarea data-local-notes rows="8" style="width:100%" aria-label="Local demo reviewer notes"></textarea><div class="toolbar"><button class="button" type="button" data-copy-session-summary>Copy local session summary</button></div><p class="muted" data-copy-status></p></article>
      {fireworks_panel}
      {export_panel}
      <article class="panel status-block"><h2>Safety disclaimers</h2><ul>{disclaimers}</ul></article>
    </section>
  </main>
  {checklist_script}
"""
    return page(f"{case['caseTitle']} Review", body)


def render_review_packet(case: dict[str, Any] | None = None) -> str:
    packet = build_review_packet(case or load_fixture())
    result = packet["result"]
    excursion = result["excursion"]
    body = f"""
  <header data-testid="review-packet-page">
    {global_nav()}
    <h1>Human Review Packet</h1>
    <p data-testid="packet-synthetic-label">Synthetic demo data only. This is not a validated pharmaceutical, medical, or compliance product.</p>
    {badge("Final disposition blocked", "danger")}{badge("Human review required", "warn")}{badge("Fireworks optional", "warn")}
  </header>
  <main>
    <section class="grid">
      <article class="panel" data-testid="packet-shipment"><h2>Shipment</h2><p class="metric">{html.escape(result["shipmentId"])}</p></article>
      <article class="panel" data-testid="packet-excursion"><h2>Excursion</h2><p>{fmt_time(excursion["startUtc"])} to {fmt_time(excursion["endUtc"])}</p><p class="metric">{excursion["durationMinutes"]} minutes</p></article>
      <article class="panel status-block" data-testid="packet-status"><h2>Status</h2><p data-testid="packet-final-disposition">Final disposition blocked.</p><p data-testid="packet-human-review">Human review required.</p></article>
    </section>

    <section class="grid">
      <article class="panel" data-testid="packet-mapped-pallets"><h2>Mapped pallets</h2><ul>{items(result["mappedPalletIds"], "packet-mapped")}</ul></article>
      <article class="panel status-block" data-testid="packet-unresolved-pallets"><h2>Unresolved evidence</h2><ul>{items(packet["unresolvedEvidence"], "packet-unresolved")}</ul></article>
    </section>

    <section class="grid">
      <article class="panel status-block" data-testid="packet-blocking-reasons"><h2>Blocking reasons</h2><ul>{items(packet["blockingReasons"], "packet-blocking-reason")}</ul></article>
      <article class="panel status-block" data-testid="packet-prohibited-actions"><h2>Prohibited autonomous actions</h2><ul>{items(packet["prohibitedAutonomousActions"], "packet-prohibited")}</ul></article>
    </section>

    <section class="grid">
      <article class="panel" data-testid="reviewer-checklist"><h2>Human reviewer checklist</h2><ul>{items(packet["reviewerChecklist"], "review-check")}</ul></article>
      <article class="panel" data-testid="next-inspection"><h2>Reviewer should inspect next</h2><ul>{items(packet["nextInspection"], "next-inspect")}</ul></article>
    </section>

    <section class="panel" data-testid="packet-limitations"><h2>Limitations</h2><p>{html.escape(packet["productBoundary"])}</p><ul>{items(packet["limitations"], "packet-limitation")}</ul></section>
  </main>
"""
    return page("ColdChain Sentinel Review Packet", body)


def render_ai_review(case: dict[str, Any] | None = None, case_id: str | None = None) -> str:
    packet = case_packet(get_case(case_id)) if case_id else build_review_packet(case or load_fixture())
    ai_review = build_ai_review(packet)
    result = ai_review["deterministicResult"]
    provider = ai_review["assistant"]["provider"]
    brief = ai_review["assistant"]["brief"]
    safety_items = items(ai_review["safety"], "ai-safety")
    checklist_items = items([str(value) for value in brief["reviewerChecklist"]], "ai-check")
    missing_items = items([str(value) for value in brief["missingEvidence"]], "ai-missing")
    root_cause_items = items([str(value) for value in brief["rootCauseHypotheses"]], "ai-root-cause")
    why_items = items([str(value) for value in brief["whyBlocked"]], "ai-why-blocked")
    source = provider["displayedBriefSource"]
    source_label = (
        "<p><strong>Sanitized Fireworks-generated reviewer brief, non-authoritative.</strong></p>"
        if source == "sanitized_fireworks_text"
        else ""
    )
    case_identity = f'<p data-testid="ai-selected-case">Selected case: {html.escape(packet.get("caseId", "baseline"))} - {html.escape(packet.get("caseTitle", "Baseline review packet"))}</p>'
    body = f"""
  <header data-testid="ai-review-page">
    {global_nav()}
    <h1>AI Review Assistant</h1>
    <p data-testid="ai-scope-note">AI-assisted explanation only. Deterministic rules remain authoritative.</p>
    {case_identity}
    <nav><a href="/">Dashboard</a><a href="/review">Review packet</a><a href="/ai-review.json">AI Review JSON</a></nav>
    {badge("Fireworks configured: " + ("yes" if provider["fireworksConfigured"] else "no"), "good" if provider["fireworksConfigured"] else "warn")}
    {badge("Fireworks call succeeded: " + ("yes" if provider["fireworksCallSucceeded"] else "no"), "good" if provider["fireworksCallSucceeded"] else "warn")}
    {badge("Structured output verified: " + ("yes" if provider["fireworksStructuredOutputVerified"] else "no"), "good" if provider["fireworksStructuredOutputVerified"] else "warn")}
    {badge("Displayed brief source: " + source, "good" if source != "deterministic_fallback" else "warn")}
    {badge("AMD status: pending/not configured", "warn")}
  </header>
  <main>
    <section class="grid" aria-label="Provider status">
      <article class="panel" data-testid="provider-status"><h2>Provider status</h2><p>{html.escape(provider["status"])}</p><p>Model: {html.escape(provider["fireworksModel"])}</p><p>Displayed brief source: {html.escape(source)}</p><p>AMD status: pending/not configured.</p></article>
      <article class="panel status-block" data-testid="ai-safety-boundary"><h2>Safety boundary</h2><ul>{safety_items}</ul></article>
    </section>

    <section class="grid" aria-label="Deterministic facts">
      <article class="panel" data-testid="ai-shipment-id"><h2>Shipment</h2><p class="metric">{html.escape(result["shipmentId"])}</p></article>
      <article class="panel" data-testid="ai-duration"><h2>Excursion duration</h2><p class="metric">{result["excursion"]["durationMinutes"] if result["excursion"] else "None"}{ " minutes" if result["excursion"] else ""}</p></article>
      <article class="panel status-block" data-testid="ai-final-disposition"><h2>Final disposition</h2><p class="metric">{html.escape(result["finalDisposition"])}</p></article>
      <article class="panel status-block" data-testid="ai-review-status"><h2>Review status</h2><p>{html.escape(result["reviewStatus"])}</p></article>
      <article class="panel status-block" data-testid="ai-unresolved-pallet"><h2>Unresolved pallet</h2><p>{html.escape(", ".join(result["unresolvedPalletIds"]))}</p></article>
      <article class="panel status-block" data-testid="ai-autonomous-actions"><h2>Autonomous actions allowed</h2><p>{str(result["autonomousActionsAllowed"]).lower()}</p></article>
    </section>

    <section class="grid" aria-label="AI reviewer brief">
      <article class="panel" data-testid="ai-summary"><h2>Reviewer brief</h2>{source_label}<p>{html.escape(str(brief["summary"]))}</p></article>
      <article class="panel status-block" data-testid="ai-why-blocked"><h2>Why blocked</h2><ul>{why_items}</ul></article>
      <article class="panel status-block" data-testid="ai-missing-evidence"><h2>Missing evidence</h2><ul>{missing_items}</ul></article>
      <article class="panel" data-testid="ai-reviewer-checklist"><h2>Reviewer checklist</h2><ul>{checklist_items}</ul></article>
      <article class="panel" data-testid="ai-root-cause"><h2>Root-cause hypotheses</h2><ul>{root_cause_items}</ul></article>
      <article class="panel" data-testid="ai-safety-note"><h2>Safety note</h2><p>{html.escape(str(brief["safetyNote"]))}</p></article>
    </section>
  </main>
"""
    return page("ColdChain Sentinel AI Review Assistant", body)

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        case_id = query.get("caseId", [None])[0]
        simulate_resolved = query.get("simulateResolved", ["false"])[0].lower() == "true"
        if path in ("/", "/index.html"):
            self.respond_text(render_dashboard())
            return
        if path == "/command-center":
            self.respond_text(render_command_center())
            return
        if path == "/command-center.json":
            self.respond_json(command_center_payload())
            return
        if path == "/sensor-lab":
            self.respond_text(render_sensor_lab())
            return
        if path == "/sensor-lab.json":
            self.respond_json(sensor_lab_payload())
            return
        if path == "/beta-readiness":
            self.respond_text(render_beta_readiness())
            return
        if path == "/system-status.json":
            self.respond_json(system_status_json())
            return
        if path == "/validation-evidence":
            self.respond_text(render_validation_evidence())
            return
        if path == "/validation-evidence.json":
            self.respond_json(validation_evidence_json())
            return
        if path == "/roadmap":
            self.respond_text(render_roadmap())
            return
        if path == "/data-contract":
            self.respond_text(render_data_contract())
            return
        if path == "/data-contract.json":
            self.respond_json(data_contract_json())
            return
        if path == "/sensor-adapters":
            self.respond_text(render_sensor_adapters())
            return
        if path == "/sensor-adapters.json":
            self.respond_json(sensor_adapters_json())
            return
        if path == "/sensor-adapters/example.json":
            source_format = query.get("format", [None])[0]
            if not source_format:
                self.respond_json(example_results())
                return
            try:
                self.respond_json(example_results(source_format))
            except KeyError:
                self.respond_json({"error": "unknown synthetic adapter format", "format": source_format})
            return
        if path == "/data-pipeline":
            self.respond_text(render_data_pipeline())
            return
        if path == "/data-pipeline.json":
            self.respond_json(data_pipeline_json())
            return
        if path == "/model-benchmark":
            self.respond_text(render_model_benchmark())
            return
        if path == "/model-benchmark.json":
            self.respond_json(model_benchmark_json())
            return
        if path == "/sers-model-card":
            self.respond_text(render_sers_model_card())
            return
        if path == "/sers-model-card.json":
            self.respond_json(sers_model_card_json())
            return
        if path == "/benchmark-explainability":
            self.respond_text(render_benchmark_explainability())
            return
        if path == "/benchmark-explainability.json":
            self.respond_json(benchmark_explainability_json())
            return
        if path == "/public-data-readiness":
            self.respond_text(render_public_data_readiness())
            return
        if path == "/dataset-adapters":
            self.respond_text(render_dataset_adapters())
            return
        if path == "/dataset-adapters.json":
            self.respond_json(dataset_adapters_json())
            return
        if path == "/dataset-license-checklist":
            self.respond_text(render_dataset_license_checklist())
            return
        if path == "/dataset-license-checklist.json":
            self.respond_json(dataset_license_checklist_json())
            return
        if path == "/public-dataset-benchmark-plan":
            self.respond_text(render_public_dataset_benchmark_plan())
            return
        if path == "/public-dataset-benchmark-plan.json":
            self.respond_json(public_dataset_benchmark_plan_json())
            return
        if path == "/cases":
            self.respond_text(render_cases())
            return
        if path.startswith("/cases/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 2:
                try:
                    selected = parts[1]
                    if len(parts) == 2:
                        self.respond_text(render_case_detail(selected))
                        return
                    if parts[2] == "review":
                        self.respond_text(render_case_review(selected, simulate_resolved))
                        return
                    if parts[2] == "evidence.json":
                        self.respond_json(evidence_json(get_case(selected), simulate_resolved))
                        return
                    if parts[2] == "trace.json":
                        self.respond_json(trace_json(get_case(selected), simulate_resolved))
                        return
                    if parts[2] == "export.md":
                        self.respond_markdown(export_markdown(get_case(selected), simulate_resolved))
                        return
                    if parts[2] == "audit.md":
                        self.respond_markdown(audit_markdown(get_case(selected), simulate_resolved))
                        return
                    if parts[2] == "sensor-summary.json":
                        packet = case_packet(get_case(selected), simulate_resolved)
                        self.respond_json(sensor_summary(get_case(selected), packet["result"]))
                        return
                    if parts[2] == "sensor-window.json":
                        try:
                            offset = int(query.get("offset", ["0"])[0])
                            limit = int(query.get("limit", ["100"])[0])
                        except ValueError:
                            self.respond_json({"error": "offset and limit must be integers"})
                            return
                        self.respond_json(sensor_window(get_case(selected), offset, limit))
                        return
                    if parts[2] == "cleaning-report.json":
                        self.respond_json(cleaning_report(get_case(selected)))
                        return
                    if parts[2] == "prediction.json":
                        packet = case_packet(get_case(selected), simulate_resolved)
                        self.respond_json(prediction_report(get_case(selected), packet["result"], load_cases()))
                        return
                except KeyError:
                    self.respond_text(render_not_found(parts[1]), 404)
                    return
        if path == "/review":
            self.respond_text(render_review_packet())
            return
        if path == "/ai-review":
            try:
                self.respond_text(render_ai_review(case_id=case_id))
            except KeyError:
                self.respond_text(render_not_found(case_id), 404)
            return
        if path == "/api/baseline":
            self.respond_json(evaluate_case(load_fixture()))
            return
        if path == "/review.json":
            self.respond_json(build_review_packet(load_fixture()))
            return
        if path == "/ai-review.json":
            try:
                packet = case_packet(get_case(case_id)) if case_id else build_review_packet(load_fixture())
            except KeyError:
                self.respond_text(render_not_found(case_id), 404)
                return
            self.respond_json(build_ai_review(packet))
            return
        if path == "/health":
            self.respond_json({"ok": True, "providers": "disabled"})
            return
        self.respond_text(render_not_found(), 404)

    def respond_text(self, content: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def respond_json(self, content: dict[str, Any]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(content, sort_keys=True).encode("utf-8"))

    def respond_markdown(self, content: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return


def self_check() -> None:
    dashboard = render_dashboard()
    review = render_review_packet()
    ai_review = render_ai_review()
    packet = build_review_packet(load_fixture())
    required = [
        'data-testid="demo-overview"',
        'data-testid="review-packet-link"',
        'data-testid="ai-review-link"',
        'data-testid="review-packet-page"',
        'data-testid="ai-review-page"',
        'data-testid="provider-status"',
        "AI-assisted explanation only.",
        'data-testid="packet-blocking-reasons"',
        'data-testid="packet-prohibited-actions"',
        'data-testid="reviewer-checklist"',
        'data-testid="next-inspection"',
        "Synthetic demo data only.",
        "Deterministic rules are authoritative.",
        "Final disposition blocked.",
        "Human review required.",
        "No autonomous release.",
        "not a validated pharmaceutical, medical, or compliance product",
        "PAL-SYN-1004 has missing zone mapping.",
    ]
    combined = dashboard + review + ai_review + json.dumps(packet, sort_keys=True)
    for text in required:
        assert text in combined, text
    assert packet["result"]["excursion"]["durationMinutes"] == 45
    assert packet["result"]["finalDisposition"] == "BLOCKED"
    assert packet["result"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ColdChain Sentinel deterministic dashboard.")
    parser.add_argument("--check", action="store_true", help="Render dashboard/review packet and run assertions.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    if args.check:
        self_check()
        print("dashboard and review packet self-check passed")
        return

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"ColdChain Sentinel dashboard: http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
