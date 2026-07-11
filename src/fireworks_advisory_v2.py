from __future__ import annotations

from functools import lru_cache
import html
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable

from fireworks_runtime_guard import guarded_provider_result, live_calls_enabled, read_bounded_json, selected_model, unsafe_provider_text

FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
DEFAULT_MODEL = "accounts/fireworks/routers/kimi-k2p6-turbo"
ALLOWED_MODELS = (DEFAULT_MODEL,)
TIMEOUT_SECONDS = 45
PHASE = "Phase 12 - Fireworks Advisory Explanation Layer"
STATUS = "SAFETY_GATED_OPTIONAL"

CASE_IDS = (
    "no-excursion-control",
    "single-sensor-spike",
    "multi-sensor-confirmed-warming",
    "unresolved-mapping-risk",
    "door-open-warming",
    "dropout-weak-signal",
)

ADVISORY_KEYS = (
    "summary",
    "riskDrivers",
    "evidenceToInspect",
    "confidenceLimits",
    "humanReviewPrompt",
    "safetyNote",
)

MAX_TEXT = 260
MAX_ITEMS = 5

UNSAFE_PHRASES = (
    "safe for distribution",
    "approve shipment",
    "clear for use",
    "release " + "shipment",
    "autonomous " + "release",
    "autonomous " + "quarantine",
    "autonomous " + "discard",
    "autonomous " + "reroute",
    "customer " + "notification",
    "compliance " + "certified",
    "pharma " + "validated",
    "real" + "-world validated",
    "production" + "-ready",
)


def _bounded_text(value: str, limit: int = MAX_TEXT) -> str:
    cleaned = re.sub(r"[*_`>#\[\]{}]", "", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:\t\r\n")
    return cleaned[:limit].rstrip()


def _bounded_list(value: Any) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(entry, str) for entry in value):
        return []
    return [
        item
        for item in (_bounded_text(entry) for entry in value[:MAX_ITEMS])
        if item
    ]


def _flatten(value: dict[str, Any]) -> str:
    pieces: list[str] = []
    for key in ADVISORY_KEYS:
        entry = value.get(key)
        if isinstance(entry, list):
            pieces.extend(str(item) for item in entry)
        else:
            pieces.append(str(entry))
    return " ".join(pieces)


def _unsafe_text(value: str) -> bool:
    return unsafe_provider_text(value, UNSAFE_PHRASES)


