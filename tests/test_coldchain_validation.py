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


def main() -> None:
    old_key = os.environ.pop("FIREWORKS_API_KEY", None)
    try:
        case = load_fixture()
        test_deterministic_baseline(case)
        test_review_packet(case)
        test_rendered_pages(case)
        test_routes(case)
        print("coldchain validation suite passed")
    finally:
        if old_key is not None:
            os.environ["FIREWORKS_API_KEY"] = old_key


if __name__ == "__main__":
    main()
