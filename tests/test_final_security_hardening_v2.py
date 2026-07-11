from __future__ import annotations

from contextlib import contextmanager
import http.client
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
import urllib.error
from urllib.request import HTTPRedirectHandler
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_review_assistant import (  # noqa: E402
    brief_is_unsafe,
    build_ai_review,
    build_runtime_ai_review,
    call_fireworks,
    validate_brief,
)
from coldchain_baseline import build_review_packet, load_fixture  # noqa: E402
from fireworks_advisory_v2 import (  # noqa: E402
    ALLOWED_MODELS,
    DEFAULT_MODEL,
    _call_fireworks as call_advisory_fireworks,
    _case_context,
    _extract_message_content,
    _fallback_payload,
    _validate_advisory,
)
from fireworks_runtime_guard import MAX_PROVIDER_RESPONSE_BYTES, read_bounded_json  # noqa: E402
from serve_dashboard import self_check as base_self_check  # noqa: E402
from serve_dashboard_amd import AmdDashboardHandler  # noqa: E402
from serve_dashboard_amd import self_check as amd_self_check  # noqa: E402


@contextmanager
def running_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), AmdDashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(address, path: str, method: str = "GET", headers: dict[str, str] | None = None):
    connection = http.client.HTTPConnection(*address, timeout=20)
    connection.request(method, path, headers=headers or {})
    response = connection.getresponse()
    body = response.read()
    result = response.status, dict(response.getheaders()), body
    connection.close()
    return result


def test_protocol_headers_404s_and_strict_dynamic_routes() -> None:
    with running_server() as address:
        status, headers, body = request(address, "/command-center")
        assert status == 200 and body
        assert headers["Server"] == "ColdChainSentinel"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert "default-src 'self'" in headers["Content-Security-Policy"]
        assert "Access-Control-Allow-Origin" not in headers
        assert "Strict-Transport-Security" not in headers

        status, headers, body = request(address, "/command-center", "HEAD")
        assert status == 200 and body == b""
        assert headers["Content-Type"].startswith("text/html")

        for method in ("POST", "PUT", "PATCH", "DELETE", "TRACE", "CONNECT", "OPTIONS"):
            status, headers, _ = request(address, "/command-center", method)
            assert status == 405
            assert headers["Allow"] == "GET, HEAD"
            assert "Access-Control-Allow-Origin" not in headers

        status, headers, _ = request(address, "/command-center", headers={"X-Forwarded-Proto": "https"})
        assert status == 200 and headers["Strict-Transport-Security"].startswith("max-age=")

        status, headers, body = request(address, "/unknown")
        assert status == 404 and headers["Content-Type"].startswith("text/html")
        assert b'href="/command-center"' in body and b"Traceback" not in body

        status, headers, body = request(address, "/unknown.json")
        assert status == 404 and headers["Content-Type"].startswith("application/json")
        assert json.loads(body) == {"error": "not found"}

        expected_404 = (
            "//command-center",
            "/%2e%2e/",
            "/..%2f",
            "/%3Cscript%3Ealert(1)%3C/script%3E",
            "/a%0d%0aInjected-Header:test",
            "/.env",
            "/.git/config",
            "/Dockerfile",
            "/src/serve_dashboard_amd.py",
            "/cases/blocked-unresolved-pallet/review/extra",
            "/reviewer-workspace/extra/door-open-warming.json",
            "/scenario-lab/extra/door-open-warming.json",
            "/scenario-library-v4/extra/door-open-warming.json",
            "/decision-simulator/extra/door-open-warming.json",
            "/review-workbench/extra/no-excursion-control.json",
            "/incident-replay/extra/no-excursion-control.json",
            "/cases/no-excursion-control/extra/fireworks-advisory.json",
            "/cases/door-open-warming/extra/audit-ledger.json",
            "/cases//blocked-unresolved-pallet",
            "/cases/blocked-unresolved-pallet/review/",
            "/scenario-lab//door-open-warming.json",
            "/cases//door-open-warming/fireworks-advisory.json",
            "/case-walkthroughs//door-open-warming",
        )
        for path in expected_404:
            assert request(address, path)[0] == 404, path

        assert request(address, "/" + "a" * 9000)[0] == 414
        assert request(address, "/" + "a" * 70_000)[0] == 414

        for path in (
            "/cases/unknown-case/risk-timeline.json",
            "/cases/unknown-case/consensus-report.json",
            "/cases/unknown-case/quality-events.json",
            "/cases/unknown-case/raw-sensor-window.json",
        ):
            status, headers, body = request(address, path)
            assert status == 404 and headers["Content-Type"].startswith("application/json"), path
            assert json.loads(body)["error"] == "unknown synthetic case"

        for query in ("offset=-1", "limit=0"):
            status, headers, body = request(
                address,
                f"/cases/blocked-unresolved-pallet/sensor-window.json?{query}",
            )
            assert status == 400 and headers["Content-Type"].startswith("application/json")
            assert "error" in json.loads(body)

        for resource, query in (
            ("raw-sensor-window.json", "offset=oops"),
            ("normalized-sensor-window.json", "offset=-1"),
            ("rejected-readings.json", "limit=0"),
            ("rejected-readings.json", "limit=bad"),
        ):
            status, headers, body = request(
                address,
                f"/cases/blocked-unresolved-pallet/{resource}?{query}",
            )
            assert status == 400 and headers["Content-Type"].startswith("application/json")
            assert "error" in json.loads(body)


