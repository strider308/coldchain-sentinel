"""Bounded, same-origin route and link audit for local or live deployments."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_SEEDS = ("/", "/command-center")
DEFAULT_MANIFEST_PATHS = (
    "/command-center.json",
    "/final-route-manifest.json",
    "/screenshot-route-map.json",
    "/submission-readiness.json",
)
DEFAULT_SERVER_SOURCES = ("src/serve_dashboard.py", "src/serve_dashboard_amd.py")
DEFAULT_EDGE_EXPECTATIONS = (
    ("/unknown", 404, "text/html"),
    ("/unknown.json", 404, "application/json"),
    ("/cases/unknown-case/behavior-prediction.json", 404, "application/json"),
    ("/cases/unknown-case/inspection-plan.json", 404, "application/json"),
    ("/fault-atlas/unknown-fault.json", 404, "application/json"),
    ("/case-walkthroughs/unknown-case", 404, "text/html"),
    ("/case-walkthroughs/unknown-case.json", 404, "application/json"),
    ("/%2e%2e/", 404, "text/html"),
    ("/..%2f", 404, "text/html"),
    ("/%3Cscript%3Ealert(1)%3C/script%3E", 404, "text/html"),
    ("/a%0d%0aInjected-Header:test", 404, "text/html"),
    ("//command-center", 404, "text/html"),
    ("/COMMAND-CENTER", 404, "text/html"),
    ("/command-center/", 404, "text/html"),
    ("/command-center?test=1", 200, "text/html"),
    ("/" + "a" * 9000, 414, "text/html"),
    ("/cases//blocked-unresolved-pallet", 404, "text/html"),
    ("/cases/blocked-unresolved-pallet/review/", 404, "text/html"),
    ("/scenario-lab//door-open-warming.json", 404, "application/json"),
    ("/cases//door-open-warming/fireworks-advisory.json", 404, "application/json"),
    ("/case-walkthroughs//door-open-warming", 404, "text/html"),
    ("/cases/unknown-case/risk-timeline.json", 404, "application/json"),
    ("/cases/unknown-case/consensus-report.json", 404, "application/json"),
    ("/cases/unknown-case/quality-events.json", 404, "application/json"),
    ("/cases/unknown-case/raw-sensor-window.json", 404, "application/json"),
    ("/cases/blocked-unresolved-pallet/sensor-window.json?offset=-1", 400, "application/json"),
    ("/cases/blocked-unresolved-pallet/sensor-window.json?limit=0", 400, "application/json"),
    ("/cases/blocked-unresolved-pallet/raw-sensor-window.json?offset=oops", 400, "application/json"),
    ("/cases/blocked-unresolved-pallet/rejected-readings.json?limit=0", 400, "application/json"),
)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class RouteHTMLParser(HTMLParser):
    """Collect hrefs and fragment targets without interpreting page scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        for name, value in attrs:
            name = name.lower()
            if name == "href" and value is not None:
                self.hrefs.append(value)
            if name == "id" and value:
                self.ids.append(value)
            if tag == "a" and name == "name" and value:
                self.ids.append(value)

    handle_startendtag = handle_starttag


def _origin(url: str) -> tuple[str, str, int]:
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValueError("base URL must be an absolute HTTP(S) URL")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URLs containing credentials are not supported")
    try:
        port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise ValueError("base URL has an invalid port") from exc
    return parts.scheme.lower(), parts.hostname.lower(), port


def normalize_base_url(base_url: str) -> str:
    """Return a canonical origin URL ending in a slash."""

    scheme, _, _ = _origin(base_url)
    parts = urlsplit(base_url)
    return urlunsplit((scheme, parts.netloc.lower(), "/", "", ""))


def normalize_internal_href(base_url: str, source_url: str, href: str) -> tuple[str, str] | None:
    """Resolve an href and return ``(URL without fragment, decoded fragment)``.

    ``None`` means the reference is empty, unsafe, unsupported, or external.
    """

    href = href.strip()
    if not href or _CONTROL.search(href):
        return None
    joined = urljoin(source_url, href)
    parts = urlsplit(joined)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    try:
        if _origin(joined) != _origin(base_url):
            return None
    except ValueError:
        return None
    base = urlsplit(normalize_base_url(base_url))
    target = urlunsplit((base.scheme, base.netloc, parts.path or "/", parts.query, ""))
    return target, unquote(parts.fragment)


