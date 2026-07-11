"""Optional Fireworks reviewer brief for deterministic ColdChain packets."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from fireworks_runtime_guard import guarded_provider_result, read_bounded_json, selected_model, unsafe_provider_text

FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
DEFAULT_MODEL = "accounts/fireworks/routers/kimi-k2p6-turbo"
ALLOWED_MODELS = (DEFAULT_MODEL,)
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
MAX_TEXT = 240
MAX_ITEMS = 5
QUALITY_REJECT_STATUS = "Fireworks call succeeded; output rejected by quality gate; deterministic fallback shown."
JSON_FRAGMENT_MARKERS = [f'"{key}":' for key in BRIEF_KEYS]
UNSAFE_PHRASES = [
    "release shipment",
    "approve shipment",
    "clear for use",
    "safe for distribution",
    "quarantine automatically",
    "discard automatically",
    "reroute automatically",
    "notify customer automatically",
    "validated pharmaceutical product",
    "certified compliance",
    "medical validation",
    "production-ready decision",
    "autonomous " + "release",
    "autonomous " + "quarantine",
    "autonomous " + "discard",
    "autonomous " + "reroute",
    "customer " + "notification",
    "compliance " + "certified",
    "pharma " + "validated",
    "real" + "-world validated",
    "production" + "-ready",
]


def provider_status(
    configured: bool,
    call_succeeded: bool,
    structured_verified: bool,
    model: str,
    source: str,
    status: str,
) -> dict[str, Any]:
    return {
        "fireworksConfigured": configured,
        "fireworksCallSucceeded": call_succeeded,
        "fireworksStructuredOutputVerified": structured_verified,
        "fireworksVerified": structured_verified,
        "fireworksModel": model,
        "displayedBriefSource": source,
        "amdStatus": "pending/not configured",
        "status": status,
    }


def deterministic_brief(packet: dict[str, Any]) -> dict[str, Any]:
    result = packet["result"]
    unresolved = ", ".join(result["unresolvedPalletIds"])
    missing = packet.get("unresolvedEvidence") or []
    if not missing:
        missing = [f"Missing zone mapping for {unresolved}."] if unresolved else ["No missing synthetic pallet mapping listed."]
    return {
        "summary": str(packet.get("summary") or "Synthetic cold-chain review remains pending human review."),
        "whyBlocked": packet["blockingReasons"],
        "missingEvidence": missing,
        "reviewerChecklist": packet["reviewerChecklist"],
        "rootCauseHypotheses": [
            "Zone mapping was not supplied for one pallet.",
            "The temperature excursion requires reviewer inspection before any consequential action.",
        ],
        "safetyNote": "AI-assisted explanation only. Deterministic rules remain authoritative.",
    }


def fallback_brief(packet: dict[str, Any], reason: str, call_succeeded: bool = False) -> dict[str, Any]:
    model = selected_model(DEFAULT_MODEL, ALLOWED_MODELS)
    return {
        "provider": provider_status(
            bool(os.environ.get("FIREWORKS_API_KEY")),
            call_succeeded,
            False,
            model,
            "deterministic_fallback",
            reason,
        ),
        "brief": deterministic_brief(packet),
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
    if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
        return []
    return [bounded_text(item) for item in value[:MAX_ITEMS] if bounded_text(item)]


def bounded_text(value: str, limit: int = MAX_TEXT) -> str:
    value = re.sub(r"[*_`>#\[\]{}]", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -:\t\r\n")
    return value[:limit].rstrip()


def validate_brief(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if not all(key in value for key in BRIEF_KEYS):
        return None
    if not isinstance(value["summary"], str) or not isinstance(value["safetyNote"], str):
        return None
    brief = {
        "summary": bounded_text(value["summary"]),
        "whyBlocked": string_list(value["whyBlocked"]),
        "missingEvidence": string_list(value["missingEvidence"]),
        "reviewerChecklist": string_list(value["reviewerChecklist"]),
        "rootCauseHypotheses": string_list(value["rootCauseHypotheses"]),
        "safetyNote": bounded_text(value["safetyNote"]),
    }
    if not brief["summary"] or not brief["safetyNote"]:
        return None
    if any(not brief[key] for key in ("whyBlocked", "missingEvidence", "reviewerChecklist", "rootCauseHypotheses")):
        return None
    return brief


def flattened_brief_values(brief: dict[str, Any]) -> list[str]:
    values = [str(brief["summary"]), str(brief["safetyNote"])]
    for key in ("whyBlocked", "missingEvidence", "reviewerChecklist", "rootCauseHypotheses"):
        values.extend(str(item) for item in brief[key])
    return values


def quality_gate(brief: dict[str, Any]) -> bool:
    if brief_is_unsafe(brief):
        return False
    values = flattened_brief_values(brief)
    for value in values:
        stripped = value.strip()
        if any(marker in stripped for marker in JSON_FRAGMENT_MARKERS):
            return False
        if "{" in stripped or "}" in stripped:
            return False
        if stripped.startswith(('"', ",")) or stripped.endswith(('"', ",")):
            return False
        if len(stripped) > MAX_TEXT:
            return False

    normalized = [re.sub(r"\s+", " ", value.lower()).strip() for value in values if value.strip()]
    return not any(normalized.count(value) >= 3 for value in set(normalized))


def unsafe_text(value: str) -> bool:
    return unsafe_provider_text(value, UNSAFE_PHRASES)


def brief_is_unsafe(brief: dict[str, Any]) -> bool:
    return any(unsafe_text(value) for value in flattened_brief_values(brief))


def extracted_json_object(content: str) -> dict[str, Any] | None:
    start = content.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(content)):
            char = content[index]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(content[start : index + 1])
                    except json.JSONDecodeError:
                        break
                    return value if isinstance(value, dict) else None
        start = content.find("{", start + 1)
    return None


def candidate_lines(content: str) -> list[str]:
    lines = []
    for raw in content.splitlines():
        line = bounded_text(re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", raw))
        if 20 <= len(line) <= MAX_TEXT:
            lines.append(line)
    return lines[:24]


def lines_with(lines: list[str], *needles: str) -> list[str]:
    values = [line for line in lines if any(needle in line.lower() for needle in needles)]
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen[:MAX_ITEMS]


def sanitize_fireworks_text(packet: dict[str, Any], content: str) -> dict[str, Any] | None:
    if unsafe_text(content):
        return None
    embedded = extracted_json_object(content)
    if embedded is not None:
        brief = validate_brief({key: embedded.get(key) for key in BRIEF_KEYS})
        return brief if brief is not None and quality_gate(brief) else None

    lines = candidate_lines(content)
    joined = " ".join(lines).lower()
    if "pal-syn-1004" not in joined and "temperature" not in joined and "human review" not in joined:
        return None

    fallback = deterministic_brief(packet)
    summary = next(
        (
            line
            for line in lines
            if any(term in line.lower() for term in ("blocked", "human review", "temperature", "missing zone"))
        ),
        fallback["summary"],
    )
    brief = {
        "summary": summary,
        "whyBlocked": lines_with(lines, "blocked", "temperature excursion", "human review") or fallback["whyBlocked"],
        "missingEvidence": lines_with(lines, "missing evidence", "not supplied", "zone mapping is missing")
        or fallback["missingEvidence"],
        "reviewerChecklist": lines_with(lines, "reviewer should", "confirm", "inspect", "resolve")
        or fallback["reviewerChecklist"],
        "rootCauseHypotheses": lines_with(lines, "omitted", "not supplied", "missing mapping", "requires reviewer")
        or fallback["rootCauseHypotheses"],
        "safetyNote": "AI-assisted explanation only. Deterministic rules remain authoritative.",
    }
    brief = validate_brief(brief)
    return brief if brief is not None and quality_gate(brief) else None


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
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Unredirected headers are sent to the fixed provider origin but are not copied
    # by urllib's redirect handler to a different destination.
    request.add_unredirected_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return read_bounded_json(response)


def request_structured_fireworks(api_key: str, payload: dict[str, Any], max_attempts: int = 4) -> tuple[dict[str, Any], str, bool]:
    attempts = [
        ("json_schema", True, json_schema_format()),
        ("json_schema", False, json_schema_format()),
        ("json_object", True, {"type": "json_object"}),
        ("json_object", False, {"type": "json_object"}),
    ]
    last_error: urllib.error.HTTPError | None = None
    for mode, use_reasoning, response_format in attempts[:max_attempts]:
        attempt = dict(payload, response_format=response_format)
        if use_reasoning:
            attempt["reasoning_effort"] = "none"
        try:
            return call_fireworks(api_key, attempt), mode, use_reasoning
        except urllib.error.HTTPError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def request_fireworks(packet: dict[str, Any], max_attempts: int = 4) -> dict[str, Any]:
    api_key = os.environ.get("FIREWORKS_API_KEY")
    model = selected_model(DEFAULT_MODEL, ALLOWED_MODELS)
    if not api_key:
        return fallback_brief(packet, "Fireworks not configured")

    payload = {
        "model": model,
        "messages": build_prompt(packet),
        "max_tokens": 350,
        "temperature": 0.2,
    }

    try:
        body, structured_mode, reasoning_accepted = request_structured_fireworks(api_key, payload, max_attempts)
    except urllib.error.HTTPError as exc:
        return fallback_brief(packet, f"Fireworks unavailable: HTTP {exc.code} {exc.reason}")
    except (OSError, TimeoutError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return fallback_brief(packet, f"Fireworks unavailable: {exc.__class__.__name__}")

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return fallback_brief(
            packet,
            "Fireworks call succeeded; malformed response rejected; deterministic fallback shown.",
            call_succeeded=True,
        )
    if not isinstance(content, str):
        return fallback_brief(
            packet,
            "Fireworks call succeeded; malformed response rejected; deterministic fallback shown.",
            call_succeeded=True,
        )
    try:
        brief = validate_brief(json.loads(content))
    except json.JSONDecodeError:
        brief = sanitize_fireworks_text(packet, content)
        if brief is None:
            status = "Fireworks call succeeded; output rejected by safety filter; deterministic fallback shown."
            if not unsafe_text(content):
                status = QUALITY_REJECT_STATUS
            return fallback_brief(packet, status, call_succeeded=True)
        return {
            "provider": provider_status(
                True,
                True,
                False,
                model,
                "sanitized_fireworks_text",
                "Fireworks call succeeded; sanitized reviewer brief shown.",
            ),
            "brief": brief,
            "unstructuredAiResponse": "",
        }

    unsafe_brief = brief is not None and brief_is_unsafe(brief)
    if brief is None or not quality_gate(brief):
        return fallback_brief(
            packet,
            (
                "Fireworks call succeeded; output rejected by safety filter; deterministic fallback shown."
                if unsafe_brief
                else QUALITY_REJECT_STATUS
            ),
            call_succeeded=True,
        )

    return {
        "provider": provider_status(
            True,
            True,
            True,
            model,
            "fireworks_structured_json",
            "Fireworks verified structured reviewer brief.",
        )
        | {"structuredOutputMode": structured_mode, "reasoningEffortNoneAccepted": reasoning_accepted},
        "brief": brief,
        "unstructuredAiResponse": "",
    }


def build_ai_review(
    packet: dict[str, Any],
    *,
    provider_attempts: int = 4,
    provider_enabled: bool = True,
    disabled_reason: str = "Fireworks live calls are disabled",
) -> dict[str, Any]:
    result_before = json.dumps(packet["result"], sort_keys=True)
    assistant = request_fireworks(packet, provider_attempts) if provider_enabled else fallback_brief(packet, disabled_reason)
    assert json.dumps(packet["result"], sort_keys=True) == result_before
    return {
        "deterministicResult": packet["result"],
        "assistant": assistant,
        "safety": [
            "AI-assisted explanation only.",
            "Deterministic rules remain authoritative.",
            "No autonomous operational action.",
            "No autonomous release, quarantine, discard, reroute, or customer notification.",
            "Synthetic demo data only.",
            "Not a validated pharmaceutical, medical, logistics compliance, or medical product.",
        ],
    }


def build_runtime_ai_review(packet: dict[str, Any], provider_allowed: bool = True) -> dict[str, Any]:
    if not provider_allowed:
        return build_ai_review(packet, provider_enabled=False, disabled_reason="Fireworks calls are not made for HEAD requests")
    cache_key = "ai-review:" + json.dumps(compact_packet(packet), sort_keys=True, separators=(",", ":"))
    return guarded_provider_result(
        cache_key,
        lambda: build_ai_review(packet, provider_attempts=2),
        lambda reason: build_ai_review(packet, provider_enabled=False, disabled_reason=reason),
    )


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