def test_json_is_finite_and_fireworks_is_default_off_at_runtime() -> None:
    def reject_constant(value: str):
        raise ValueError(value)

    with patch.dict(os.environ, {"FIREWORKS_API_KEY": "test-only", "FIREWORKS_MODEL": "unapproved/model"}, clear=True):
        with patch("urllib.request.urlopen", side_effect=AssertionError("provider call must remain disabled")):
            with running_server() as address:
                for path in ("/command-center.json", "/ai-review.json", "/cases/door-open-warming/fireworks-advisory.json"):
                    status, headers, body = request(address, path)
                    assert status == 200 and headers["Content-Type"].startswith("application/json")
                    payload = json.loads(body, parse_constant=reject_constant)
                    assert payload
                assert b"disabled by default" in request(address, "/ai-review.json")[2]
                assert request(address, "/ai-review.json", "HEAD")[2] == b""

        fallback = _fallback_payload(_case_context("door-open-warming"), "test")
        assert fallback["provider"]["fireworksModel"] == DEFAULT_MODEL
        assert DEFAULT_MODEL in ALLOWED_MODELS


def test_runtime_provider_retry_and_response_bounds() -> None:
    packet = build_review_packet(load_fixture())
    calls = []

    def fail(_key, _payload):
        calls.append(1)
        raise urllib.error.HTTPError("https://example.invalid", 400, "bad request", {}, None)

    with patch.dict(os.environ, {"FIREWORKS_API_KEY": "test-only", "FIREWORKS_LIVE_ENABLED": "true"}, clear=True):
        with patch("ai_review_assistant.call_fireworks", side_effect=fail):
            result = build_runtime_ai_review(packet)
    assert len(calls) == 2
    assert result["assistant"]["provider"]["displayedBriefSource"] == "deterministic_fallback"
    assert result["deterministicResult"]["autonomousActionsAllowed"] is False

    class OversizedResponse:
        def read(self, size=-1):
            return b"x" * (MAX_PROVIDER_RESPONSE_BYTES + 1)

    try:
        read_bounded_json(OversizedResponse())
    except ValueError as exc:
        assert "size limit" in str(exc)
    else:
        raise AssertionError("oversized provider response was accepted")


def test_structured_provider_output_cannot_bypass_safety_language_filter() -> None:
    packet = build_review_packet(load_fixture())
    unsafe_brief = {
        "summary": "Approve shipment and release shipment now.",
        "whyBlocked": ["Human review is pending."],
        "missingEvidence": ["Zone mapping is missing."],
        "reviewerChecklist": ["Inspect the synthetic evidence."],
        "rootCauseHypotheses": ["A mapping omission may explain the block."],
        "safetyNote": "Deterministic rules remain authoritative.",
    }
    response = {"choices": [{"message": {"content": json.dumps(unsafe_brief)}}]}

    with patch.dict(os.environ, {"FIREWORKS_API_KEY": "test-only"}, clear=True):
        with patch("ai_review_assistant.request_structured_fireworks", return_value=(response, "json_schema", True)):
            result = build_ai_review(packet, provider_attempts=1)

    provider = result["assistant"]["provider"]
    assert provider["displayedBriefSource"] == "deterministic_fallback"
    assert provider["fireworksStructuredOutputVerified"] is False
    assert "safety filter" in provider["status"]
    assert result["deterministicResult"]["autonomousActionsAllowed"] is False


