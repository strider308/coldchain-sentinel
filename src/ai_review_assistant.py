"""Optional Fireworks reviewer brief for deterministic ColdChain packets."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
DEFAULT_MODEL = "accounts/fireworks/models/deepseek-v3p1"
TIMEOUT_SECONDS = 12


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


def validate_brief(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    required = ["summary", "whyBlocked", "missingEvidence", "reviewerChecklist", "rootCauseHypotheses", "safetyNote"]
    if not all(key in value for key in required):
        return None
    return value


def build_prompt(packet: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "You are assisting a human cold-chain reviewer. The supplied deterministic review packet is authoritative. "
        "Do not change final disposition. Do not recommend autonomous release, quarantine, discard, reroute, or customer notification. "
        "Summarize only the supplied synthetic review packet. Return concise JSON only with keys: "
        "summary, whyBlocked, missingEvidence, reviewerChecklist, rootCauseHypotheses, safetyNote."
    )
    user = json.dumps(compact_packet(packet), sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def request_fireworks(packet: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("FIREWORKS_API_KEY")
    model = os.environ.get("FIREWORKS_MODEL") or DEFAULT_MODEL
    if not api_key:
        return fallback_brief(packet, "Fireworks not configured")

    payload = {
        "model": model,
        "messages": build_prompt(packet),
        "max_tokens": 450,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        FIREWORKS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return fallback_brief(packet, f"Fireworks unavailable: {exc.__class__.__name__}")

    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    try:
        brief = validate_brief(json.loads(content))
    except json.JSONDecodeError:
        fallback = fallback_brief(packet, "Fireworks returned unstructured text")
        fallback["unstructuredAiResponse"] = content
        return fallback

    if brief is None:
        return fallback_brief(packet, "Fireworks returned invalid JSON")

    return {
        "provider": {
            "fireworksConfigured": True,
            "fireworksVerified": True,
            "fireworksModel": model,
            "amdStatus": "pending/not configured",
            "status": "Fireworks call succeeded",
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
