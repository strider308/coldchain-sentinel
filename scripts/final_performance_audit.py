#!/usr/bin/env python3
"""Bounded, stdlib-only HTTP performance audit for ColdChain Sentinel."""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


PRIMARY_ROUTES = (
    "/",
    "/command-center",
    "/command-center.json",
    "/dashboard-strategy",
    "/algorithm-console",
    "/behavior-predictor",
    "/inspection-engine",
    "/judge-pack",
    "/case-walkthroughs",
    "/case-walkthroughs/door-open-warming",
    "/fault-atlas",
    "/large-scale-data-lab",
    "/final-route-manifest",
    "/submission-readiness",
    "/demo-script-final",
    "/judge-qna",
    "/final-freeze",
)
CONCURRENCY_ROUTES = (
    "/command-center",
    "/command-center.json",
    "/algorithm-console",
    "/judge-pack",
    "/case-walkthroughs/door-open-warming",
)
MIN_WARM_SAMPLES = 20
CONCURRENCY_WORKERS = 10
CONCURRENCY_REQUESTS = 50
MAX_BODY_BYTES = 8 * 1024 * 1024
DEFAULT_JSON_OUTPUT = Path("submission-work/final-audit/performance-audit.json")
DEFAULT_MARKDOWN_OUTPUT = Path("submission-work/final-audit/performance-audit.md")


