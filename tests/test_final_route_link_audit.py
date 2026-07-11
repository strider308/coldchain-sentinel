import json
import sys
import threading
import unittest
from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from final_route_link_audit import (
    RouteHTMLParser,
    audit_routes,
    extract_manifest_route_entries,
    extract_server_route_inventory,
    normalize_internal_href,
    write_reports,
)


class _FakeHandler(BaseHTTPRequestHandler):
    requests: list[str] = []
    methods: list[tuple[str, str]] = []

    def do_GET(self):  # noqa: N802 - stdlib handler API
        type(self).requests.append(self.path)
        type(self).methods.append(("GET", self.path))
        path = self.path.split("?", 1)[0]
        if path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/page")
            self.end_headers()
            return
        if path == "/outside":
            self.send_response(302)
            self.send_header("Location", "https://example.invalid/blocked")
            self.end_headers()
            return
        if path == "/manifest.json":
            self._send(
                "application/json",
                json.dumps(
                    {
                        "routeMap": {"home": "/", "page": "/page", "stale": "/missing"},
                        "requiredRoutes": ["/redirect", "/relative"],
                    }
                ),
            )
            return
        if path == "/bad.json":
            self._send("text/html", "<html><main>wrong type</main></html>")
            return
        if path == "/":
            self._send(
                "text/html",
                '<html><body id="top"><a href="/page#section">Page</a>'
                '<a href="/page#section">Page again</a><a href="relative">Relative</a>'
                '<a href="#top">Top</a><a href="/redirect">Redirect</a>'
                '<a href="/ai-review.json">Provider-safe HEAD</a>'
                '<a href="https://example.invalid/not-crawled">External</a></body></html>',
            )
            return
        if path == "/page":
            self._send("text/html", '<html><main id="section"><a href="/">Home</a></main></html>')
            return
        if path == "/relative":
            self._send("text/html", '<html><main id="relative">Relative</main></html>')
            return
        if path == "/duplicate":
            self._send("text/html", '<html><main id="same" id="same">Duplicate</main></html>')
            return
        self._send("text/html", '<html><main><a href="/">Home</a></main></html>', 404)

    def do_HEAD(self):  # noqa: N802 - stdlib handler API
        type(self).methods.append(("HEAD", self.path))
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send(self, content_type: str, body: str, status: int = 200):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _format, *args):
        pass


@contextmanager
def _server():
    _FakeHandler.requests = []
    _FakeHandler.methods = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class RouteAuditHelperTests(unittest.TestCase):
    def test_html_parser_and_href_normalization(self):
        parser = RouteHTMLParser()
        parser.feed('<main id="one"><a name="legacy" href="../next?q=1#frag">Next</a><p id="one"></p></main>')
        self.assertEqual(parser.hrefs, ["../next?q=1#frag"])
        self.assertEqual(Counter(parser.ids), Counter({"one": 2, "legacy": 1}))

        base = "http://example.test:8080/"
        self.assertEqual(
            normalize_internal_href(base, f"{base}a/page", "../next?q=1#frag"),
            (f"{base}next?q=1", "frag"),
        )
        self.assertEqual(normalize_internal_href(base, f"{base}a/page", "#one"), (f"{base}a/page", "one"))
        self.assertIsNone(normalize_internal_href(base, f"{base}a/page", "//other.test/path"))
        self.assertIsNone(normalize_internal_href(base, f"{base}a/page", "javascript:alert(1)"))

        duplicate_attribute = RouteHTMLParser()
        duplicate_attribute.feed('<main id="same" id="same"></main>')
        self.assertEqual(duplicate_attribute.ids, ["same", "same"])

    def test_manifest_and_literal_dispatch_extraction(self):
        entries = extract_manifest_route_entries(
            {"routeMap": {"home": "/", "detail": "/dynamic/item?q=1#part"}, "copy": "visit /not-a-route later"}
        )
        self.assertEqual({item["route"] for item in entries}, {"/", "/dynamic/item"})
        self.assertTrue(all(item["routeMap"] for item in entries))

        with TemporaryDirectory() as directory:
            source = Path(directory) / "server.py"
            source.write_text(
                "routes = {'/', '/page'}\n"
                "def dispatch(path):\n"
                "    navigation = '/not-dispatch'\n"
                "    if path in routes: return 1\n"
                "    if path == '/exact': return 2\n"
                "    if path.startswith('/dynamic/'): return 3\n",
                encoding="utf-8",
            )
            inventory = extract_server_route_inventory([source])
        self.assertEqual(inventory["literalRoutes"], ["/", "/exact", "/page"])
        self.assertEqual(inventory["dynamicPrefixes"], ["/dynamic/"])
        self.assertEqual(inventory["errors"], [])


