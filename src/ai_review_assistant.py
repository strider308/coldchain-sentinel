"""Optional Fireworks reviewer brief for deterministic ColdChain packets."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
DEFAULT_MODEL = "accounts/fireworks/routers/kimi-k2p6-turbo"
TIMEOUT_SECONDS = 12
BRIEF_KEYS = ["summary", "whyBlocked", "missingEvidence", "reviewerChecklist", "rootCauseHypotheses", "safetyNote"]
BRIEF_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": BRIEF_KEYS,
    "properties": {
        "summary": {"type": "string"},
        "whyBlocked": {"type": "array", "items": {"type": "string"}},
        "missingEvidence": {"type": "array", "items": {"type": "string"}},
        "reviewerChecklist": {"type": "array", "items": {"type": "string"}},
        "rootCauseHypotheses": {"type": "array", "items": {"type": "string"}},
        "safetyNote": {"type": "string"},
    },
}


def fallback_brief(packet: dict[str, Any], reason: str) -> dict[str, Any]:
    result = packet["result"]
    unresolved = ", ".join(result["unresolvedPalletIds"])
    return {
        "provider": {
            "fireworksConfigured": bool(os.environ.get("FIREWORKS_API_KEY")),
            "fireworksVerified": False,
            "fireworksModel": os.environ.get("FIREWORKS_MODEL") or DEFAULT_MODEL,
            "amdStatus": "pending/not configured",
            "status": reason,
        },
        "brief": {
            "summary": "Synthetic cold-chain excursion review remains blocked pending human review.",
            "whyBlocked": packet["blockingReasons"],
            "missingEvidence": [f"Missing zone mapping for {unresolved}."],
            "reviewerChecklist": packet["reviewerChecklist"],
            "rootCauseHypotheses": [
                "Zone mapping was not supplied for one pallet.",
                "The temperature excursion requires reviewer inspection before any consequential action.",
            ],
            "safetyNote": "AI-assisted explanation only. Deterministic rules remain authoritative.",
        },
        "unstructuredAiResponse": "",
    }


def compact_packet(packet: dict[str, Any]) -> dict[str, Any]:
    result = packet["result"]
    return {
        "shipmentId": result["shipmentId"],
        "excursion": result["excursion"],
        "mappedPalletIds": result["mappedPalletIds"],
        "unresolvedPalletIds": result["unresolvedPalletIds"],
        "finalDisposition": result["finalDisposition"],
        "reviewStatus": result["reviewStatus"],
        "autonomousActionsAllowed": result["autonomousActionsAllowed"],
        "blockingReasons": packet["blockingReasons"],
        "prohibitedAutonomousActions": packet["prohibitedAutonomousActions"],
        "limitations": packet["limitations"],
    }


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def validate_brief(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if not all(key in value for key in BRIEF_KEYS):
        return None
    return {
        "summary": str(value["summary"]),
        "whyBlocked": string_list(value["whyBlocked"]),
        "missingEvidence": string_list(value["missingEvidence"]),
        "reviewerChecklist": string_list(value["reviewerChecklist"]),
        "rootCauseHypotheses": string_list(value["rootCauseHypotheses"]),
        "safetyNote": str(value["safetyNote"]),
    }


def build_prompt(packet: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "You are assisting a human cold-chain reviewer. The supplied deterministic review packet is authoritative. "
        "Return only valid JSON. No reasoning. No markdown. No prose outside JSON. Do not include chain-of-thought. "
        "Do not change final disposition. Do not recommend autonomous release, quarantine, discard, reroute, or customer notification. "
        "Summarize only the supplied synthetic review packet with keys: "
        "summary, whyBlocked, missingEvidence, reviewerChecklist, rootCauseHypotheses, safetyNote."
    )
    user = json.dumps(compact_packet(packet), sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def json_schema_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "coldchain_reviewer_brief",
            "strict": True,
            "schema": BRIEF_SCHEMA,
        },
    }


def call_fireworks(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        FIREWORKS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def request_structured_fireworks(api_key: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str, bool]:
    attempts = [
        ("json_schema", True, json_schema_format()),
        ("json_schema", False, json_schema_format()),
        ("json_object", True, {"type": "json_object"}),
        ("json_object", False, {"type": "json_object"}),
    ]
    last_error: urllib.error.HTTPError | None = None
    for mode, use_reasoning, response_format in attempts:
        attempt = dict(payload, response_format=response_format)
        if use_reasoning:
            attempt["reasoning_effort"] = "none"
        try:
            return call_fireworks(api_key, attempt), mode, use_reasoning
        except urllib.error.HTTPError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def request_fireworks(packet: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("FIREWORKS_API_KEY")
    model = os.environ.get("FIREWORKS_MODEL") or DEFAULT_MODEL
    if not api_key:
        return fallback_brief(packet, "Fireworks not configured")

    payload = {
        "model": model,
        "messages": build_prompt(packet),
        "max_tokens": 350,
        "temperature": 0.2,
    }

    try:
        body, structured_mode, reasoning_accepted = request_structured_fireworks(api_key, payload)
    except urllib.error.HTTPError as exc:
        return fallback_brief(packet, f"Fireworks called but structured verification pending: HTTP {exc.code} {exc.reason}")
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return fallback_brief(packet, f"Fireworks unavailable: {exc.__class__.__name__}")

    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    try:
        brief = validate_brief(json.loads(content))
    except json.JSONDecodeError:
        return fallback_brief(packet, "Fireworks called but structured verification pending: unstructured text")

    if brief is None:
        return fallback_brief(packet, "Fireworks called but structured verification pending: invalid JSON")

    return {
        "provider": {
            "fireworksConfigured": True,
            "fireworksVerified": True,
            "fireworksModel": model,
            "amdStatus": "pending/not configured",
            "status": "Fireworks verified structured reviewer brief",
            "structuredOutputMode": structured_mode,
            "reasoningEffortNoneAccepted": reasoning_accepted,
        },
        "brief": brief,
        "unstructuredAiResponse": "",
    }


def build_ai_review(packet: dict[str, Any]) -> dict[str, Any]:
    result_before = json.dumps(packet["result"], sort_keys=True)
    assistant = request_fireworks(packet)
    assert json.dumps(packet["result"], sort_keys=True) == result_before
    return {
        "deterministicResult": packet["result"],
        "assistant": assistant,
        "safety": [
            "AI-assisted explanation only.",
            "Deterministic rules remain authoritative.",
            "No autonomous release, quarantine, discard, reroute, or customer notification.",
            "Synthetic demo data only.",
            "Not a validated pharmaceutical, medical, logistics compliance, or medical product.",
        ],
    }


def self_check() -> None:
    from coldchain_baseline import build_review_packet, load_fixture

    old_key = os.environ.pop("FIREWORKS_API_KEY", None)
    try:
        packet = build_review_packet(load_fixture())
        result_before = json.dumps(packet["result"], sort_keys=True)
        review = build_ai_review(packet)
        assert review["assistant"]["provider"]["fireworksVerified"] is False
        assert review["deterministicResult"]["finalDisposition"] == "BLOCKED"
        assert review["deterministicResult"]["reviewStatus"] == "HUMAN_REVIEW_REQUIRED"
        assert review["deterministicResult"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]
        assert review["deterministicResult"]["autonomousActionsAllowed"] is False
        assert json.dumps(packet["result"], sort_keys=True) == result_before
    finally:
        if old_key is not None:
            os.environ["FIREWORKS_API_KEY"] = old_key


if __name__ == "__main__":
    self_check()
    print("ai review assistant self-check passed")