class _HtmlCounts(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links = 0
        self.articles = 0
        self.sections = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "a" and any(name.lower() == "href" for name, _ in attrs):
            self.links += 1
        elif tag == "article":
            self.articles += 1
        elif tag == "section":
            self.sections += 1


class _NoRedirects(HTTPRedirectHandler):
    """Expose redirects as results; never follow them to another origin."""

    def redirect_request(self, request: Any, file_pointer: Any, code: int, message: str,
                         headers: Any, new_url: str) -> None:
        return None


def normalize_base_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute http:// or https:// origin")
    if parsed.username or parsed.password:
        raise ValueError("base URL must not contain credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("base URL must contain only a scheme and origin")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, "", "", ""))


def _route_url(base_url: str, route: str) -> str:
    parsed = urlsplit(route)
    if not route.startswith("/") or parsed.scheme or parsed.netloc:
        raise ValueError(f"route must be an origin-relative path: {route!r}")
    return f"{base_url}{route}"


def _read_limited(response: Any) -> bytes:
    body = response.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
        raise ValueError(f"response exceeds {MAX_BODY_BYTES} bytes")
    return body


def _decoded_body(body: bytes, content_encoding: str) -> bytes:
    if content_encoding.lower().split(",", 1)[0].strip() != "gzip":
        return body
    decoded = gzip.decompress(body)
    if len(decoded) > MAX_BODY_BYTES:
        raise ValueError(f"decoded response exceeds {MAX_BODY_BYTES} bytes")
    return decoded


def _header_map(headers: Any) -> dict[str, str]:
    return {name.lower(): value for name, value in headers.items()}


def request_route(base_url: str, route: str, timeout: float) -> dict[str, Any]:
    """Fetch one fixed route without following redirects or discovering links."""
    url = _route_url(base_url, route)
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip",
            "User-Agent": "ColdChainSentinel-FinalPerformanceAudit/1.0",
        },
    )
    started = time.perf_counter()
    response: Any = None
    error: str | None = None
    try:
        response = build_opener(_NoRedirects).open(request, timeout=timeout)
        status = response.status
        headers = _header_map(response.headers)
        transfer_body = _read_limited(response)
    except HTTPError as exc:
        response = exc
        status = exc.code
        headers = _header_map(exc.headers)
        try:
            transfer_body = _read_limited(exc)
        except (OSError, ValueError) as body_error:
            transfer_body = b""
            error = f"{type(body_error).__name__}: {body_error}"
    except (OSError, URLError, ValueError) as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "route": route,
            "url": url,
            "status": None,
            "contentType": None,
            "bodyBytes": 0,
            "transferBytes": 0,
            "linkCount": 0,
            "articleCount": 0,
            "sectionCount": 0,
            "headers": {},
            "elapsedMs": round(elapsed_ms, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        if response is not None:
            response.close()

    elapsed_ms = (time.perf_counter() - started) * 1000
    try:
        body = _decoded_body(transfer_body, headers.get("content-encoding", ""))
    except (OSError, ValueError) as exc:
        body = b""
        error = f"{type(exc).__name__}: {exc}"
    content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower() or None
    counts = _HtmlCounts()
    if content_type == "text/html" and body:
        counts.feed(body.decode("utf-8", errors="replace"))
        counts.close()
    return {
        "route": route,
        "url": url,
        "status": status,
        "contentType": content_type,
        "bodyBytes": len(body),
        "transferBytes": len(transfer_body),
        "linkCount": counts.links,
        "articleCount": counts.articles,
        "sectionCount": counts.sections,
        "headers": headers,
        "elapsedMs": round(elapsed_ms, 3),
        "error": error,
    }


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _timing_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    timings = [float(result["elapsedMs"]) for result in results]
    statuses = Counter(str(result["status"]) for result in results if result["status"] is not None)
    return {
        "sampleCount": len(results),
        "samplesMs": timings,
        "medianMs": round(statistics.median(timings), 3) if timings else None,
        "p95Ms": round(_p95(timings), 3) if timings else None,
        "minMs": round(min(timings), 3) if timings else None,
        "maxMs": round(max(timings), 3) if timings else None,
        "statusCounts": dict(sorted(statuses.items())),
        "errorCount": sum(result["error"] is not None for result in results),
    }


def profile_route(base_url: str, route: str, warm_samples: int, timeout: float,
                  cold_timeout: float | None = None) -> dict[str, Any]:
    if warm_samples < MIN_WARM_SAMPLES:
        raise ValueError(f"warm_samples must be at least {MIN_WARM_SAMPLES}")
    cold = request_route(base_url, route, cold_timeout or timeout)
    warm_results = [request_route(base_url, route, timeout) for _ in range(warm_samples)]
    warm = _timing_summary(warm_results)
    headers = cold["headers"]
    return {
        "route": route,
        "url": cold["url"],
        "status": cold["status"],
        "contentType": cold["contentType"],
        "bodyBytes": cold["bodyBytes"],
        "transferBytes": cold["transferBytes"],
        "linkCount": cold["linkCount"],
        "articleCount": cold["articleCount"],
        "sectionCount": cold["sectionCount"],
        "headers": headers,
        "cacheHeaders": {
            name: headers.get(name)
            for name in ("cache-control", "etag", "expires", "last-modified", "vary")
            if name in headers
        },
        "gzipRequested": True,
        "gzipUsed": headers.get("content-encoding", "").lower().startswith("gzip"),
        "coldResponseMs": cold["elapsedMs"],
        "coldError": cold["error"],
        "warmSampleCount": warm["sampleCount"],
        "warmSamplesMs": warm["samplesMs"],
        "warmMedianMs": warm["medianMs"],
        "warmP95Ms": warm["p95Ms"],
        "warmMinMs": warm["minMs"],
        "warmMaxMs": warm["maxMs"],
        "warmStatusCounts": warm["statusCounts"],
        "warmErrorCount": warm["errorCount"],
    }


def _is_loopback(base_url: str) -> bool:
    host = (urlsplit(base_url).hostname or "").lower()
    return host == "localhost" or host.endswith(".localhost") or host in {"127.0.0.1", "::1"}


def run_concurrency_audit(base_url: str, timeout: float) -> dict[str, Any]:
    if not _is_loopback(base_url):
        return {
            "skipped": True,
            "reason": "Mixed-route concurrency is limited to loopback targets.",
            "workers": CONCURRENCY_WORKERS,
            "requestCount": 0,
            "plannedRequestCount": CONCURRENCY_REQUESTS,
            "routes": list(CONCURRENCY_ROUTES),
        }

    routes = [CONCURRENCY_ROUTES[index % len(CONCURRENCY_ROUTES)] for index in range(CONCURRENCY_REQUESTS)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY_WORKERS) as executor:
        results = list(executor.map(lambda route: request_route(base_url, route, timeout), routes))
    summary = _timing_summary(results)
    per_route: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        per_route[result["route"]].append(result)
    return {
        "skipped": False,
        "workers": CONCURRENCY_WORKERS,
        "requestCount": len(results),
        "routes": list(CONCURRENCY_ROUTES),
        "medianMs": summary["medianMs"],
        "p95Ms": summary["p95Ms"],
        "statusCounts": summary["statusCounts"],
        "errorCount": summary["errorCount"],
        "perRoute": {route: _timing_summary(items) for route, items in sorted(per_route.items())},
    }


def run_audit(base_url: str, warm_samples: int = MIN_WARM_SAMPLES,
              timeout: float = 10.0, cold_timeout: float = 120.0) -> dict[str, Any]:
    base_url = normalize_base_url(base_url)
    if warm_samples < MIN_WARM_SAMPLES:
        raise ValueError(f"warm_samples must be at least {MIN_WARM_SAMPLES}")
    started = time.perf_counter()
    routes = [
        profile_route(
            base_url,
            route,
            warm_samples,
            timeout,
            cold_timeout if index == 0 else timeout,
        )
        for index, route in enumerate(PRIMARY_ROUTES)
    ]
    concurrency = run_concurrency_audit(base_url, timeout)
    route_errors = sum(
        route["coldError"] is not None
        or route["warmErrorCount"]
        or route["status"] != 200
        or route["warmStatusCounts"] != {"200": warm_samples}
        for route in routes
    )
    concurrency_errors = 0 if concurrency["skipped"] else concurrency["errorCount"]
    concurrency_status_ok = concurrency["skipped"] or concurrency["statusCounts"] == {"200": CONCURRENCY_REQUESTS}
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "baseUrl": base_url,
        "primaryRouteCount": len(PRIMARY_ROUTES),
        "warmSampleCountPerRoute": warm_samples,
        "timeoutSeconds": timeout,
        "firstColdTimeoutSeconds": cold_timeout,
        "routes": routes,
        "concurrency": concurrency,
        "durationSeconds": round(time.perf_counter() - started, 3),
        "success": route_errors == 0 and concurrency_errors == 0 and concurrency_status_ok,
    }