def _route_literal(value: Any) -> str | None:
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        return None
    if _CONTROL.search(value) or any(char.isspace() for char in value):
        return None
    parts = urlsplit(value)
    return parts.path if not parts.scheme and not parts.netloc and parts.path.startswith("/") else None


def extract_manifest_route_entries(payload: Any) -> list[dict[str, Any]]:
    """Find exact route-like JSON strings and identify route-map members."""

    found: list[dict[str, Any]] = []

    def visit(value: Any, pointer: str, in_route_map: bool, expected_404: bool) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                escaped = str(key).replace("~", "~0").replace("/", "~1")
                normalized_key = re.sub(r"[-_]", "", str(key).lower())
                visit(
                    child,
                    f"{pointer}/{escaped}",
                    in_route_map or normalized_key.endswith("routemap"),
                    expected_404 or "expected404" in normalized_key,
                )
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{pointer}/{index}", in_route_map, expected_404)
        else:
            route = _route_literal(value)
            if route:
                found.append({"route": route, "pointer": pointer, "routeMap": in_route_map, "expected404": expected_404})

    visit(payload, "$", False, False)
    return sorted(found, key=lambda item: (item["route"], item["pointer"]))


def _literal_routes(node: ast.AST, variables: dict[str, set[str]]) -> set[str]:
    if isinstance(node, ast.Constant):
        route = _route_literal(node.value)
        return {route} if route else set()
    if isinstance(node, ast.Name):
        return set(variables.get(node.id, ()))
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return set().union(*(_literal_routes(item, variables) for item in node.elts)) if node.elts else set()
    if isinstance(node, ast.Dict):
        keys = _literal_routes_list(node.keys, variables)
        return set().union(*keys) if keys else set()
    return set()


def _literal_routes_list(nodes: Iterable[ast.AST | None], variables: dict[str, set[str]]) -> list[set[str]]:
    return [_literal_routes(node, variables) for node in nodes if node is not None]


def _is_path_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "path" or node.id.endswith("_path")
    return isinstance(node, ast.Attribute) and node.attr == "path"


