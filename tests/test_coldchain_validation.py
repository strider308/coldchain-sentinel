"""Stdlib validation suite for the ColdChain Sentinel deterministic demo."""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import ai_review_assistant  # noqa: E402
from case_engine import case_packet, get_case, load_cases  # noqa: E402
from coldchain_baseline import build_review_packet, evaluate_case, load_fixture  # noqa: E402
from serve_dashboard import DashboardHandler, render_ai_review, render_dashboard, render_review_packet  # noqa: E402


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
        review_status, review = fetch(base_url, "/review")
        review_json_status, review_json = fetch(base_url, "/review.json")
        ai_review_status, ai_review = fetch(base_url, "/ai-review")
        ai_review_json_status, ai_review_json = fetch(base_url, "/ai-review.json")
        cases_status, cases_page = fetch(base_url, "/cases")
        baseline_case_status, baseline_case = fetch(base_url, "/cases/blocked-unresolved-pallet")
        baseline_case_review_status, baseline_case_review = fetch(base_url, "/cases/blocked-unresolved-pallet/review")
        simulated_status, simulated_review = fetch(
            base_url, "/cases/blocked-unresolved-pallet/review?simulateResolved=true"
        )
        baseline_trace_status, baseline_trace = fetch(base_url, "/cases/blocked-unresolved-pallet/trace.json")
        baseline_evidence_status, baseline_evidence = fetch(base_url, "/cases/blocked-unresolved-pallet/evidence.json")
        baseline_export_status, baseline_export = fetch(base_url, "/cases/blocked-unresolved-pallet/export.md")
        baseline_audit_status, baseline_audit = fetch(base_url, "/cases/blocked-unresolved-pallet/audit.md")
        simulated_export_status, simulated_export = fetch(
            base_url, "/cases/blocked-unresolved-pallet/export.md?simulateResolved=true"
        )
        simulated_audit_status, simulated_audit = fetch(
            base_url, "/cases/blocked-unresolved-pallet/audit.md?simulateResolved=true"
        )
        missing_status, missing_page = fetch_any(base_url, "/cases/not-a-case")
        health_status, health_json = fetch(base_url, "/health")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert dashboard_status == 200
    assert review_status == 200
    assert review_json_status == 200
    assert ai_review_status == 200
    assert ai_review_json_status == 200
    assert cases_status == 200
    assert baseline_case_status == 200
    assert baseline_case_review_status == 200
    assert simulated_status == 200
    assert baseline_trace_status == 200
    assert baseline_evidence_status == 200
    assert baseline_export_status == 200
    assert baseline_audit_status == 200
    assert simulated_export_status == 200
    assert simulated_audit_status == 200
    assert missing_status == 404
    assert health_status == 200
    assert "Synthetic demo data only." in dashboard
    assert "Final disposition blocked." in review
    assert "Fireworks call succeeded: no" in ai_review
    assert "Structured output verified: no" in ai_review
    assert "Displayed brief source: deterministic_fallback" in ai_review
    assert "AI-assisted explanation only." in ai_review
    assert "Synthetic Case Workspace" in cases_page
    assert 'data-testid="global-nav"' in dashboard
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
    assert evidence["caseId"] == "blocked-unresolved-pallet"
    assert evidence["result"]["finalDisposition"] == "BLOCKED"
    assert evidence["result"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert trace["result"]["excursion"]["durationMinutes"] == 45
    assert "TEMP_THRESHOLD_CHECK" in {row["ruleId"] for row in trace["trace"]}


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
            ai_status, ai_page = fetch(base_url, f"/ai-review?caseId={case_id}")
            ai_json_status, ai_json = fetch(base_url, f"/ai-review.json?caseId={case_id}")

            assert detail_status == 200
            assert review_status == 200
            assert trace_status == 200
            assert evidence_status == 200
            assert export_status == 200
            assert audit_status == 200
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
            assert evidence["result"]["autonomousActionsAllowed"] is False
            assert evidence["telemetryTimeline"]
            assert evidence["trace"]
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
    assert fully_mapped["excursion"] is not None
    assert fully_mapped["unresolvedPalletIds"] == []
    assert fully_mapped["autonomousActionsAllowed"] is False

    control = case_packet(get_case("no-excursion-control"))["result"]
    assert control["excursion"] is None
    assert control["autonomousActionsAllowed"] is False
    assert "RELEASE" not in control["finalDisposition"]
    assert "APPROVAL" not in control["finalDisposition"]

    simulated = case_packet(get_case("blocked-unresolved-pallet"), simulate_resolved=True)["result"]
    assert simulated["unresolvedPalletIds"] == []
    assert simulated["reviewStatus"] == "REVIEW_PACKET_COMPLETE"
    assert simulated["finalDisposition"] == "MAPPING_REVIEW_SIMULATED"
    assert simulated["autonomousActionsAllowed"] is False


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