def _validate_advisory(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if not all(key in value for key in ADVISORY_KEYS):
        return None
    if any(not isinstance(value[key], str) for key in ("summary", "humanReviewPrompt", "safetyNote")):
        return None

    advisory = {
        "summary": _bounded_text(value["summary"]),
        "riskDrivers": _bounded_list(value["riskDrivers"]),
        "evidenceToInspect": _bounded_list(value["evidenceToInspect"]),
        "confidenceLimits": _bounded_list(value["confidenceLimits"]),
        "humanReviewPrompt": _bounded_text(value["humanReviewPrompt"]),
        "safetyNote": _bounded_text(value["safetyNote"]),
    }

    if not advisory["summary"] or not advisory["humanReviewPrompt"] or not advisory["safetyNote"]:
        return None
    if not advisory["riskDrivers"] or not advisory["evidenceToInspect"] or not advisory["confidenceLimits"]:
        return None
    if _unsafe_text(_flatten(advisory)):
        return None
    return advisory


def _case_context(case_id: str) -> dict[str, Any]:
    from sers_v2 import sers_case_json

    try:
        sers = sers_case_json(case_id)
    except KeyError:
        from scenario_lab_v2 import get_scenario_payload

        scenario = get_scenario_payload(case_id)
        advisory = scenario["sersAdvisoryFindings"]
        sers = {
            "modelVersion": scenario["version"],
            "status": "SCENARIO_ADVISORY",
            "currentRisk": {"riskBand": advisory["riskBand"], "riskScore": advisory["riskScore"]},
            "factorsThatMatterMost": [{"label": advisory["primaryReason"]}],
            "confidence": {"confidenceLabel": advisory["confidenceLabel"]},
            "advisoryOnly": True,
            "autonomousActionsAllowed": False,
        }
    return {
        "caseId": case_id,
        "modelVersion": sers.get("modelVersion"),
        "status": sers.get("status"),
        "currentRisk": sers.get("currentRisk", {}),
        "factorsThatMatterMost": sers.get("factorsThatMatterMost", []),
        "confidence": sers.get("confidence", {}),
        "advisoryOnly": sers.get("advisoryOnly", True),
        "autonomousActionsAllowed": sers.get("autonomousActionsAllowed", False),
        "deterministicRulesAuthoritative": True,
        "syntheticOnly": True,
    }


def _deterministic_advisory(context: dict[str, Any]) -> dict[str, Any]:
    risk = context.get("currentRisk", {})
    factors = context.get("factorsThatMatterMost", [])[:3]
    factor_labels = [
        str(item.get("label") or item.get("featureId") or "Synthetic risk factor")
        for item in factors
        if isinstance(item, dict)
    ]

    if not factor_labels:
        factor_labels = ["Synthetic SERS evidence should be reviewed by a human."]

    return {
        "summary": (
            f"Synthetic case {context['caseId']} remains an advisory review item with "
            f"risk band {risk.get('riskBand', 'UNKNOWN')}."
        ),
        "riskDrivers": factor_labels,
        "evidenceToInspect": [
            "Review synthetic sensor windows and consensus evidence.",
            "Inspect data-quality, mapping, and signal-confidence limitations.",
            "Compare SERS advisory output against deterministic rule outcomes.",
        ],
        "confidenceLimits": [
            "Synthetic benchmark evidence only.",
            "No real shipment or customer data is used.",
            "Human review remains required before any operational decision.",
        ],
        "humanReviewPrompt": "Inspect the synthetic evidence packet and document what additional evidence would be needed.",
        "safetyNote": "Fireworks explanation is optional. Deterministic rules remain authoritative.",
    }


def _provider_status(
    *,
    configured: bool,
    call_succeeded: bool,
    safety_gate_passed: bool,
    source: str,
    status: str,
    model: str,
) -> dict[str, Any]:
    return {
        "fireworksConfigured": configured,
        "fireworksCallSucceeded": call_succeeded,
        "fireworksSafetyGatePassed": safety_gate_passed,
        "displayedAdvisorySource": source,
        "fireworksModel": model,
        "status": status,
        "deterministicRulesAuthoritative": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
    }


def _fallback_payload(context: dict[str, Any], reason: str, *, call_succeeded: bool = False) -> dict[str, Any]:
    model = selected_model(DEFAULT_MODEL, ALLOWED_MODELS)
    return {
        "phase": PHASE,
        "status": STATUS,
        "caseId": context["caseId"],
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
        "provider": _provider_status(
            configured=bool(os.environ.get("FIREWORKS_API_KEY")),
            call_succeeded=call_succeeded,
            safety_gate_passed=False,
            source="deterministic_fallback",
            status=reason,
            model=model,
        ),
        "context": context,
        "advisory": _deterministic_advisory(context),
        "safetyBoundaries": safety_boundaries(),
    }


def _build_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    risk = context.get("currentRisk", {})
    confidence = context.get("confidence", {})

    factors: list[str] = []
    for item in context.get("factorsThatMatterMost", [])[:3]:
        if isinstance(item, dict):
            label = str(item.get("label") or item.get("featureId") or "Synthetic advisory factor")
            factors.append(label[:90])

    compact_context = {
        "caseId": context.get("caseId"),
        "riskBand": risk.get("riskBand"),
        "riskScore": risk.get("riskScore"),
        "confidenceLabel": confidence.get("label") or confidence.get("confidenceLabel"),
        "topFactors": factors,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "autonomousActionsAllowed": False,
        "deterministicRulesAuthoritative": True,
    }

    system = (
        "Return exactly one valid minified JSON object. No markdown. No code fence. "
        "Use exactly these keys: summary, riskDrivers, evidenceToInspect, confidenceLimits, "
        "humanReviewPrompt, safetyNote. "
        "summary, humanReviewPrompt, and safetyNote must be short strings under 140 characters. "
        "riskDrivers, evidenceToInspect, and confidenceLimits must be arrays with 1 to 3 short strings. "
        "Do not use these phrases: safe for distribution, approve shipment, release shipment, "
        "autonomous release, autonomous quarantine, autonomous discard, autonomous reroute, "
        "customer notification, compliance certified, pharma validated, real-world validated, production-ready. "
        "Do not recommend operational action. Deterministic rules remain authoritative."
    )

    user = {
        "requiredJsonShape": {
            "summary": "short string",
            "riskDrivers": ["short string"],
            "evidenceToInspect": ["short string"],
            "confidenceLimits": ["short string"],
            "humanReviewPrompt": "short string",
            "safetyNote": "short string",
        },
        "safeExample": {
            "summary": "Synthetic advisory evidence remains available for human review.",
            "riskDrivers": ["Synthetic SERS factors should be inspected."],
            "evidenceToInspect": ["Review synthetic sensor and consensus evidence."],
            "confidenceLimits": ["Synthetic-only evidence cannot validate real operations."],
            "humanReviewPrompt": "Document what evidence a reviewer would inspect next.",
            "safetyNote": "Optional explanation only. Deterministic rules remain authoritative.",
        },
        "context": compact_context,
    }

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, sort_keys=True)},
    ]