def extract_server_route_inventory(source_files: Iterable[str | Path]) -> dict[str, Any]:
    """Extract literal dispatch routes and dynamic prefixes from Python ASTs."""

    exact: set[str] = set()
    prefixes: set[str] = set()
    errors: list[str] = []
    used_sources: list[str] = []
    for source_file in source_files:
        path = Path(source_file)
        used_sources.append(str(path))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            errors.append(f"{path}: {exc}")
            continue

        variables: dict[str, set[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                routes = _literal_routes(node.value, variables)
                for target in node.targets:
                    if isinstance(target, ast.Name) and routes:
                        variables[target.id] = routes
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
                routes = _literal_routes(node.value, variables)
                if routes:
                    variables[node.target.id] = routes

        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                operands = [node.left, *node.comparators]
                for index, operator in enumerate(node.ops):
                    left, right = operands[index], operands[index + 1]
                    if isinstance(operator, (ast.Eq, ast.In)) and _is_path_expression(left):
                        exact.update(_literal_routes(right, variables))
                    if isinstance(operator, ast.Eq) and _is_path_expression(right):
                        exact.update(_literal_routes(left, variables))
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "startswith"
                and _is_path_expression(node.func.value)
                and node.args
            ):
                prefixes.update(_literal_routes(node.args[0], variables))

    return {
        "sourceFiles": used_sources,
        "literalRoutes": sorted(exact),
        "dynamicPrefixes": sorted(prefixes),
        "errors": errors,
    }


def _route_is_dispatched(route: str, inventory: dict[str, Any]) -> bool:
    return route in inventory["literalRoutes"] or any(route.startswith(prefix) for prefix in inventory["dynamicPrefixes"])


class _BlockedRedirect(RuntimeError):
    pass


class _SameOriginRedirectHandler(HTTPRedirectHandler):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.redirects: list[dict[str, Any]] = []

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        target = urljoin(req.full_url, newurl)
        normalized = normalize_internal_href(self.base_url, req.full_url, target)
        entry = {"source": req.full_url, "target": target, "status": code, "blocked": normalized is None}
        self.redirects.append(entry)
        if normalized is None:
            raise _BlockedRedirect(f"external or invalid redirect blocked: {target}")
        return super().redirect_request(req, fp, code, msg, headers, normalized[0])


@dataclass
class _FetchResult:
    url: str
    method: str = "GET"
    status: int = 0
    final_url: str = ""
    content_type: str = ""
    mime_type: str = ""
    charset: str = "utf-8"
    body: bytes = b""
    redirects: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    truncated: bool = False

    def text(self) -> str:
        return self.body.decode(self.charset or "utf-8", errors="replace")

    def public(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "finalUrl": self.final_url or self.url,
            "contentType": self.content_type,
            "bytesRead": len(self.body),
            "truncated": self.truncated,
            "error": self.error,
        }


def _provider_safe_head(url: str) -> bool:
    path = urlsplit(url).path
    return path in {"/ai-review", "/ai-review.json"} or (
        path.startswith("/cases/") and path.endswith("/fireworks-advisory.json")
    )


def _fetch(url: str, base_url: str, timeout: float, max_body_bytes: int) -> _FetchResult:
    redirect_handler = _SameOriginRedirectHandler(base_url)
    opener = build_opener(redirect_handler)
    method = "HEAD" if _provider_safe_head(url) else "GET"
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/json,text/plain;q=0.9,*/*;q=0.1",
            "Accept-Encoding": "identity",
            "User-Agent": "ColdChainSentinel-FinalRouteAudit/1.0",
        },
        method=method,
    )
    result = _FetchResult(url=url, method=method)
    response: Any = None
    try:
        try:
            response = opener.open(request, timeout=timeout)
        except HTTPError as exc:
            response = exc
        result.status = int(response.getcode())
        result.final_url = response.geturl()
        result.content_type = response.headers.get("Content-Type", "")
        result.mime_type = result.content_type.split(";", 1)[0].strip().lower()
        result.charset = response.headers.get_content_charset() or "utf-8"
        data = response.read(max_body_bytes + 1)
        result.truncated = len(data) > max_body_bytes
        result.body = data[:max_body_bytes]
    except (_BlockedRedirect, URLError, OSError, ValueError) as exc:
        result.error = str(getattr(exc, "reason", exc))
    finally:
        if response is not None:
            response.close()
        result.redirects = redirect_handler.redirects
    return result


def _content_type_issue(result: _FetchResult) -> str | None:
    path = urlsplit(result.url).path.lower()
    mime = result.mime_type
    if path.endswith(".json") and mime != "application/json":
        return "JSON route did not return application/json"
    if path.endswith(".ps1") and mime != "text/plain":
        return "PowerShell route did not return text/plain"
    if path.endswith(".html") and mime != "text/html":
        return "HTML route did not return text/html"
    if result.method != "HEAD" and mime == "application/json":
        try:
            json.loads(result.text())
        except (json.JSONDecodeError, UnicodeError):
            return "application/json response was not valid JSON"
    looks_html = result.method != "HEAD" and bool(
        re.match(r"\s*(?:<!doctype\s+html|<html|<main|<header)", result.text(), re.I)
    )
    if looks_html and mime != "text/html":
        return "HTML-shaped response did not return text/html"
    return None


def audit_routes(
    base_url: str,
    *,
    seeds: Iterable[str] | None = None,
    manifest_paths: Iterable[str] | None = None,
    server_sources: Iterable[str | Path] | None = None,
    timeout: float = 5.0,
    max_workers: int = 4,
    max_pages: int = 500,
    max_body_bytes: int = 2_000_000,
) -> dict[str, Any]:
    """Crawl internal links and compare manifests with source dispatch literals."""

    if not 0.1 <= timeout <= 30:
        raise ValueError("timeout must be between 0.1 and 30 seconds")
    if not 1 <= max_workers <= 8:
        raise ValueError("max_workers must be between 1 and 8")
    if not 1 <= max_pages <= 2_000:
        raise ValueError("max_pages must be between 1 and 2000")
    if not 1_024 <= max_body_bytes <= 5_000_000:
        raise ValueError("max_body_bytes must be between 1024 and 5000000")

    started = datetime.now(timezone.utc)
    base_url = normalize_base_url(base_url)
    seed_paths = tuple(DEFAULT_SEEDS if seeds is None else seeds)
    manifests = tuple(DEFAULT_MANIFEST_PATHS if manifest_paths is None else manifest_paths)
    inventory = extract_server_route_inventory(DEFAULT_SERVER_SOURCES if server_sources is None else server_sources)
    manifest_path_set = {_route_literal(path) for path in manifests} - {None}

    frontier: deque[str] = deque()
    queued: set[str] = set()

    def enqueue(href: str, source: str = base_url) -> None:
        normalized = normalize_internal_href(base_url, source, href)
        if normalized and normalized[0] not in queued:
            queued.add(normalized[0])
            frontier.append(normalized[0])

    for path in (*seed_paths, *manifests):
        enqueue(path)

    results: dict[str, _FetchResult] = {}
    html_parsers: dict[str, RouteHTMLParser] = {}
    link_references: list[dict[str, Any]] = []
    external_links: list[dict[str, str]] = []
    duplicate_ids: list[dict[str, Any]] = []
    content_type_issues: list[dict[str, str]] = []
    manifest_records: list[dict[str, Any]] = []
    manifest_entries: list[dict[str, Any]] = []
    manifest_expected_404: set[str] = set()

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="route-audit") as executor:
        while frontier and len(results) < max_pages:
            remaining = max_pages - len(results)
            batch = [frontier.popleft() for _ in range(min(max_workers, remaining, len(frontier)))]
            fetched = list(executor.map(lambda url: _fetch(url, base_url, timeout, max_body_bytes), batch))
            for result in fetched:
                results[result.url] = result
                if result.status and (issue := _content_type_issue(result)):
                    content_type_issues.append({"url": result.url, "issue": issue, "contentType": result.content_type})

                if result.method == "GET" and result.status < 400 and result.mime_type == "text/html":
                    parser = RouteHTMLParser()
                    parser.feed(result.text())
                    parser.close()
                    html_parsers[result.url] = parser
                    for identifier, count in Counter(parser.ids).items():
                        if count > 1:
                            duplicate_ids.append({"url": result.url, "id": identifier, "count": count})
                    document_url = result.final_url or result.url
                    for href in parser.hrefs:
                        normalized = normalize_internal_href(base_url, document_url, href)
                        if normalized is None:
                            joined = urljoin(document_url, href.strip())
                            if urlsplit(joined).scheme.lower() in {"http", "https"}:
                                external_links.append({"source": result.url, "href": href, "resolved": joined})
                            continue
                        target, fragment = normalized
                        link_references.append(
                            {
                                "source": result.url,
                                "href": href,
                                "target": target,
                                "fragment": fragment,
                                "fragmentOnly": href.strip().startswith("#"),
                            }
                        )
                        enqueue(target, document_url)

                if urlsplit(result.url).path in manifest_path_set:
                    record: dict[str, Any] = {"url": result.url, "status": result.status, "routes": 0, "routeMapRoutes": 0}
                    if result.status < 400 and result.mime_type == "application/json":
                        try:
                            entries = extract_manifest_route_entries(json.loads(result.text()))
                        except json.JSONDecodeError as exc:
                            record["error"] = f"invalid JSON: {exc}"
                        else:
                            record["routes"] = len(entries)
                            record["routeMapRoutes"] = sum(bool(entry["routeMap"]) for entry in entries)
                            for entry in entries:
                                enriched = {**entry, "manifest": result.url}
                                manifest_entries.append(enriched)
                                if entry["expected404"]:
                                    manifest_expected_404.add(entry["route"])
                                else:
                                    enqueue(entry["route"])
                    else:
                        record["error"] = result.error or f"unexpected status/content type: {result.status} {result.content_type}"
                    manifest_records.append(record)

    broken_urls = [result.public() for result in results.values() if result.error or result.status >= 400 or not result.status]
    unchecked_links: list[dict[str, Any]] = []
    broken_links: list[dict[str, Any]] = []
    fragment_issues: list[dict[str, Any]] = []
    fragment_not_checked: list[dict[str, Any]] = []
    for reference in link_references:
        target_result = results.get(reference["target"])
        if target_result is None:
            unchecked_links.append(reference)
            continue
        if target_result.error or target_result.status >= 400 or not target_result.status:
            broken_links.append({**reference, "status": target_result.status, "error": target_result.error})
            continue
        if reference["fragment"]:
            parser = html_parsers.get(reference["target"])
            if parser is None:
                fragment_not_checked.append({**reference, "reason": "target is not parsed HTML"})
            elif reference["fragment"] not in set(parser.ids):
                fragment_issues.append({**reference, "issue": "fragment target ID not found"})

    references_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reference in link_references:
        references_by_target[reference["target"]].append(reference)
    duplicate_link_references = [
        {"target": target, "count": len(references), "sources": sorted({item["source"] for item in references})}
        for target, references in sorted(references_by_target.items())
        if len(references) > 1
    ]
    final_url_groups: dict[str, list[str]] = defaultdict(list)
    for result in results.values():
        final_url_groups[result.final_url or result.url].append(result.url)
    duplicate_final_urls = [
        {"finalUrl": final_url, "requestedUrls": sorted(urls)}
        for final_url, urls in sorted(final_url_groups.items())
        if len(urls) > 1
    ]

    manifest_routes = sorted({entry["route"] for entry in manifest_entries if not entry["expected404"]})
    route_map_entries = [entry for entry in manifest_entries if entry["routeMap"] and not entry["expected404"]]

    def runtime_route_ok(route: str) -> bool:
        normalized = normalize_internal_href(base_url, base_url, route)
        result = results.get(normalized[0]) if normalized else None
        return bool(result and not result.error and 0 < result.status < 400)

    stale_route_map_entries = [
        entry for entry in route_map_entries
        if not _route_is_dispatched(entry["route"], inventory) and not runtime_route_ok(entry["route"])
    ]
    missing_manifest_routes = [
        entry for entry in manifest_entries
        if not entry["expected404"]
        and not _route_is_dispatched(entry["route"], inventory)
        and not runtime_route_ok(entry["route"])
    ]
    represented = {
        urlsplit(url).path
        for url in [*queued, *(entry["route"] for entry in manifest_entries)]
        if urlsplit(url).path
    }
    server_routes_not_represented = sorted(set(inventory["literalRoutes"]) - represented)
    redirects = [redirect for result in results.values() for redirect in result.redirects]
    truncated_crawl = bool(frontier)

    edge_expectations = list(DEFAULT_EDGE_EXPECTATIONS)
    known_edge_paths = {path for path, _, _ in edge_expectations}
    edge_expectations.extend(
        (path, 404, "application/json" if path.endswith(".json") else "text/html")
        for path in sorted(manifest_expected_404 - known_edge_paths)
    )

    def edge_url(path: str) -> str:
        base = urlsplit(base_url)
        return urlunsplit((base.scheme, base.netloc, path.split("?", 1)[0], path.split("?", 1)[1] if "?" in path else "", ""))

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="edge-audit") as executor:
        edge_results = list(executor.map(lambda item: _fetch(edge_url(item[0]), base_url, timeout, max_body_bytes), edge_expectations))
    edge_checks = []
    for (path, expected_status, expected_type), result in zip(edge_expectations, edge_results):
        display_path = path if len(path) <= 160 else f"/<{len(path) - 1} repeated characters>"
        edge_checks.append({
            "path": display_path,
            "expectedStatus": expected_status,
            "actualStatus": result.status,
            "expectedContentType": expected_type,
            "actualContentType": result.mime_type,
            "error": result.error,
            "passed": result.error is None and result.status == expected_status and result.mime_type == expected_type,
        })
    edge_mismatches = [check for check in edge_checks if not check["passed"]]
    blocking = (
        len(broken_urls) + len(content_type_issues) + len(fragment_issues) + len(unchecked_links)
        + len(duplicate_ids) + len(edge_mismatches) + int(truncated_crawl)
    )

    summary = {
        "urlsRequested": len(results),
        "htmlPagesCrawled": len(html_parsers),
        "linkReferencesChecked": len(link_references) - len(unchecked_links),
        "uniqueInternalLinkTargets": len(references_by_target),
        "brokenUrls": len(broken_urls),
        "brokenLinkReferences": len(broken_links),
        "uncheckedLinkReferences": len(unchecked_links),
        "redirects": len(redirects),
        "contentTypeIssues": len(content_type_issues),
        "fragmentIssues": len(fragment_issues),
        "duplicateLinkTargets": len(duplicate_link_references),
        "duplicateIds": len(duplicate_ids),
        "externalLinksIgnored": len(external_links),
        "manifestRoutes": len(manifest_routes),
        "staleRouteMapEntries": len(stale_route_map_entries),
        "manifestRoutesMissingFromServer": len(missing_manifest_routes),
        "serverRoutesNotRepresented": len(server_routes_not_represented),
        "edgeStatusChecks": len(edge_checks),
        "edgeStatusMismatches": len(edge_mismatches),
        "blockingFindings": blocking,
    }
    return {
        "schemaVersion": 1,
        "baseUrl": base_url,
        "startedAtUtc": started.isoformat(),
        "finishedAtUtc": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "timeoutSeconds": timeout,
            "maxWorkers": max_workers,
            "maxPages": max_pages,
            "maxBodyBytes": max_body_bytes,
            "seeds": list(seed_paths),
            "manifestPaths": list(manifests),
        },
        "ok": blocking == 0,
        "crawlTruncated": truncated_crawl,
        "summary": summary,
        "pages": [results[url].public() for url in sorted(results)],
        "linkReferences": link_references,
        "brokenUrls": broken_urls,
        "brokenLinks": broken_links,
        "uncheckedLinks": unchecked_links,
        "redirects": redirects,
        "contentTypeIssues": content_type_issues,
        "fragmentIssues": fragment_issues,
        "fragmentChecksSkipped": fragment_not_checked,
        "duplicateLinkReferences": duplicate_link_references,
        "duplicateFinalUrls": duplicate_final_urls,
        "duplicateIds": duplicate_ids,
        "externalLinksIgnored": external_links,
        "manifests": manifest_records,
        "manifestRouteEntries": manifest_entries,
        "manifestRoutes": manifest_routes,
        "routeInventory": inventory,
        "staleRouteMapEntries": stale_route_map_entries,
        "manifestRoutesMissingFromServer": missing_manifest_routes,
        "serverRoutesNotRepresented": server_routes_not_represented,
        "edgeStatusChecks": edge_checks,
        "edgeStatusMismatches": edge_mismatches,
    }


def _md_escape(value: Any) -> str:
    return str(value if value not in (None, "") else "-").replace("|", "\\|").replace("\n", " ")


def _md_table(rows: Iterable[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    rows = list(rows)
    if not rows:
        return "None detected.\n"
    header = "| " + " | ".join(label for _, label in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(_md_escape(row.get(key)) for key, _ in columns) + " |" for row in rows]
    return "\n".join([header, divider, *body]) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    """Render a concise, evidence-oriented Markdown audit report."""

    summary_rows = [{"metric": key, "value": value} for key, value in report["summary"].items()]
    missing_rows = [
        {"route": item["route"], "manifest": item["manifest"], "pointer": item["pointer"]}
        for item in report["manifestRoutesMissingFromServer"]
    ]
    return "\n".join(
        [
            "# Final Route and Link Integrity Audit",
            "",
            f"- Base URL: `{report['baseUrl']}`",
            f"- Completed UTC: `{report['finishedAtUtc']}`",
            f"- Crawl result: `{'PASS' if report['ok'] else 'FINDINGS'}`",
            "- Scope: bounded same-origin HTTP crawl plus static literal-route comparison.",
            "",
            "## Summary",
            "",
            _md_table(summary_rows, [("metric", "Metric"), ("value", "Value")]).rstrip(),
            "",
            "## Broken or Unreachable URLs",
            "",
            _md_table(report["brokenUrls"], [("url", "URL"), ("status", "Status"), ("error", "Error")]).rstrip(),
            "",
            "## Redirects",
            "",
            _md_table(report["redirects"], [("source", "Source"), ("status", "Status"), ("target", "Target"), ("blocked", "Blocked")]).rstrip(),
            "",
            "## Content-Type Findings",
            "",
            _md_table(report["contentTypeIssues"], [("url", "URL"), ("contentType", "Content-Type"), ("issue", "Finding")]).rstrip(),
            "",
            "## Fragment Findings",
            "",
            _md_table(report["fragmentIssues"], [("source", "Source"), ("href", "Reference"), ("issue", "Finding")]).rstrip(),
            "",
            "## Manifest Routes Missing from Literal Dispatch Inventory",
            "",
            _md_table(missing_rows, [("route", "Route"), ("manifest", "Manifest"), ("pointer", "JSON Pointer")]).rstrip(),
            "",
            "## Expected 404 and Malformed-Path Checks",
            "",
            _md_table(report["edgeStatusChecks"], [("path", "Path"), ("expectedStatus", "Expected"), ("actualStatus", "Actual"), ("actualContentType", "Content type"), ("passed", "Pass")]).rstrip(),
            "",
            "## Literal Server Routes Not Represented by the Crawl or Manifests",
            "",
            "\n".join(f"- `{route}`" for route in report["serverRoutesNotRepresented"]) or "None detected.",
            "",
            "## Limitations",
            "",
            "Dynamic dispatch is represented by literal `startswith` prefixes. Runtime-generated routes that have neither a literal route nor a literal prefix require manual review.",
            "",
        ]
    )


def write_reports(report: dict[str, Any], json_path: str | Path, markdown_path: str | Path) -> None:
    json_path, markdown_path = Path(json_path), Path(markdown_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def _bounded_number(raw: str, minimum: float, maximum: float, name: str, cast: type = int) -> Any:
    try:
        value = cast(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise argparse.ArgumentTypeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _default_output_kind(base_url: str) -> str:
    host = (urlsplit(base_url).hostname or "").lower()
    return "local" if host in {"localhost", "127.0.0.1", "::1"} else "live"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Local or live application base URL")
    parser.add_argument("--seed", action="append", dest="seeds", help="Additional/override crawl seed; repeatable")
    parser.add_argument("--manifest", action="append", dest="manifests", help="Key JSON manifest path; repeatable")
    parser.add_argument("--server-source", action="append", dest="server_sources", help="Python server source; repeatable")
    parser.add_argument("--timeout", type=lambda value: _bounded_number(value, 0.1, 30, "timeout", float), default=5.0)
    parser.add_argument("--workers", type=lambda value: _bounded_number(value, 1, 8, "workers"), default=4)
    parser.add_argument("--max-pages", type=lambda value: _bounded_number(value, 1, 2_000, "max-pages"), default=500)
    parser.add_argument("--max-body-bytes", type=lambda value: _bounded_number(value, 1_024, 5_000_000, "max-body-bytes"), default=2_000_000)
    parser.add_argument("--json-output", "--json-out", dest="json_output")
    parser.add_argument("--markdown-output", "--markdown-out", dest="markdown_output")
    args = parser.parse_args(argv)

    kind = _default_output_kind(args.base_url)
    json_output = args.json_output or f"submission-work/final-audit/route-audit-{kind}.json"
    markdown_output = args.markdown_output or (
        "docs/FINAL_ROUTE_AND_LINK_INTEGRITY_AUDIT.md"
        if kind == "local"
        else "submission-work/final-audit/route-audit-live.md"
    )
    try:
        report = audit_routes(
            args.base_url,
            seeds=args.seeds,
            manifest_paths=args.manifests,
            server_sources=args.server_sources,
            timeout=args.timeout,
            max_workers=args.workers,
            max_pages=args.max_pages,
            max_body_bytes=args.max_body_bytes,
        )
    except ValueError as exc:
        parser.error(str(exc))
    write_reports(report, json_output, markdown_output)
    print(json.dumps({"ok": report["ok"], **report["summary"]}, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