def _cell(value: Any) -> str:
    if value is None:
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Final performance audit",
        "",
        f"- Generated: {_cell(report['generatedAt'])}",
        f"- Base URL: `{_cell(report['baseUrl'])}`",
        f"- Warm samples per route: {report['warmSampleCountPerRoute']}",
        f"- Result: **{'PASS' if report['success'] else 'FAIL'}**",
        "",
        "## Primary routes",
        "",
        "| Route | Status | Content type | Bytes | Cold ms | Warm median ms | Warm p95 ms | Links | Articles | Sections | Gzip | Cache-Control |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for route in report["routes"]:
        lines.append(
            "| " + " | ".join(
                _cell(value)
                for value in (
                    f"`{route['route']}`",
                    route["status"],
                    route["contentType"],
                    route["bodyBytes"],
                    route["coldResponseMs"],
                    route["warmMedianMs"],
                    route["warmP95Ms"],
                    route["linkCount"],
                    route["articleCount"],
                    route["sectionCount"],
                    "yes" if route["gzipUsed"] else "no",
                    route["cacheHeaders"].get("cache-control"),
                )
            ) + " |"
        )

    concurrency = report["concurrency"]
    lines.extend(["", "## Mixed-route concurrency", ""])
    if concurrency["skipped"]:
        lines.append(f"Skipped: {_cell(concurrency['reason'])}")
    else:
        lines.extend(
            [
                f"- Workers: {concurrency['workers']}",
                f"- Requests: {concurrency['requestCount']}",
                f"- Errors: {concurrency['errorCount']}",
                f"- Median: {concurrency['medianMs']} ms",
                f"- P95: {concurrency['p95Ms']} ms",
                f"- Statuses: `{json.dumps(concurrency['statusCounts'], sort_keys=True)}`",
            ]
        )
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], json_output: Path, markdown_output: Path) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_output.write_text(render_markdown(report), encoding="utf-8")


def _warm_samples(value: str) -> int:
    samples = int(value)
    if samples < MIN_WARM_SAMPLES:
        raise argparse.ArgumentTypeError(f"must be at least {MIN_WARM_SAMPLES}")
    return samples


def _timeout(value: str) -> float:
    seconds = float(value)
    if not 0 < seconds <= 120:
        raise argparse.ArgumentTypeError("must be greater than 0 and no more than 120 seconds")
    return seconds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Profile fixed ColdChain Sentinel routes and write JSON/Markdown reports. "
            "The target server must already be running; links and external domains are never crawled."
        )
    )
    parser.add_argument("--base-url", required=True, help="HTTP(S) origin, for example http://127.0.0.1:8090")
    parser.add_argument("--warm-samples", type=_warm_samples, default=MIN_WARM_SAMPLES,
                        help=f"warm requests per route (minimum/default: {MIN_WARM_SAMPLES})")
    parser.add_argument("--timeout", type=_timeout, default=10.0,
                        help="per-request timeout after the first request (default: 10 seconds)")
    parser.add_argument("--cold-timeout", type=_timeout, default=120.0,
                        help="timeout for the first request only (default: 120 seconds)")
    parser.add_argument("--json-output", "--output-json", "--json-out", type=Path,
                        default=DEFAULT_JSON_OUTPUT, help=f"JSON report path (default: {DEFAULT_JSON_OUTPUT})")
    parser.add_argument("--markdown-output", "--output-markdown", "--markdown-out", type=Path,
                        default=DEFAULT_MARKDOWN_OUTPUT,
                        help=f"Markdown report path (default: {DEFAULT_MARKDOWN_OUTPUT})")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = run_audit(args.base_url, args.warm_samples, args.timeout, args.cold_timeout)
        write_reports(report, args.json_output, args.markdown_output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"JSON report: {args.json_output}")
    print(f"Markdown report: {args.markdown_output}")
    print(f"Result: {'PASS' if report['success'] else 'FAIL'}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