def test_provider_schema_types_and_all_prohibited_language_are_enforced() -> None:
    valid_brief = {
        "summary": "Shipment remains blocked pending review.",
        "whyBlocked": ["Human review is pending."],
        "missingEvidence": ["Zone mapping is missing."],
        "reviewerChecklist": ["Inspect the synthetic evidence."],
        "rootCauseHypotheses": ["A mapping omission may explain the block."],
        "safetyNote": "Deterministic rules remain authoritative.",
    }
    assert validate_brief(valid_brief) is not None
    assert validate_brief(valid_brief | {"summary": {"nested": "object"}}) is None
    assert validate_brief(valid_brief | {"whyBlocked": [True]}) is None
    assert "extra" not in validate_brief(valid_brief | {"extra": "field"})

    valid_advisory = {
        "summary": "Synthetic advisory remains review-only.",
        "riskDrivers": ["Synthetic temperature trend."],
        "evidenceToInspect": ["Inspect the synthetic timeline."],
        "confidenceLimits": ["Synthetic evidence only."],
        "humanReviewPrompt": "Review the evidence.",
        "safetyNote": "Deterministic rules remain authoritative.",
    }
    assert _validate_advisory(valid_advisory) is not None
    assert _validate_advisory(valid_advisory | {"summary": {"nested": "object"}}) is None
    assert _validate_advisory(valid_advisory | {"riskDrivers": [1]}) is None
    assert "extra" not in _validate_advisory(valid_advisory | {"extra": "field"})

    for phrase in (
        "autonomous " + "release",
        "autonomous " + "quarantine",
        "autonomous " + "discard",
        "autonomous " + "reroute",
        "customer " + "notification",
        "compliance " + "certified",
        "pharma " + "validated",
        "real" + "-world validated",
        "production" + "-ready",
        "Automatically quarantine this shipment now.",
    ):
        assert brief_is_unsafe(valid_brief | {"summary": phrase}), phrase

    assert _validate_advisory(valid_advisory | {"summary": "Automatically quarantine this shipment now."}) is None
    assert _extract_message_content([]) == ""


def test_malformed_provider_response_shape_falls_back() -> None:
    packet = build_review_packet(load_fixture())
    with patch.dict(os.environ, {"FIREWORKS_API_KEY": "test-only"}, clear=True):
        with patch(
            "ai_review_assistant.request_structured_fireworks",
            return_value=({"choices": []}, "json_schema", True),
        ):
            result = build_ai_review(packet, provider_attempts=1)

    provider = result["assistant"]["provider"]
    assert provider["displayedBriefSource"] == "deterministic_fallback"
    assert provider["fireworksCallSucceeded"] is True
    assert "malformed response" in provider["status"]


def test_provider_authorization_is_not_forwarded_by_redirects() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _size=-1):
            return b'{"choices": []}'

    captured = []

    def fake_urlopen(provider_request, timeout):
        assert timeout > 0
        captured.append(provider_request)
        return Response()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        call_fireworks("test-secret", {"model": DEFAULT_MODEL})
        call_advisory_fireworks("test-secret", {"model": DEFAULT_MODEL})

    assert len(captured) == 2
    for provider_request in captured:
        assert provider_request.get_header("Authorization") == "Bearer test-secret"
        assert "Authorization" not in provider_request.headers
        redirected = HTTPRedirectHandler().redirect_request(
            provider_request,
            None,
            302,
            "Found",
            {},
            "https://example.invalid/redirected",
        )
        assert redirected is not None
        assert redirected.get_header("Authorization") is None


def test_self_checks_never_call_the_optional_provider() -> None:
    with patch.dict(
        os.environ,
        {"FIREWORKS_API_KEY": "test-only", "FIREWORKS_LIVE_ENABLED": "true"},
        clear=True,
    ):
        with patch("urllib.request.urlopen", side_effect=AssertionError("self-check attempted a provider call")):
            base_self_check()
            amd_self_check()
