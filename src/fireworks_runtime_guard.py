"""Small process-local guard for optional paid Fireworks calls."""

from __future__ import annotations

from copy import deepcopy
import json
import os
import re
import threading
import time
from typing import Any, Callable

MAX_PROVIDER_RESPONSE_BYTES = 65_536
_CACHE_TTL_SECONDS = 300.0
_COOLDOWN_SECONDS = 10.0
_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_LAST_CALL = 0.0


def unsafe_provider_text(value: str, phrases: tuple[str, ...] | list[str] = ()) -> bool:
    normalized = re.sub(r"\s+", " ", value.lower())
    if any(phrase in normalized for phrase in phrases):
        return True
    tokens = re.findall(r"[a-z]+", normalized)

    def near(left: set[str], right: set[str], distance: int = 4) -> bool:
        left_positions = [index for index, token in enumerate(tokens) if token in left]
        right_positions = [index for index, token in enumerate(tokens) if token in right]
        return any(abs(left_index - right_index) <= distance for left_index in left_positions for right_index in right_positions)

    automation = {"autonomous", "autonomously", "automatic", "automatically"}
    actions = {"release", "quarantine", "quarantined", "discard", "reroute"}
    return near(automation, actions) or any(
        near(left, right)
        for left, right in (
            ({"approve", "release"}, {"shipment"}),
            ({"safe"}, {"distribution"}),
            ({"clear"}, {"use"}),
            ({"notify"}, {"customer"}),
            ({"customer"}, {"notification"}),
            ({"compliance"}, {"certified"}),
            ({"pharma", "pharmaceutical"}, {"validated"}),
            ({"real", "world"}, {"validated"}),
            ({"production"}, {"ready"}),
        )
    )


def live_calls_enabled() -> bool:
    return os.environ.get("FIREWORKS_LIVE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def selected_model(default: str, allowed: tuple[str, ...]) -> str:
    candidate = os.environ.get("FIREWORKS_MODEL") or default
    return candidate if candidate in allowed else default


def read_bounded_json(response: Any) -> dict[str, Any]:
    try:
        raw = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
    except TypeError:  # Minimal compatibility for existing test doubles.
        raw = response.read()
    if len(raw) > MAX_PROVIDER_RESPONSE_BYTES:
        raise ValueError("provider response exceeds size limit")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provider response must be a JSON object")
    return value


def guarded_provider_result(
    cache_key: str,
    call: Callable[[], dict[str, Any]],
    fallback: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    if not live_calls_enabled():
        return fallback("Fireworks live calls are disabled by default")

    global _LAST_CALL
    # ponytail: one process-wide lock/cache; use a shared quota store only for multi-instance paid traffic.
    with _LOCK:
        now = time.monotonic()
        cached = _CACHE.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return deepcopy(cached[1])
        if _LAST_CALL and now - _LAST_CALL < _COOLDOWN_SECONDS:
            return fallback("Fireworks per-process cooldown is active")
        _LAST_CALL = now
        result = call()
        _CACHE[cache_key] = (time.monotonic(), deepcopy(result))
        return result