def _call_fireworks(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        FIREWORKS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ColdChainSentinel/phase12 (+https://github.com/strider308/coldchain-sentinel)",
        },
        method="POST",
    )
    request.add_unredirected_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return read_bounded_json(response)


def _extract_message_content(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    return content if isinstance(content, str) else json.dumps(content)


def _extract_json_object(content: str) -> dict[str, Any] | None:
    try:
        value = json.loads(content)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass

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


def get_case_fireworks_advisory_payload(
    case_id: str,
    requester: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    context = _case_context(case_id)
    original_context = json.dumps(context, sort_keys=True)
    api_key = os.environ.get("FIREWORKS_API_KEY")
    model = selected_model(DEFAULT_MODEL, ALLOWED_MODELS)

    if not api_key:
        return _fallback_payload(context, "Fireworks not configured")

    request_payload = {
        "model": model,
        "messages": _build_messages(context),
        "max_tokens": 700,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    try:
        body = (requester or _call_fireworks)(api_key, request_payload)
    except urllib.error.HTTPError as exc:
        return _fallback_payload(context, f"Fireworks unavailable: HTTP {exc.code} {exc.reason}")
    except (OSError, TimeoutError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return _fallback_payload(context, f"Fireworks unavailable: {exc.__class__.__name__}")

    assert json.dumps(context, sort_keys=True) == original_context

    content = _extract_message_content(body)
    candidate = _extract_json_object(content)
    advisory = _validate_advisory(candidate)

    if advisory is None:
        return _fallback_payload(
            context,
            "Fireworks call succeeded; output rejected by safety gate; deterministic fallback shown.",
            call_succeeded=True,
        )

    return {
        "phase": PHASE,
        "status": STATUS,
        "caseId": context["caseId"],
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
        "provider": _provider_status(
            configured=True,
            call_succeeded=True,
            safety_gate_passed=True,
            source="fireworks_safety_gated_json",
            status="Fireworks advisory explanation accepted by safety gate.",
            model=model,
        ),
        "context": context,
        "advisory": advisory,
        "safetyBoundaries": safety_boundaries(),
    }


def get_runtime_case_fireworks_advisory_payload(case_id: str, provider_allowed: bool = True) -> dict[str, Any]:
    context = _case_context(case_id)
    if not provider_allowed:
        return _fallback_payload(context, "Fireworks calls are not made for HEAD requests")
    return guarded_provider_result(
        "fireworks-advisory:" + case_id,
        lambda: get_case_fireworks_advisory_payload(case_id),
        lambda reason: _fallback_payload(context, reason),
    )


def safety_boundaries() -> dict[str, Any]:
    return {
        "syntheticOnly": True,
        "advisoryOnly": True,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
        "runtimeExternalServiceRequired": False,
        "fallbackRequired": True,
        "notClaimed": [
            "operation-ready deployment",
            "regulated pharma validation",
            "real deployment validation",
            "compliance signoff",
            "release/quarantine/discard/reroute decisions",
            "customer messaging decisions",
        ],
    }


@lru_cache(maxsize=1)
def get_fireworks_advisory_payload() -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
        "fireworksConfigured": bool(os.environ.get("FIREWORKS_API_KEY")),
        "defaultModel": selected_model(DEFAULT_MODEL, ALLOWED_MODELS),
        "liveCallsEnabled": live_calls_enabled(),
        "cases": [
            {
                "caseId": case_id,
                "route": f"/cases/{case_id}/fireworks-advisory.json",
            }
            for case_id in CASE_IDS
        ],
        "routeLinks": {
            "html": "/fireworks-advisory",
            "json": "/fireworks-advisory.json",
            "modelCard": "/fireworks-model-card",
            "modelCardJson": "/fireworks-model-card.json",
            "sers": "/sers",
            "scenarioLab": "/scenario-lab",
            "reviewWorkbench": "/review-workbench",
        },
        "safetyBoundaries": safety_boundaries(),
    }


def get_fireworks_model_card_payload() -> dict[str, Any]:
    return {
        "modelCardName": "Fireworks Advisory Explanation Layer",
        "phase": PHASE,
        "model": selected_model(DEFAULT_MODEL, ALLOWED_MODELS),
        "purpose": "Optional explanation support for synthetic SERS review evidence.",
        "inputScope": "Synthetic, compact, redacted advisory case context only.",
        "outputScope": "Human-readable explanation fields accepted only after safety validation.",
        "fallback": "Deterministic fallback is shown when Fireworks is not configured, unavailable, malformed, or unsafe.",
        "safetyControls": [
            "Deterministic rules remain authoritative.",
            "SERS remains advisory-only.",
            "Fireworks cannot change risk or operational status.",
            "Unsafe or malformed output is rejected.",
            "No external service is required for the app to run.",
        ],
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
        "safetyBoundaries": safety_boundaries(),
    }


def _json_block(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def render_fireworks_advisory_html() -> str:
    payload = get_fireworks_advisory_payload()
    cases = "\n".join(
        f'<li><a href="{html.escape(item["route"])}">{html.escape(item["caseId"])}</a></li>'
        for item in payload["cases"]
    )
    links = "\n".join(
        f'<a class="button" href="{html.escape(url)}">{html.escape(name)}</a>'
        for name, url in payload["routeLinks"].items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ColdChain Sentinel Fireworks Advisory Layer</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #071014; color: #eef7f2; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }}
    .panel {{ background: #102129; border: 1px solid #21414d; border-radius: 18px; padding: 20px; margin: 18px 0; }}
    .badge {{ display: inline-block; margin: 4px 8px 4px 0; padding: 6px 10px; border-radius: 999px; background: #20323a; border: 1px solid #3b5965; }}
    .button {{ display: inline-block; margin: 6px 8px 6px 0; padding: 8px 12px; border-radius: 12px; background: #18323b; color: #96e6b3; text-decoration: none; border: 1px solid #315766; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #071014; border: 1px solid #21414d; border-radius: 14px; padding: 16px; }}
    a {{ color: #96e6b3; }}
  </style>
</head>
<body>
<main data-testid="fireworks-advisory-page">
  <p><a href="/">ColdChain Sentinel</a></p>
  <h1>Fireworks Advisory Explanation Layer</h1>
  <p>Optional Fireworks explanation support for synthetic SERS evidence. Deterministic rules remain authoritative.</p>
  <span class="badge">Synthetic-only</span>
  <span class="badge">Advisory-only</span>
  <span class="badge">Fallback always available</span>
  <span class="badge">Runtime external service required: false</span>

  <section class="panel">
    <h2>Configured Status</h2>
    <p>Fireworks configured: {str(payload["fireworksConfigured"]).lower()}</p>
    <p>Default model: {html.escape(payload["defaultModel"])}</p>
  </section>

  <section class="panel">
    <h2>Case Routes</h2>
    <ul>{cases}</ul>
  </section>

  <section class="panel">
    <h2>Routes</h2>
    <div>{links}</div>
  </section>

  <section class="panel">
    <h2>Machine-Readable Payload</h2>
    <pre>{_json_block(payload)}</pre>
  </section>
</main>
</body>
</html>"""


def render_fireworks_model_card_html() -> str:
    payload = get_fireworks_model_card_payload()
    controls = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["safetyControls"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ColdChain Sentinel Fireworks Model Card</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #071014; color: #eef7f2; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 56px; }}
    section {{ background: #102129; border: 1px solid #21414d; border-radius: 18px; padding: 20px; margin: 18px 0; }}
    a {{ color: #96e6b3; }}
  </style>
</head>
<body>
<main data-testid="fireworks-model-card-page">
  <p><a href="/fireworks-advisory">Fireworks Advisory Layer</a></p>
  <h1>{html.escape(payload["modelCardName"])}</h1>
  <p>{html.escape(payload["purpose"])}</p>
  <section>
    <h2>Scope</h2>
    <p>Input: {html.escape(payload["inputScope"])}</p>
    <p>Output: {html.escape(payload["outputScope"])}</p>
    <p>Fallback: {html.escape(payload["fallback"])}</p>
  </section>
  <section>
    <h2>Safety Controls</h2>
    <ul>{controls}</ul>
  </section>
  <section>
    <h2>Payload</h2>
    <pre>{_json_block(payload)}</pre>
  </section>
</main>
</body>
</html>"""
