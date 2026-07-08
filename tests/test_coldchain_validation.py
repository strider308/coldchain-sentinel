"""Stdlib validation suite for the ColdChain Sentinel deterministic demo."""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import ai_review_assistant  # noqa: E402
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
    assert health_status == 200
    assert "Synthetic demo data only." in dashboard
    assert "Final disposition blocked." in review
    assert "Fireworks verified: no" in ai_review
    assert "AI-assisted explanation only." in ai_review

    packet = json.loads(review_json)
    assert packet == build_review_packet(case)
    assert packet["result"]["excursion"]["durationMinutes"] == 45
    assert packet["result"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]

    ai_packet = json.loads(ai_review_json)
    assert ai_packet["deterministicResult"] == packet["result"]
    assert ai_packet["assistant"]["provider"]["fireworksVerified"] is False
    assert ai_packet["deterministicResult"]["finalDisposition"] == "BLOCKED"
    assert ai_packet["deterministicResult"]["reviewStatus"] == "HUMAN_REVIEW_REQUIRED"
    assert ai_packet["deterministicResult"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]
    assert ai_packet["deterministicResult"]["autonomousActionsAllowed"] is False

    health = json.loads(health_json)
    assert health == {"ok": True, "providers": "disabled"}


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
    assert review["assistant"]["provider"]["status"] == "Fireworks not configured"
    assert review["deterministicResult"]["finalDisposition"] == "BLOCKED"


def test_fireworks_unstructured_fallback(case: dict[str, Any]) -> None:
    packet = build_review_packet(case)
    calls, original = with_fake_fireworks("not json")
    old_key = os.environ.get("FIREWORKS_API_KEY")
    os.environ["FIREWORKS_API_KEY"] = "test-key"
    try:
        review = ai_review_assistant.build_ai_review(packet)
    finally:
        restore_fireworks(original, old_key)

    assert calls[0]["response_format"]["type"] == "json_schema"
    assert calls[0]["reasoning_effort"] == "none"
    assert review["assistant"]["provider"]["fireworksVerified"] is False
    assert "structured verification pending" in review["assistant"]["provider"]["status"]
    assert review["deterministicResult"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]


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
    assert "structured verification pending" in review["assistant"]["provider"]["status"]
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
        test_fireworks_missing_key_fallback(case)
        test_fireworks_unstructured_fallback(case)
        test_fireworks_missing_required_json_key_fallback(case)
        test_fireworks_structured_json_accepted_and_non_authoritative(case)
        print("coldchain validation suite passed")
    finally:
        if old_key is not None:
            os.environ["FIREWORKS_API_KEY"] = old_key


if __name__ == "__main__":
    main()