class RouteAuditIntegrationTests(unittest.TestCase):
    def test_duplicate_ids_are_blocking(self):
        with _server() as base, patch("final_route_link_audit.DEFAULT_EDGE_EXPECTATIONS", ()):
            report = audit_routes(
                base,
                seeds=["/duplicate"],
                manifest_paths=[],
                server_sources=[],
                timeout=2,
                max_workers=1,
                max_pages=2,
            )
        self.assertEqual(report["summary"]["duplicateIds"], 1)
        self.assertEqual(report["summary"]["blockingFindings"], 1)
        self.assertFalse(report["ok"])

    def test_bounded_same_origin_crawl_manifest_comparison_and_reports(self):
        with TemporaryDirectory() as directory, _server() as base:
            source = Path(directory) / "server.py"
            source.write_text(
                "routes = {'/', '/page', '/relative', '/redirect', '/manifest.json', '/orphan'}\n"
                "def dispatch(path):\n"
                "    if path in routes: return True\n",
                encoding="utf-8",
            )
            report = audit_routes(
                base,
                seeds=["/"],
                manifest_paths=["/manifest.json"],
                server_sources=[source],
                timeout=2,
                max_workers=2,
                max_pages=20,
            )
            json_output = Path(directory) / "audit.json"
            markdown_output = Path(directory) / "audit.md"
            write_reports(report, json_output, markdown_output)

            self.assertGreaterEqual(report["summary"]["htmlPagesCrawled"], 3)
            self.assertEqual(report["summary"]["externalLinksIgnored"], 1)
            self.assertTrue(any(item["target"].endswith("/page") for item in report["duplicateLinkReferences"]))
            self.assertTrue(any(item["target"].endswith("/page") for item in report["redirects"]))
            self.assertEqual(report["fragmentIssues"], [])
            self.assertEqual({item["route"] for item in report["staleRouteMapEntries"]}, {"/missing"})
            self.assertEqual({item["route"] for item in report["manifestRoutesMissingFromServer"]}, {"/missing"})
            self.assertIn("/orphan", report["serverRoutesNotRepresented"])
            self.assertTrue(json.loads(json_output.read_text(encoding="utf-8"))["baseUrl"].startswith(base))
            self.assertIn("# Final Route and Link Integrity Audit", markdown_output.read_text(encoding="utf-8"))
            self.assertFalse(any("example.invalid" in request for request in _FakeHandler.requests))
            self.assertIn(("HEAD", "/ai-review.json"), _FakeHandler.methods)
            self.assertNotIn(("GET", "/ai-review.json"), _FakeHandler.methods)

    def test_content_type_and_external_redirect_fail_closed(self):
        with _server() as base:
            report = audit_routes(
                base,
                seeds=["/bad.json", "/outside"],
                manifest_paths=[],
                server_sources=[],
                timeout=2,
                max_workers=2,
                max_pages=4,
            )
        self.assertEqual(report["summary"]["contentTypeIssues"], 1)
        self.assertTrue(any(item["blocked"] for item in report["redirects"]))
        self.assertTrue(any(item["url"].endswith("/outside") and item["error"] for item in report["brokenUrls"]))


if __name__ == "__main__":
    unittest.main()
