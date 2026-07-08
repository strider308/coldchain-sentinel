"""Stdlib validation suite for the ColdChain Sentinel deterministic demo."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SNAPSHOTS = ROOT / "tests" / "golden_snapshots.json"
sys.path.insert(0, str(SRC))

import ai_review_assistant  # noqa: E402
from case_engine import case_packet, get_case, load_cases  # noqa: E402
from coldchain_baseline import build_review_packet, evaluate_case, load_fixture  # noqa: E402
from sensor_adapters import SUPPORTED_FORMATS, first_example, normalize  # noqa: E402
from sensor_engine import (  # noqa: E402
    cleaning_report,
    consensus_report,
    prediction_report,
    sensor_summary,
    sensor_window,
    sers_risk,
    synthetic_readings,
)
from serve_dashboard import (  # noqa: E402
    DashboardHandler,
    command_center_payload,
    model_benchmark_json,
    render_ai_review,
    render_dashboard,
    render_review_packet,
    sensor_lab_payload,
    system_status_json,
    validation_evidence_json,
)


def assert_contains(text: str, needles: list[str]) -> None:
    for needle in needles:
        assert needle in text, needle


def test_deterministic_baseline(case: dict[str, Any]) -> None:
    result = evaluate_case(case)

    assert case["dataClassification"] == "synthetic"
    assert result["excursion"]["startUtc"] == "2026-06-26T10:30:00Z"
    assert result["excursion"]["endUtc"] == "2026-06-26T11:15:00Z"
    assert result["excursion"]["durationMinutes"] == 45
    assert result["mappedPalletIds"] == ["PAL-SYN-1001", "PAL-SYN-1002", "PAL-SYN-1003"]
    assert result["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert result["finalDisposition"] == "BLOCKED"
    assert result["reviewStatus"] == "HUMAN_REVIEW_REQUIRED"
    assert result["autonomousActionsAllowed"] is False
    assert "TEMPERATURE_EXCURSION_DETECTED" in result["blockers"]
    assert "UNRESOLVED_PALLET_MAPPING" in result["blockers"]
    assert "HUMAN_REVIEW_REQUIRED" in result["blockers"]


def test_review_packet(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    result = packet["result"]

    assert packet["dataClassification"] == "synthetic"
    assert packet["unresolvedEvidence"] == ["PAL-SYN-1004 has missing zone mapping."]
    assert result == evaluate_case(case)
    assert_contains(
        "\n".join(packet["blockingReasons"]),
        [
            "Temperature excursion detected.",
            "PAL-SYN-1004 has missing zone mapping.",
            "Final disposition cannot be completed safely from the deterministic baseline.",
        ],
    )
    assert packet["prohibitedAutonomousActions"] == [
        "No autonomous release.",
        "No autonomous quarantine.",
        "No autonomous discard.",
        "No autonomous reroute.",
        "No autonomous customer notification.",
    ]


def test_rendered_pages(case: dict[str, Any]) -> None:
    dashboard = render_dashboard(case)
    review = render_review_packet(case)
    ai_review = render_ai_review(case)

    assert_contains(
        dashboard,
        [
            'data-testid="demo-overview"',
            'data-testid="shipment-dashboard"',
            'data-testid="excursion-timeline"',
            'data-testid="mapping-status"',
            'data-testid="final-disposition-blocked"',
            'data-testid="human-review-required"',
            'data-testid="unresolved-PAL-SYN-1004"',
            "Synthetic demo data only.",
            "Deterministic rules are authoritative.",
            "No autonomous release, quarantine, discard, reroute, or customer notification.",
        ],
    )
    assert_contains(
        ai_review,
        [
            'data-testid="ai-review-page"',
            'data-testid="provider-status"',
            "AI-assisted explanation only.",
            "Deterministic rules remain authoritative.",
            "No autonomous release, quarantine, discard, reroute, or customer notification.",
            "Synthetic demo data only.",
            "Not a validated pharmaceutical, medical, logistics compliance, or medical product.",
        ],
    )

    assert_contains(
        review,
        [
            'data-testid="review-packet-page"',
            'data-testid="packet-blocking-reasons"',
            'data-testid="packet-prohibited-actions"',
            'data-testid="reviewer-checklist"',
            'data-testid="next-inspection"',
            "Final disposition blocked.",
            "Human review required.",
            "not a validated pharmaceutical, medical, or compliance product",
        ],
    )


def test_sensor_adapters_normalize_and_validate() -> None:
    for source_format in SUPPORTED_FORMATS:
        clean = normalize(source_format, first_example(source_format))
        assert clean["accepted"] is True
        assert clean["errors"] == []
        normalized = clean["normalizedReading"]
        assert normalized["sourceFormat"] == source_format
        assert normalized["adapterVersion"] == "sensor-adapter-v2-synthetic"
        assert set(("timestampUtc", "sensorId", "shipmentId", "temperatureC")).issubset(normalized)

        bad = dict(first_example(source_format))
        if source_format == "sentinel_native_v1":
            bad["temperatureC"] = 99.9
            missing = dict(bad)
            missing.pop("timestampUtc", None)
        elif source_format == "vendor_flat_csv_v1":
            bad["temp_c"] = "99.9"
            missing = dict(bad)
            missing.pop("ts", None)
        else:
            bad = json.loads(json.dumps(bad))
            bad["reading"]["temperature"]["value"] = 99.9
            bad["reading"]["temperature"]["unit"] = "C"
            missing = json.loads(json.dumps(bad))
            missing["reading"].pop("timestamp", None)

        rejected = normalize(source_format, bad)
        assert rejected["accepted"] is False
        assert any("temperatureC" in error for error in rejected["errors"])

        missing_required = normalize(source_format, missing)
        assert missing_required["accepted"] is False
        assert any("missing required field" in error for error in missing_required["errors"])

    optional = {
        "timestampUtc": "2026-06-26T10:35:00Z",
        "sensorId": "SYN-OPTIONAL",
        "shipmentId": "SYN-SHIP-2026-06-26-A",
        "temperatureC": 6.2,
    }
    warning_result = normalize("sentinel_native_v1", optional)
    assert warning_result["accepted"] is True
    assert "missing recommended field: readingSequence" in warning_result["warnings"]
    assert "missing recommended field: zoneId" in warning_result["warnings"]


def fetch(base_url: str, path: str) -> tuple[int, str]:
    with urllib.request.urlopen(base_url + path, timeout=5) as response:
        return response.status, response.read().decode("utf-8")


def fetch_any(base_url: str, path: str) -> tuple[int, str]:
    try:
        return fetch(base_url, path)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


def test_routes(case: dict[str, Any]) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        dashboard_status, dashboard = fetch(base_url, "/")
        command_center_status, command_center = fetch(base_url, "/command-center")
        command_center_json_status, command_center_json = fetch(base_url, "/command-center.json")
        review_status, review = fetch(base_url, "/review")
        review_json_status, review_json = fetch(base_url, "/review.json")
        ai_review_status, ai_review = fetch(base_url, "/ai-review")
        ai_review_json_status, ai_review_json = fetch(base_url, "/ai-review.json")
        cases_status, cases_page = fetch(base_url, "/cases")
        sensor_lab_status, sensor_lab = fetch(base_url, "/sensor-lab")
        sensor_lab_json_status, sensor_lab_json = fetch(base_url, "/sensor-lab.json")
        data_contract_status, data_contract = fetch(base_url, "/data-contract")
        data_contract_json_status, data_contract_json = fetch(base_url, "/data-contract.json")
        sensor_adapters_status, sensor_adapters = fetch(base_url, "/sensor-adapters")
        sensor_adapters_json_status, sensor_adapters_json = fetch(base_url, "/sensor-adapters.json")
        adapter_example_statuses = [
            fetch(base_url, f"/sensor-adapters/example.json?format={source_format}")
            for source_format in SUPPORTED_FORMATS
        ]
        data_pipeline_status, data_pipeline = fetch(base_url, "/data-pipeline")
        data_pipeline_json_status, data_pipeline_json = fetch(base_url, "/data-pipeline.json")
        model_benchmark_status, model_benchmark = fetch(base_url, "/model-benchmark")
        model_benchmark_json_status, model_benchmark_json = fetch(base_url, "/model-benchmark.json")
        public_data_status, public_data_page = fetch(base_url, "/public-data-readiness")
        roadmap_status, roadmap_page = fetch(base_url, "/roadmap")
        baseline_case_status, baseline_case = fetch(base_url, "/cases/blocked-unresolved-pallet")
        baseline_case_review_status, baseline_case_review = fetch(base_url, "/cases/blocked-unresolved-pallet/review")
        simulated_status, simulated_review = fetch(
            base_url, "/cases/blocked-unresolved-pallet/review?simulateResolved=true"
        )
        baseline_trace_status, baseline_trace = fetch(base_url, "/cases/blocked-unresolved-pallet/trace.json")
        baseline_evidence_status, baseline_evidence = fetch(base_url, "/cases/blocked-unresolved-pallet/evidence.json")
        baseline_export_status, baseline_export = fetch(base_url, "/cases/blocked-unresolved-pallet/export.md")
        baseline_audit_status, baseline_audit = fetch(base_url, "/cases/blocked-unresolved-pallet/audit.md")
        baseline_sensor_summary_status, baseline_sensor_summary = fetch(
            base_url, "/cases/blocked-unresolved-pallet/sensor-summary.json"
        )
        baseline_sensor_window_status, baseline_sensor_window = fetch(
            base_url, "/cases/blocked-unresolved-pallet/sensor-window.json"
        )
        capped_sensor_window_status, capped_sensor_window = fetch(
            base_url, "/cases/blocked-unresolved-pallet/sensor-window.json?offset=0&limit=900"
        )
        cleaning_status, cleaning_text = fetch(base_url, "/cases/blocked-unresolved-pallet/cleaning-report.json")
        prediction_status, prediction_text = fetch(base_url, "/cases/blocked-unresolved-pallet/prediction.json")
        simulated_export_status, simulated_export = fetch(
            base_url, "/cases/blocked-unresolved-pallet/export.md?simulateResolved=true"
        )
        simulated_audit_status, simulated_audit = fetch(
            base_url, "/cases/blocked-unresolved-pallet/audit.md?simulateResolved=true"
        )
        missing_status, missing_page = fetch_any(base_url, "/cases/not-a-case")
        beta_status, beta_page = fetch(base_url, "/beta-readiness")
        validation_status, validation_page = fetch(base_url, "/validation-evidence")
        validation_json_status, validation_json = fetch(base_url, "/validation-evidence.json")
        system_status_code, system_status_json = fetch(base_url, "/system-status.json")
        health_status, health_json = fetch(base_url, "/health")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert dashboard_status == 200
    assert command_center_status == 200
    assert command_center_json_status == 200
    assert review_status == 200
    assert review_json_status == 200
    assert ai_review_status == 200
    assert ai_review_json_status == 200
    assert cases_status == 200
    assert sensor_lab_status == 200
    assert sensor_lab_json_status == 200
    assert data_contract_status == 200
    assert data_contract_json_status == 200
    assert sensor_adapters_status == 200
    assert sensor_adapters_json_status == 200
    assert all(status == 200 for status, _ in adapter_example_statuses)
    assert data_pipeline_status == 200
    assert data_pipeline_json_status == 200
    assert model_benchmark_status == 200
    assert model_benchmark_json_status == 200
    assert public_data_status == 200
    assert roadmap_status == 200
    assert baseline_case_status == 200
    assert baseline_case_review_status == 200
    assert simulated_status == 200
    assert baseline_trace_status == 200
    assert baseline_evidence_status == 200
    assert baseline_export_status == 200
    assert baseline_audit_status == 200
    assert baseline_sensor_summary_status == 200
    assert baseline_sensor_window_status == 200
    assert capped_sensor_window_status == 200
    assert cleaning_status == 200
    assert prediction_status == 200
    assert simulated_export_status == 200
    assert simulated_audit_status == 200
    assert missing_status == 404
    assert beta_status == 200
    assert validation_status == 200
    assert validation_json_status == 200
    assert system_status_code == 200
    assert health_status == 200
    assert "Synthetic demo data only." in dashboard
    assert "/command-center" in dashboard
    assert "Platform Command Center" in command_center
    assert "Sensor telemetry summary" in command_center
    assert "Data cleaning summary" in command_center
    assert "Redundancy and consensus summary" in command_center
    assert "SERS advisory risk summary" in command_center
    assert "Model benchmark summary" in command_center
    assert "Deterministic review packet summary" in command_center
    assert "Fireworks safety-gate summary" in command_center
    assert "Sensor Adapter status" in command_center
    assert "/sensor-adapters" in command_center
    assert "/data-contract" in command_center
    assert "No real data" in command_center
    assert "No autonomous operational actions" in command_center
    assert "Deterministic fallback remains authoritative" in command_center
    assert "Final demo flow" in command_center
    assert "/validation-evidence" in command_center
    assert "Final disposition blocked." in review
    assert "Fireworks call succeeded: no" in ai_review
    assert "Structured output verified: no" in ai_review
    assert "Displayed brief source: deterministic_fallback" in ai_review
    assert "AI-assisted explanation only." in ai_review
    assert "Synthetic Case Workspace" in cases_page
    assert "Judges do not need to inspect every reading." in sensor_lab
    assert "41472 synthetic readings represented" in sensor_lab
    assert "Readings per case: 13824" in sensor_lab
    assert "Optional synthetic scale profile" in sensor_lab
    assert "201,600 synthetic readings" in sensor_lab
    assert "large synthetic sensor stream" in sensor_lab
    assert "Sensor Lab" in sensor_lab
    assert "raw vendor payload -> adapter normalization -> schema validation" in data_pipeline
    assert "Data Contract v2" in data_contract
    assert "No field can authorize autonomous operational action" in data_contract
    assert "Sensor Adapters" in sensor_adapters
    assert "sentinel_native_v1" in sensor_adapters
    assert "vendor_flat_csv_v1" in sensor_adapters
    assert "vendor_nested_iot_v1" in sensor_adapters
    assert "On deterministic synthetic benchmark data only." in model_benchmark
    assert "No external datasets are ingested" in public_data_page
    assert "not ingested" in public_data_page
    assert "Platform Roadmap" in roadmap_page
    assert "FastAPI/Pydantic migration" in roadmap_page
    assert "Planned items are not production claims" in roadmap_page
    assert 'data-testid="global-nav"' in dashboard
    assert '<a href="/command-center">Command Center</a>' in dashboard
    assert 'data-testid="global-nav"' in cases_page
    assert 'data-testid="global-nav"' in baseline_case_review
    assert 'class="global-nav"' in baseline_case_review
    assert "@media (max-width: 640px)" in baseline_case_review
    for case_id in ("blocked-unresolved-pallet", "excursion-fully-mapped", "no-excursion-control"):
        assert case_id in cases_page
    assert cases_page.count("<td>false</td>") >= 3
    assert "Blocked excursion with unresolved pallet" in baseline_case
    assert "Reviewer checklist" in baseline_case_review
    assert "0/4 reviewed" in baseline_case_review
    assert "BLOCKED" in baseline_case_review
    assert "HUMAN_REVIEW_REQUIRED" in baseline_case_review
    assert "AUTONOMOUS_ACTIONS_DISABLED" in baseline_case_review
    assert "SYNTHETIC_ONLY" in baseline_case_review
    assert "localStorage" in baseline_case_review
    assert "Local demo notes only. Not uploaded, not persisted server-side." in baseline_case_review
    assert "Packet completeness" in baseline_case_review
    assert "DEMO_PACKET_INCOMPLETE" in baseline_case_review
    assert "Review session summary" in baseline_case_review
    assert "Clear local checklist and notes" in baseline_case_review
    assert "Simulate resolving missing mapping" in baseline_case_review
    assert "/ai-review?caseId=blocked-unresolved-pallet" in baseline_case_review
    assert "/ai-review.json?caseId=blocked-unresolved-pallet" in baseline_case_review
    assert "/cases/blocked-unresolved-pallet/audit.md" in baseline_case_review
    assert "/cases/blocked-unresolved-pallet/audit.md?simulateResolved=true" in baseline_case_review
    assert "2026-06-26 10:30 UTC" in baseline_case_review
    assert "2026-06-26 11:15 UTC" in baseline_case_review
    assert "Duration: 45 minutes" in baseline_case_review
    assert "Deterministic Rule Trace" in baseline_case_review
    assert "Rule trace is deterministic and does not depend on Fireworks." in baseline_case_review
    assert "Synthetic temperature timeline" in baseline_case_review
    assert "Threshold: 8.0 C" in baseline_case_review
    assert "Above threshold - review signal" in baseline_case_review
    assert "Large Sensor Data Summary" in baseline_case_review
    assert "Total readings represented: 13824" in baseline_case_review
    assert "Sensor window preview" in baseline_case_review
    assert "REVIEW_PACKET_COMPLETE" in simulated_review
    assert "MAPPING_REVIEW_SIMULATED" in simulated_review
    assert "PAL-SYN-1004 is synthetically mapped" in simulated_review
    assert "This is a synthetic review packet completion, not an operational decision." in simulated_review
    simulated_lower = simulated_review.lower()
    for forbidden in ("approved", "released", "safe for distribution", "compliant", "certified"):
        assert forbidden not in simulated_lower
    assert "Synthetic demo data only." in baseline_export
    assert "## Evidence Timeline" in baseline_export
    assert "## Safety Disclaimers" in baseline_export
    assert "## Reviewer Local Notes" in baseline_audit
    assert "Reviewer local notes: stored only in browser localStorage and not included in server export." in baseline_audit
    assert "## Synthetic Telemetry Summary" in baseline_audit
    assert "## Deterministic Rule Trace" in baseline_audit
    assert "Fireworks may provide an optional non-authoritative reviewer explanation only." in baseline_audit
    assert "No autonomous operational action." in baseline_audit
    assert "## Simulated Resolution" in simulated_export
    assert "After reviewStatus: REVIEW_PACKET_COMPLETE" in simulated_export
    assert "## Audit Simulation Details" in simulated_audit
    assert "## High-Volume Sensor Aggregation Summary" in baseline_audit
    assert "Generated readings represented: 13824" in baseline_audit
    assert "Case not found" in missing_page
    assert "not-a-case" in missing_page
    assert "blocked-unresolved-pallet" in missing_page
    assert "/cases" in missing_page

    packet = json.loads(review_json)
    assert packet == build_review_packet(case)
    assert packet["result"]["excursion"]["durationMinutes"] == 45
    assert packet["result"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]

    ai_packet = json.loads(ai_review_json)
    assert ai_packet["deterministicResult"] == packet["result"]
    assert ai_packet["assistant"]["provider"]["fireworksVerified"] is False
    assert ai_packet["assistant"]["provider"]["fireworksCallSucceeded"] is False
    assert ai_packet["assistant"]["provider"]["fireworksStructuredOutputVerified"] is False
    assert ai_packet["assistant"]["provider"]["displayedBriefSource"] == "deterministic_fallback"
    assert ai_packet["deterministicResult"]["finalDisposition"] == "BLOCKED"
    assert ai_packet["deterministicResult"]["reviewStatus"] == "HUMAN_REVIEW_REQUIRED"
    assert ai_packet["deterministicResult"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert ai_packet["deterministicResult"]["autonomousActionsAllowed"] is False

    health = json.loads(health_json)
    assert health == {"ok": True, "providers": "disabled"}

    evidence = json.loads(baseline_evidence)
    trace = json.loads(baseline_trace)
    sensor_summary_json = json.loads(baseline_sensor_summary)
    sensor_window_json = json.loads(baseline_sensor_window)
    capped_window_json = json.loads(capped_sensor_window)
    cleaning_json = json.loads(cleaning_text)
    prediction_json = json.loads(prediction_text)
    sensor_lab_payload = json.loads(sensor_lab_json)
    command_payload = json.loads(command_center_json)
    contract_payload = json.loads(data_contract_json)
    adapters_payload = json.loads(sensor_adapters_json)
    adapter_examples = [json.loads(body) for _, body in adapter_example_statuses]
    pipeline_payload = json.loads(data_pipeline_json)
    benchmark_payload = json.loads(model_benchmark_json)
    system_status = json.loads(system_status_json)
    validation_payload = json.loads(validation_json)
    assert evidence["caseId"] == "blocked-unresolved-pallet"
    assert evidence["result"]["finalDisposition"] == "BLOCKED"
    assert evidence["result"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert trace["result"]["excursion"]["durationMinutes"] == 45
    assert "TEMP_THRESHOLD_CHECK" in {row["ruleId"] for row in trace["trace"]}
    assert trace["sensorAggregationReference"]["generatedReadingCount"] == 13824
    assert sensor_summary_json["syntheticOnly"] is True
    assert sensor_summary_json["generatedReadingCount"] == 13824
    assert sensor_summary_json["excursionWindows"][0]["durationMinutes"] == 45
    assert sensor_summary_json["impactedZones"] == ["Z1"]
    assert sensor_summary_json["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert len(sensor_window_json["readings"]) <= 100
    assert capped_window_json["limit"] == 500
    assert all("qualityLabel" in row for row in sensor_window_json["readings"])
    assert cleaning_json["duplicateCount"] > 0
    assert cleaning_json["flagCounts"]["FLAGGED_DROPOUT"] > 0
    assert cleaning_json["flagCounts"]["FLAGGED_OUTLIER"] > 0
    assert prediction_json["advisoryOnly"] is True
    assert prediction_json["deterministicResultUnchanged"] == sensor_summary_json["deterministicResult"]
    assert 0 <= prediction_json["sers"]["riskScore"] <= 100
    assert prediction_json["sers"]["riskBand"] in ("LOW", "WATCH", "REVIEW", "CRITICAL")
    assert pipeline_payload["stages"] == [
        "raw vendor payload",
        "adapter normalization",
        "schema validation",
        "cleaning",
        "redundancy consensus",
        "SERS advisory risk score",
        "deterministic rule trace",
        "human-review packet",
    ]
    assert contract_payload["dataContractVersion"] == "v2"
    assert contract_payload["neverAuthorizesAutonomousAction"] is True
    assert "sourceFormat" in contract_payload["schema"]["fields"]
    assert adapters_payload["dataContractVersion"] == "v2"
    assert adapters_payload["supportedSyntheticAdapterFormats"] == SUPPORTED_FORMATS
    assert all(payload["dataContractVersion"] == "v2" for payload in adapter_examples)
    assert all(list(payload["formats"]) == [source_format] for payload, source_format in zip(adapter_examples, SUPPORTED_FORMATS))
    assert benchmark_payload["benchmarkScope"] == "On deterministic synthetic benchmark data only."
    assert "naiveCurrentTemperatureThreshold" in benchmark_payload["baselines"]
    assert "rollingAverageThreshold" in benchmark_payload["baselines"]
    assert "accuracy" in benchmark_payload["metrics"]
    assert "confusionMatrix" in benchmark_payload["metrics"]
    assert command_payload["appName"] == "ColdChain Sentinel"
    assert command_payload["betaTotalGeneratedReadings"] == 41472
    assert command_payload["fireworksSafetySummary"]["fireworksAuthoritative"] is False
    assert command_payload["deterministicReviewSummary"]["autonomousActionsAllowed"] is False
    assert command_payload["sersSummary"]["advisoryOnly"] is True
    assert command_payload["deterministicReviewSummary"]["finalDisposition"] == "BLOCKED"
    assert command_payload["deterministicReviewSummary"]["reviewStatus"] == "HUMAN_REVIEW_REQUIRED"
    assert command_payload["deterministicReviewSummary"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert sensor_lab_payload["syntheticOnly"] is True
    assert sensor_lab_payload["betaTotalGeneratedReadings"] == 41472
    assert sensor_lab_payload["readingsPerCase"] == 13824
    assert sensor_lab_payload["caseCount"] == 3
    assert sensor_lab_payload["sensorCount"] == 24
    assert sensor_lab_payload["zoneCount"] == 4
    assert sensor_lab_payload["timeRangeHours"] == 48
    assert sensor_lab_payload["readingIntervalMinutes"] == 5
    assert sensor_lab_payload["realDataUsed"] is False
    assert sensor_lab_payload["autonomousActionsAllowed"] is False
    assert sensor_lab_payload["fireworksAuthoritative"] is False
    assert "threshold breaches" in sensor_lab_payload["aggregationCapabilities"]
    assert "SENSOR_OUTLIER_REJECTED" in sensor_lab_payload["qualityLabels"]
    assert system_status["realDataUsed"] is False
    assert system_status["autonomousActionsAllowed"] is False
    assert system_status["fireworksAuthoritative"] is False
    assert system_status["sensorLabAvailable"] is True
    assert system_status["sensorAdaptersAvailable"] is True
    assert system_status["dataContractVersion"] == "v2"
    assert system_status["supportedSyntheticAdapterFormats"] == SUPPORTED_FORMATS
    assert system_status["reviewWorkspaceAvailable"] is True
    assert system_status["betaTotalGeneratedReadings"] == 41472
    assert validation_payload["realDataUsed"] is False
    assert validation_payload["autonomousActionsAllowed"] is False
    assert validation_payload["fireworksAuthoritative"] is False
    assert validation_payload["sersAdvisoryOnly"] is True
    assert validation_payload["deterministicRulesAuthoritative"] is True
    assert validation_payload["productionValidated"] is False
    assert "/command-center" in validation_payload["routeChecklist"]
    assert "/roadmap" in validation_payload["routeChecklist"]
    assert "synthetic_hackathon_beta" in beta_page
    assert "Sensor lab available" in beta_page
    assert "No real data" in beta_page
    assert "No autonomous actions" in beta_page
    assert "Validation Evidence" in validation_page
    assert "Docker route smoke" in validation_page
    assert "Deterministic rules authoritative" in validation_page
    assert "Fireworks safety gate" in validation_page
    assert "SERS advisory-only" in validation_page
    assert "No real data" in validation_page
    assert "No autonomous action" in validation_page
    assert "run manually after Render deploy" in validation_page


def test_golden_json_snapshots(case: dict[str, Any]) -> None:
    golden = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))
    baseline = get_case("blocked-unresolved-pallet")
    baseline_result = case_packet(baseline)["result"]

    command = command_center_payload()
    assert command["appName"] == golden["commandCenter"]["appName"]
    assert command["betaTotalGeneratedReadings"] == golden["commandCenter"]["betaTotalGeneratedReadings"]
    assert command["caseCount"] == golden["commandCenter"]["caseCount"]
    assert command["fireworksSafetySummary"]["fireworksAuthoritative"] == golden["commandCenter"]["fireworksAuthoritative"]
    assert command["sersSummary"]["advisoryOnly"] == golden["commandCenter"]["sersAdvisoryOnly"]
    assert command["deterministicReviewSummary"]["finalDisposition"] == golden["commandCenter"]["finalDisposition"]
    assert command["deterministicReviewSummary"]["reviewStatus"] == golden["commandCenter"]["reviewStatus"]

    status = system_status_json()
    assert status["appName"] == golden["systemStatus"]["appName"]
    assert status["betaTotalGeneratedReadings"] == golden["systemStatus"]["betaTotalGeneratedReadings"]
    assert status["realDataUsed"] == golden["systemStatus"]["realDataUsed"]
    assert status["autonomousActionsAllowed"] == golden["systemStatus"]["autonomousActionsAllowed"]
    assert status["fireworksAuthoritative"] == golden["systemStatus"]["fireworksAuthoritative"]
    assert status["productionValidated"] == golden["systemStatus"]["productionValidated"]

    sensor_lab = sensor_lab_payload()
    assert sensor_lab["betaTotalGeneratedReadings"] == golden["sensorLab"]["betaTotalGeneratedReadings"]
    assert sensor_lab["readingsPerCase"] == golden["sensorLab"]["readingsPerCase"]
    assert sensor_lab["sensorCount"] == golden["sensorLab"]["sensorCount"]
    assert sensor_lab["zoneCount"] == golden["sensorLab"]["zoneCount"]
    assert sensor_lab["realDataUsed"] == golden["sensorLab"]["realDataUsed"]
    assert sensor_lab["autonomousActionsAllowed"] == golden["sensorLab"]["autonomousActionsAllowed"]

    benchmark = model_benchmark_json()
    assert benchmark["benchmarkScope"] == golden["modelBenchmark"]["benchmarkScope"]
    assert benchmark["model"]["trainingRows"] == golden["modelBenchmark"]["trainingRows"]
    assert benchmark["model"]["testRows"] == golden["modelBenchmark"]["testRows"]
    assert sorted(benchmark["baselines"]) == sorted(golden["modelBenchmark"]["baselines"])

    cleaning = cleaning_report(baseline)
    assert cleaning["caseId"] == golden["baselineCleaningReport"]["caseId"]
    assert cleaning["rawReadingCount"] == golden["baselineCleaningReport"]["rawReadingCount"]
    assert cleaning["acceptedReadingCount"] == golden["baselineCleaningReport"]["acceptedReadingCount"]
    assert cleaning["rejectedReadingCount"] == golden["baselineCleaningReport"]["rejectedReadingCount"]
    assert cleaning["duplicateCount"] == golden["baselineCleaningReport"]["duplicateCount"]
    assert cleaning["missingExpectedReadings"] == golden["baselineCleaningReport"]["missingExpectedReadings"]
    for label, count in golden["baselineCleaningReport"]["flagCounts"].items():
        assert cleaning["flagCounts"][label] == count

    prediction = prediction_report(baseline, baseline_result, load_cases())
    assert prediction["caseId"] == golden["baselinePrediction"]["caseId"]
    assert prediction["advisoryOnly"] == golden["baselinePrediction"]["advisoryOnly"]
    assert prediction["sers"]["riskScore"] == golden["baselinePrediction"]["riskScore"]
    assert prediction["sers"]["riskBand"] == golden["baselinePrediction"]["riskBand"]
    assert prediction["deterministicResultUnchanged"]["reviewStatus"] == golden["baselinePrediction"]["deterministicReviewStatus"]

    validation = validation_evidence_json()
    for key, value in golden["validationEvidence"].items():
        assert validation[key] == value


def test_readme_route_map_is_covered(case: dict[str, Any]) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    routes_section = readme.split("## Routes", 1)[1].split("\n## ", 1)[0]
    routes = re.findall(r"^- `([^`]+)`", routes_section, flags=re.MULTILINE)
    assert routes

    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        for route in routes:
            status, _ = fetch(base_url, route)
            assert status == 200, route
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_case_routes_and_invariants(case: dict[str, Any]) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        for synthetic_case in load_cases():
            case_id = synthetic_case["caseId"]
            detail_status, _ = fetch(base_url, f"/cases/{case_id}")
            review_status, review_page = fetch(base_url, f"/cases/{case_id}/review")
            trace_status, trace_json = fetch(base_url, f"/cases/{case_id}/trace.json")
            evidence_status, evidence_json = fetch(base_url, f"/cases/{case_id}/evidence.json")
            export_status, export_md = fetch(base_url, f"/cases/{case_id}/export.md")
            audit_status, audit_md = fetch(base_url, f"/cases/{case_id}/audit.md")
            sensor_summary_status, sensor_summary_text = fetch(base_url, f"/cases/{case_id}/sensor-summary.json")
            sensor_window_status, sensor_window_text = fetch(base_url, f"/cases/{case_id}/sensor-window.json")
            cleaning_status, cleaning_text = fetch(base_url, f"/cases/{case_id}/cleaning-report.json")
            prediction_status, prediction_text = fetch(base_url, f"/cases/{case_id}/prediction.json")
            ai_status, ai_page = fetch(base_url, f"/ai-review?caseId={case_id}")
            ai_json_status, ai_json = fetch(base_url, f"/ai-review.json?caseId={case_id}")

            assert detail_status == 200
            assert review_status == 200
            assert trace_status == 200
            assert evidence_status == 200
            assert export_status == 200
            assert audit_status == 200
            assert sensor_summary_status == 200
            assert sensor_window_status == 200
            assert cleaning_status == 200
            assert prediction_status == 200
            assert ai_status == 200
            assert ai_json_status == 200
            assert "Reviewer checklist" in review_page
            assert "Local demo notes only. Not uploaded, not persisted server-side." in review_page
            assert "Packet completeness" in review_page
            assert "Review session summary" in review_page
            assert "No autonomous operational action." in review_page
            assert "Deterministic Rule Trace" in review_page
            assert "Rule trace is deterministic and does not depend on Fireworks." in review_page
            assert "Synthetic temperature timeline" in review_page
            assert "Large Sensor Data Summary" in review_page
            assert "Threshold:" in review_page
            assert "AUTONOMOUS_ACTIONS_DISABLED" in review_page
            assert "SYNTHETIC_ONLY" in review_page
            assert "/evidence.json" in review_page
            assert "/trace.json" in review_page
            assert "/export.md" in review_page
            assert "/audit.md" in review_page
            assert f"Selected case: {case_id}" in ai_page
            assert "Fireworks may provide an optional non-authoritative reviewer explanation only." in export_md
            assert "quality-gated" in export_md
            assert "No autonomous operational action." in export_md
            assert "## Deterministic Rule Trace" in export_md
            assert "## Synthetic Telemetry Summary" in export_md
            assert "## Deterministic Rule Trace" in audit_md
            assert "## Synthetic Telemetry Summary" in audit_md
            assert "## Reviewer Local Notes" in audit_md
            assert "## High-Volume Sensor Aggregation Summary" in audit_md
            assert "Fireworks output is optional, quality-gated, and non-authoritative." in audit_md
            for page_text in (review_page, export_md, audit_md):
                lowered = page_text.lower()
                for forbidden in ("approved", "released", "safe for distribution", "compliant", "certified"):
                    assert forbidden not in lowered, (case_id, forbidden)

            trace = json.loads(trace_json)
            rule_ids = {row["ruleId"] for row in trace["trace"]}
            assert "TEMP_THRESHOLD_CHECK" in rule_ids
            assert "PALLET_MAPPING_CHECK" in rule_ids
            assert "HUMAN_REVIEW_GATE" in rule_ids
            assert "AUTONOMOUS_ACTION_DENY" in rule_ids
            assert trace["result"]["autonomousActionsAllowed"] is False
            assert trace["safetyDisclaimers"]
            evidence = json.loads(evidence_json)
            sensor_case_summary = json.loads(sensor_summary_text)
            sensor_case_window = json.loads(sensor_window_text)
            prediction_case = json.loads(prediction_text)
            cleaning_case = json.loads(cleaning_text)
            assert evidence["result"]["autonomousActionsAllowed"] is False
            assert evidence["telemetryTimeline"]
            assert evidence["trace"]
            assert sensor_case_summary["deterministicResult"]["autonomousActionsAllowed"] is False
            assert sensor_case_summary["generatedReadingCount"] == 13824
            assert len(sensor_case_window["readings"]) <= 100
            assert all(row["qualityLabel"].startswith("SENSOR_") for row in sensor_case_window["readings"])
            assert cleaning_case["duplicateCount"] >= 1
            assert prediction_case["advisoryOnly"] is True
            assert prediction_case["deterministicResultUnchanged"] == case_packet(get_case(case_id))["result"]
            ai_packet = json.loads(ai_json)
            assert ai_packet["deterministicResult"]["autonomousActionsAllowed"] is False
            assert ai_packet["deterministicResult"] == case_packet(get_case(case_id))["result"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    baseline = case_packet(get_case("blocked-unresolved-pallet"))["result"]
    baseline_packet = case_packet(get_case("blocked-unresolved-pallet"))
    assert baseline["finalDisposition"] == "BLOCKED"
    assert baseline["reviewStatus"] == "HUMAN_REVIEW_REQUIRED"
    assert baseline["excursion"]["durationMinutes"] == 45
    assert baseline["excursion"]["startUtc"] == "2026-06-26T10:30:00Z"
    assert baseline["excursion"]["endUtc"] == "2026-06-26T11:15:00Z"
    assert baseline["excursion"]["zoneId"] == "Z1"
    assert baseline["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert "TEMP_THRESHOLD_CHECK" in {row["ruleId"] for row in baseline_packet["ruleTrace"]}

    fully_mapped = case_packet(get_case("excursion-fully-mapped"))["result"]
    fully_mapped_sensor = sensor_summary(get_case("excursion-fully-mapped"), fully_mapped)
    assert fully_mapped["excursion"] is not None
    assert fully_mapped["unresolvedPalletIds"] == []
    assert fully_mapped["autonomousActionsAllowed"] is False
    assert fully_mapped_sensor["excursionWindows"]
    assert fully_mapped_sensor["unresolvedPalletIds"] == []

    control = case_packet(get_case("no-excursion-control"))["result"]
    control_sensor = sensor_summary(get_case("no-excursion-control"), control)
    assert control["excursion"] is None
    assert control["autonomousActionsAllowed"] is False
    assert "RELEASE" not in control["finalDisposition"]
    assert "APPROVAL" not in control["finalDisposition"]
    assert control_sensor["excursionWindows"] == []

    simulated = case_packet(get_case("blocked-unresolved-pallet"), simulate_resolved=True)["result"]
    assert simulated["unresolvedPalletIds"] == []
    assert simulated["reviewStatus"] == "REVIEW_PACKET_COMPLETE"
    assert simulated["finalDisposition"] == "MAPPING_REVIEW_SIMULATED"
    assert simulated["autonomousActionsAllowed"] is False


def test_sensor_generator_deterministic() -> None:
    case = get_case("blocked-unresolved-pallet")
    first = synthetic_readings(case)[:20]
    second = synthetic_readings(case)[:20]
    summary = sensor_summary(case, case_packet(case)["result"])
    clean = cleaning_report(case)
    consensus = consensus_report(case)
    risk = sers_risk(case, case_packet(case)["result"])
    assert first == second
    assert {"humidityPercent", "batteryPercent", "signalStrength", "doorOpen", "readingSequence", "ingestionDelaySeconds"} <= set(first[0])
    assert summary["generatedReadingCount"] == 13824
    assert summary["excursionWindows"][0]["durationMinutes"] == 45
    assert summary["impactedZones"] == ["Z1"]
    assert summary["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert clean["duplicateCount"] > 0
    assert clean["flagCounts"]["FLAGGED_DROPOUT"] > 0
    assert clean["flagCounts"]["FLAGGED_OUTLIER"] > 0
    assert consensus["zones"]
    assert all("zoneConsensusScore" in zone for zone in consensus["zones"])
    assert 0 <= risk["riskScore"] <= 100
    assert risk["riskBand"] in ("LOW", "WATCH", "REVIEW", "CRITICAL")
    assert sensor_window(case, 0, 900)["limit"] == 500


class FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode("utf-8")


def fireworks_body(content: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": content}}]}


def with_fake_fireworks(content: str) -> tuple[list[dict[str, Any]], Any]:
    calls: list[dict[str, Any]] = []
    original = urllib.request.urlopen

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> FakeResponse:
        assert timeout == ai_review_assistant.TIMEOUT_SECONDS
        calls.append(json.loads(request.data.decode("utf-8")))  # type: ignore[union-attr]
        return FakeResponse(fireworks_body(content))

    urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]
    return calls, original


def with_fireworks_http_error() -> tuple[list[dict[str, Any]], Any]:
    calls: list[dict[str, Any]] = []
    original = urllib.request.urlopen

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> FakeResponse:
        calls.append(json.loads(request.data.decode("utf-8")))  # type: ignore[union-attr]
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, None)

    urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]
    return calls, original


def restore_fireworks(original_urlopen: Any, old_key: str | None) -> None:
    urllib.request.urlopen = original_urlopen  # type: ignore[assignment]
    if old_key is None:
        os.environ.pop("FIREWORKS_API_KEY", None)
    else:
        os.environ["FIREWORKS_API_KEY"] = old_key


def test_fireworks_missing_key_fallback(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    old_key = os.environ.pop("FIREWORKS_API_KEY", None)
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        if old_key is not None:
            os.environ["FIREWORKS_API_KEY"] = old_key

    assert review["assistant"]["provider"]["fireworksVerified"] is False
    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is False
    assert review["assistant"]["provider"]["fireworksStructuredOutputVerified"] is False
    assert review["assistant"]["provider"]["displayedBriefSource"] == "deterministic_fallback"
    assert review["assistant"]["provider"]["status"] == "Fireworks not configured"
    assert review["deterministicResult"]["finalDisposition"] == "BLOCKED"


def test_fireworks_http_error_fallback(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    calls, original = with_fireworks_http_error()
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert len(calls) == 4
    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is False
    assert review["assistant"]["provider"]["fireworksStructuredOutputVerified"] is False
    assert review["assistant"]["provider"]["displayedBriefSource"] == "deterministic_fallback"
    assert review["deterministicResult"]["finalDisposition"] == "BLOCKED"


def test_fireworks_unstructured_text_sanitized(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    text = """
    The shipment remains blocked because a temperature excursion was detected and PAL-SYN-1004 has missing zone mapping.
    Missing evidence: PAL-SYN-1004 zone mapping is not supplied.
    Reviewer should confirm the synthetic excursion window and resolve the missing mapping.
    Root cause hypothesis: mapping feed omitted one pallet.
    Deterministic rules remain authoritative.
    """
    calls, original = with_fake_fireworks(text)
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert calls[0]["response_format"]["type"] == "json_schema"
    assert calls[0]["reasoning_effort"] == "none"
    assert review["assistant"]["provider"]["fireworksVerified"] is False
    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is True
    assert review["assistant"]["provider"]["fireworksStructuredOutputVerified"] is False
    assert review["assistant"]["provider"]["displayedBriefSource"] == "sanitized_fireworks_text"
    assert "PAL-SYN-1004" in " ".join(review["assistant"]["brief"]["missingEvidence"])
    assert review["assistant"]["unstructuredAiResponse"] == ""
    assert review["deterministicResult"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]


def test_fireworks_embedded_json_object_sanitized(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    embedded = {
        "summary": "Shipment remains blocked pending human review.",
        "whyBlocked": ["Temperature excursion detected.", "PAL-SYN-1004 has missing zone mapping."],
        "missingEvidence": ["Missing zone mapping for PAL-SYN-1004."],
        "reviewerChecklist": ["Resolve missing zone mapping for PAL-SYN-1004."],
        "rootCauseHypotheses": ["Mapping feed omitted one pallet."],
        "safetyNote": "AI-assisted explanation only. Deterministic rules remain authoritative.",
        "finalDisposition": "RELEASED",
    }
    _, original = with_fake_fireworks("Here is the JSON:\n" + json.dumps(embedded))
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert review["assistant"]["provider"]["displayedBriefSource"] == "sanitized_fireworks_text"
    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is True
    assert review["assistant"]["provider"]["fireworksStructuredOutputVerified"] is False
    assert review["assistant"]["brief"]["summary"] == "Shipment remains blocked pending human review."
    assert "finalDisposition" not in review["assistant"]["brief"]
    assert review["deterministicResult"]["finalDisposition"] == "BLOCKED"


def test_fireworks_malformed_json_fragment_rejected(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    text = '''
    "summary":"Shipment SYN-SHIP-2026-06-26-A is blocked pending human review.",
    "whyBlocked":["Temperature excursion detected.", "PAL-SYN-1004 has missing zone mapping."],
    "missingEvidence":["PAL-SYN-1004 zone mapping"],
    "reviewerChecklist":["Resolve missing mapping"],
    '''
    _, original = with_fake_fireworks(text)
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is True
    assert review["assistant"]["provider"]["displayedBriefSource"] == "deterministic_fallback"
    assert review["assistant"]["provider"]["status"] == ai_review_assistant.QUALITY_REJECT_STATUS
    assert review["assistant"]["brief"] == ai_review_assistant.deterministic_brief(packet)


def test_fireworks_repeated_low_quality_text_rejected(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    repeated = (
        "Shipment remains blocked because PAL-SYN-1004 has missing mapping and reviewer should resolve missing mapping."
    )
    text = "\n".join([repeated, repeated, repeated])
    _, original = with_fake_fireworks(text)
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is True
    assert review["assistant"]["provider"]["displayedBriefSource"] == "deterministic_fallback"
    assert review["assistant"]["provider"]["fireworksStructuredOutputVerified"] is False
    assert review["assistant"]["provider"]["status"] == ai_review_assistant.QUALITY_REJECT_STATUS
    assert review["deterministicResult"]["reviewStatus"] == "HUMAN_REVIEW_REQUIRED"


def test_fireworks_unsafe_text_rejected(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    text = "The shipment can clear for use and is safe for distribution after review."
    _, original = with_fake_fireworks(text)
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is True
    assert review["assistant"]["provider"]["displayedBriefSource"] == "deterministic_fallback"
    assert review["assistant"]["provider"]["status"] == (
        "Fireworks call succeeded; output rejected by safety filter; deterministic fallback shown."
    )
    assert review["deterministicResult"]["autonomousActionsAllowed"] is False


def test_fireworks_missing_required_json_key_fallback(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    incomplete_brief = {
        "summary": "Reviewer brief only.",
        "whyBlocked": ["Missing mapping remains unresolved."],
        "missingEvidence": ["PAL-SYN-1004 zone mapping."],
        "reviewerChecklist": ["Resolve missing mapping."],
        "safetyNote": "Deterministic rules remain authoritative.",
    }
    _, original = with_fake_fireworks(json.dumps(incomplete_brief))
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert review["assistant"]["provider"]["fireworksVerified"] is False
    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is True
    assert review["assistant"]["provider"]["fireworksStructuredOutputVerified"] is False
    assert review["assistant"]["provider"]["displayedBriefSource"] == "deterministic_fallback"
    assert review["deterministicResult"]["finalDisposition"] == "BLOCKED"


def test_fireworks_structured_json_accepted_and_non_authoritative(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    provider_brief = {
        "summary": "Reviewer brief only.",
        "whyBlocked": ["Missing mapping remains unresolved."],
        "missingEvidence": ["PAL-SYN-1004 zone mapping."],
        "reviewerChecklist": ["Resolve missing mapping."],
        "rootCauseHypotheses": ["Mapping feed omitted one pallet."],
        "safetyNote": "Deterministic rules remain authoritative.",
        "finalDisposition": "RELEASED",
        "reviewStatus": "COMPLETE",
        "unresolvedPalletIds": [],
        "autonomousActionsAllowed": True,
    }
    calls, original = with_fake_fireworks(json.dumps(provider_brief))
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert calls[0]["response_format"]["type"] == "json_schema"
    assert review["assistant"]["provider"]["fireworksVerified"] is True
    assert review["assistant"]["provider"]["fireworksCallSucceeded"] is True
    assert review["assistant"]["provider"]["fireworksStructuredOutputVerified"] is True
    assert review["assistant"]["provider"]["displayedBriefSource"] == "fireworks_structured_json"
    assert review["assistant"]["provider"]["structuredOutputMode"] == "json_schema"
    assert review["assistant"]["provider"]["reasoningEffortNoneAccepted"] is True
    assert "finalDisposition" not in review["assistant"]["brief"]
    assert review["deterministicResult"]["finalDisposition"] == "BLOCKED"
    assert review["deterministicResult"]["reviewStatus"] == "HUMAN_REVIEW_REQUIRED"
    assert review["deterministicResult"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert review["deterministicResult"]["autonomousActionsAllowed"] is False


def main() -> None:
    old_key = os.environ.pop("FIREWORKS_API_KEY", None)
    try:
        case = load_fixture()
        test_deterministic_baseline(case)
        test_review_packet(case)
        test_rendered_pages(case)
        test_sensor_generator_deterministic()
        test_routes(case)
        test_case_routes_and_invariants(case)
        test_fireworks_missing_key_fallback(case)
        test_fireworks_http_error_fallback(case)
        test_fireworks_unstructured_text_sanitized(case)
        test_fireworks_embedded_json_object_sanitized(case)
        test_fireworks_malformed_json_fragment_rejected(case)
        test_fireworks_repeated_low_quality_text_rejected(case)
        test_fireworks_unsafe_text_rejected(case)
        test_fireworks_missing_required_json_key_fallback(case)
        test_fireworks_structured_json_accepted_and_non_authoritative(case)
        print("coldchain validation suite passed")
    finally:
        if old_key is not None:
            os.environ["FIREWORKS_API_KEY"] = old_key


if __name__ == "__main__":
    main()
