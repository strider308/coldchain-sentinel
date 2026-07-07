"""Stdlib-only ColdChain Sentinel dashboard and review packet."""

from __future__ import annotations

import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ai_review_assistant import build_ai_review
from coldchain_baseline import build_review_packet, evaluate_case, load_fixture

HOST = "127.0.0.1"
PORT = 8080


def fmt_time(value: str) -> str:
    return value.replace("T", " ").replace(":00Z", " UTC")


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="badge badge-{tone}">{html.escape(text)}</span>'


def items(values: list[str], test_prefix: str) -> str:
    return "\n".join(
        f'<li data-testid="{html.escape(test_prefix)}-{html.escape(value)}">{html.escape(value)}</li>' for value in values
    )


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172026;
      --muted: #5c6870;
      --line: #d9e0e5;
      --panel: #f7f9fa;
      --accent: #146c5f;
      --warn: #9a4f00;
      --danger: #a32626;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: #fff; line-height: 1.45; }}
    header {{ padding: 28px clamp(16px, 4vw, 48px); border-bottom: 1px solid var(--line); background: var(--panel); }}
    main {{ width: min(1120px, 100%); margin: 0 auto; padding: 24px clamp(16px, 4vw, 32px) 40px; }}
    nav a {{ color: var(--accent); font-weight: 700; margin-right: 16px; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(28px, 4vw, 42px); }}
    h2 {{ margin: 0 0 12px; font-size: 20px; }}
    p {{ margin: 0 0 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 16px 0; }}
    .panel {{ border: 1px solid var(--line); border-radius: 8px; padding: 16px; background: #fff; }}
    .metric {{ font-size: 30px; font-weight: 700; margin: 4px 0; }}
    .muted {{ color: var(--muted); }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 13px; font-weight: 700; border: 1px solid var(--line); margin: 2px 4px 2px 0; }}
    .badge-good {{ color: var(--accent); background: #e9f7f4; }}
    .badge-warn {{ color: var(--warn); background: #fff3df; }}
    .badge-danger {{ color: var(--danger); background: #ffecec; }}
    ul {{ padding-left: 20px; margin: 8px 0 0; }}
    .status-block {{ border-left: 4px solid var(--danger); background: #fff6f6; }}
    .timeline {{ display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; }}
    .line {{ height: 3px; background: var(--line); }}
    .button {{ display: inline-block; border: 1px solid var(--accent); border-radius: 6px; padding: 8px 12px; color: #fff; background: var(--accent); text-decoration: none; font-weight: 700; }}
  </style>
</head>
<body>{body}</body>
</html>
"""


def render_dashboard(case: dict[str, Any] | None = None) -> str:
    case = case or load_fixture()
    result = evaluate_case(case)
    excursion = result["excursion"]
    mapped = result["mappedPalletIds"]
    unresolved = result["unresolvedPalletIds"]
    forbidden = case["reviewPolicy"]["autonomousActionsForbidden"]

    mapped_items = items(mapped, "mapped")
    unresolved_items = "\n".join(
        f'<li data-testid="unresolved-{html.escape(pallet_id)}">{html.escape(pallet_id)} because zone mapping is missing.</li>'
        for pallet_id in unresolved
    )
    forbidden_items = "\n".join(
        f'<li data-testid="forbidden-{html.escape(action)}">{html.escape(action.replace("_", " "))}</li>'
        for action in forbidden
    )
    blocker_items = "\n".join(
        f'<li data-testid="blocker-{html.escape(blocker)}">{html.escape(blocker.replace("_", " ").title())}</li>'
        for blocker in result["blockers"]
    )

    body = f"""
  <header data-testid="demo-overview">
    <h1>ColdChain Sentinel</h1>
    <p data-testid="synthetic-scope-note">Synthetic demo data only. Deterministic rules are authoritative.</p>
    <nav><a href="/">Dashboard</a><a href="/review" data-testid="review-packet-link">Review packet</a><a href="/ai-review" data-testid="ai-review-link">AI review</a><a href="/review.json">Review JSON</a></nav>
    {badge("Track 3 demo", "good")}{badge("Fireworks optional", "warn")}{badge("No production validation", "warn")}
  </header>
  <main>
    <section class="grid" aria-label="Shipment summary">
      <article class="panel" data-testid="shipment-dashboard">
        <h2>Shipment overview</h2>
        <p class="muted">Synthetic shipment</p>
        <p class="metric" data-testid="shipment-id">{html.escape(result["shipmentId"])}</p>
        <p>Temperature range: {case["shipment"]["temperatureRangeC"]["min"]} C to {case["shipment"]["temperatureRangeC"]["max"]} C.</p>
      </article>
      <article class="panel" data-testid="excursion-summary">
        <h2>Excursion</h2>
        <p data-testid="excursion-window">{fmt_time(excursion["startUtc"])} to {fmt_time(excursion["endUtc"])}</p>
        <p class="metric" data-testid="duration-45">{excursion["durationMinutes"]} minutes</p>
        <p class="muted">Calculated by deterministic threshold comparison.</p>
      </article>
      <article class="panel status-block" data-testid="decision-status">
        <h2>Decision status</h2>
        <p class="metric" data-testid="final-disposition-blocked">{html.escape(result["finalDisposition"].title())}</p>
        <p data-testid="human-review-required">Human review required.</p>
      </article>
    </section>

    <section class="panel" data-testid="excursion-timeline">
      <h2>Excursion timeline</h2>
      <div class="timeline"><strong>{fmt_time(excursion["startUtc"])}</strong><div class="line" aria-hidden="true"></div><strong>{fmt_time(excursion["endUtc"])}</strong></div>
      <p class="muted">Affected zone: {html.escape(excursion["zoneId"])}. Evidence: {", ".join(map(html.escape, excursion["evidenceIds"]))}.</p>
    </section>

    <section class="grid" aria-label="Pallet mapping">
      <article class="panel" data-testid="mapping-status"><h2>Mapped pallets</h2><ul>{mapped_items}</ul></article>
      <article class="panel status-block" data-testid="unresolved-mapping"><h2>Unresolved pallet</h2><ul>{unresolved_items}</ul></article>
    </section>

    <section class="grid" aria-label="Safety boundary">
      <article class="panel status-block" data-testid="safety-boundary"><h2>Safety boundary</h2><p>No autonomous release, quarantine, discard, reroute, or customer notification.</p><ul>{forbidden_items}</ul></article>
      <article class="panel" data-testid="blockers"><h2>Blockers</h2><ul>{blocker_items}</ul></article>
      <article class="panel" data-testid="review-packet-card"><h2>Review packet</h2><p>Human-readable packet generated from deterministic status.</p><a class="button" href="/review" data-testid="open-review-packet">Open review packet</a></article>
    </section>
  </main>
"""
    return page("ColdChain Sentinel", body)


def render_review_packet(case: dict[str, Any] | None = None) -> str:
    packet = build_review_packet(case or load_fixture())
    result = packet["result"]
    excursion = result["excursion"]
    body = f"""
  <header data-testid="review-packet-page">
    <h1>Human Review Packet</h1>
    <p data-testid="packet-synthetic-label">Synthetic demo data only. This is not a validated pharmaceutical, medical, or compliance product.</p>
    <nav><a href="/">Dashboard</a><a href="/review.json">Review JSON</a></nav>
    {badge("Final disposition blocked", "danger")}{badge("Human review required", "warn")}{badge("Fireworks optional", "warn")}
  </header>
  <main>
    <section class="grid">
      <article class="panel" data-testid="packet-shipment"><h2>Shipment</h2><p class="metric">{html.escape(result["shipmentId"])}</p></article>
      <article class="panel" data-testid="packet-excursion"><h2>Excursion</h2><p>{fmt_time(excursion["startUtc"])} to {fmt_time(excursion["endUtc"])}</p><p class="metric">{excursion["durationMinutes"]} minutes</p></article>
      <article class="panel status-block" data-testid="packet-status"><h2>Status</h2><p data-testid="packet-final-disposition">Final disposition blocked.</p><p data-testid="packet-human-review">Human review required.</p></article>
    </section>

    <section class="grid">
      <article class="panel" data-testid="packet-mapped-pallets"><h2>Mapped pallets</h2><ul>{items(result["mappedPalletIds"], "packet-mapped")}</ul></article>
      <article class="panel status-block" data-testid="packet-unresolved-pallets"><h2>Unresolved evidence</h2><ul>{items(packet["unresolvedEvidence"], "packet-unresolved")}</ul></article>
    </section>

    <section class="grid">
      <article class="panel status-block" data-testid="packet-blocking-reasons"><h2>Blocking reasons</h2><ul>{items(packet["blockingReasons"], "packet-blocking-reason")}</ul></article>
      <article class="panel status-block" data-testid="packet-prohibited-actions"><h2>Prohibited autonomous actions</h2><ul>{items(packet["prohibitedAutonomousActions"], "packet-prohibited")}</ul></article>
    </section>

    <section class="grid">
      <article class="panel" data-testid="reviewer-checklist"><h2>Human reviewer checklist</h2><ul>{items(packet["reviewerChecklist"], "review-check")}</ul></article>
      <article class="panel" data-testid="next-inspection"><h2>Reviewer should inspect next</h2><ul>{items(packet["nextInspection"], "next-inspect")}</ul></article>
    </section>

    <section class="panel" data-testid="packet-limitations"><h2>Limitations</h2><p>{html.escape(packet["productBoundary"])}</p><ul>{items(packet["limitations"], "packet-limitation")}</ul></section>
  </main>
"""
    return page("ColdChain Sentinel Review Packet", body)


def render_ai_review(case: dict[str, Any] | None = None) -> str:
    packet = build_review_packet(case or load_fixture())
    ai_review = build_ai_review(packet)
    result = ai_review["deterministicResult"]
    provider = ai_review["assistant"]["provider"]
    brief = ai_review["assistant"]["brief"]
    safety_items = items(ai_review["safety"], "ai-safety")
    checklist_items = items([str(value) for value in brief["reviewerChecklist"]], "ai-check")
    missing_items = items([str(value) for value in brief["missingEvidence"]], "ai-missing")
    root_cause_items = items([str(value) for value in brief["rootCauseHypotheses"]], "ai-root-cause")
    why_items = items([str(value) for value in brief["whyBlocked"]], "ai-why-blocked")
    unstructured = ai_review["assistant"].get("unstructuredAiResponse") or ""
    unstructured_html = (
        f'<section class="panel status-block" data-testid="ai-unstructured"><h2>Unstructured AI response</h2><p>{html.escape(unstructured)}</p></section>'
        if unstructured
        else ""
    )
    body = f"""
  <header data-testid="ai-review-page">
    <h1>AI Review Assistant</h1>
    <p data-testid="ai-scope-note">AI-assisted explanation only. Deterministic rules remain authoritative.</p>
    <nav><a href="/">Dashboard</a><a href="/review">Review packet</a><a href="/ai-review.json">AI Review JSON</a></nav>
    {badge("Fireworks configured: " + ("yes" if provider["fireworksConfigured"] else "no"), "good" if provider["fireworksConfigured"] else "warn")}
    {badge("Fireworks verified: " + ("yes" if provider["fireworksVerified"] else "no"), "good" if provider["fireworksVerified"] else "warn")}
    {badge("AMD status: pending/not configured", "warn")}
  </header>
  <main>
    <section class="grid" aria-label="Provider status">
      <article class="panel" data-testid="provider-status"><h2>Provider status</h2><p>{html.escape(provider["status"])}</p><p>Model: {html.escape(provider["fireworksModel"])}</p><p>AMD status: pending/not configured.</p></article>
      <article class="panel status-block" data-testid="ai-safety-boundary"><h2>Safety boundary</h2><ul>{safety_items}</ul></article>
    </section>

    <section class="grid" aria-label="Deterministic facts">
      <article class="panel" data-testid="ai-shipment-id"><h2>Shipment</h2><p class="metric">{html.escape(result["shipmentId"])}</p></article>
      <article class="panel" data-testid="ai-duration"><h2>Excursion duration</h2><p class="metric">{result["excursion"]["durationMinutes"]} minutes</p></article>
      <article class="panel status-block" data-testid="ai-final-disposition"><h2>Final disposition</h2><p class="metric">{html.escape(result["finalDisposition"])}</p></article>
      <article class="panel status-block" data-testid="ai-review-status"><h2>Review status</h2><p>{html.escape(result["reviewStatus"])}</p></article>
      <article class="panel status-block" data-testid="ai-unresolved-pallet"><h2>Unresolved pallet</h2><p>{html.escape(", ".join(result["unresolvedPalletIds"]))}</p></article>
      <article class="panel status-block" data-testid="ai-autonomous-actions"><h2>Autonomous actions allowed</h2><p>{str(result["autonomousActionsAllowed"]).lower()}</p></article>
    </section>

    <section class="grid" aria-label="AI reviewer brief">
      <article class="panel" data-testid="ai-summary"><h2>Reviewer brief</h2><p>{html.escape(str(brief["summary"]))}</p></article>
      <article class="panel status-block" data-testid="ai-why-blocked"><h2>Why blocked</h2><ul>{why_items}</ul></article>
      <article class="panel status-block" data-testid="ai-missing-evidence"><h2>Missing evidence</h2><ul>{missing_items}</ul></article>
      <article class="panel" data-testid="ai-reviewer-checklist"><h2>Reviewer checklist</h2><ul>{checklist_items}</ul></article>
      <article class="panel" data-testid="ai-root-cause"><h2>Root-cause hypotheses</h2><ul>{root_cause_items}</ul></article>
      <article class="panel" data-testid="ai-safety-note"><h2>Safety note</h2><p>{html.escape(str(brief["safetyNote"]))}</p></article>
    </section>
    {unstructured_html}
  </main>
"""
    return page("ColdChain Sentinel AI Review Assistant", body)

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path in ("/", "/index.html"):
            self.respond_text(render_dashboard())
            return
        if self.path == "/review":
            self.respond_text(render_review_packet())
            return
        if self.path == "/ai-review":
            self.respond_text(render_ai_review())
            return
        if self.path == "/api/baseline":
            self.respond_json(evaluate_case(load_fixture()))
            return
        if self.path == "/review.json":
            self.respond_json(build_review_packet(load_fixture()))
            return
        if self.path == "/ai-review.json":
            self.respond_json(build_ai_review(build_review_packet(load_fixture())))
            return
        if self.path == "/health":
            self.respond_json({"ok": True, "providers": "disabled"})
            return
        self.send_response(404)
        self.end_headers()

    def respond_text(self, content: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def respond_json(self, content: dict[str, Any]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(content, sort_keys=True).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return


def self_check() -> None:
    dashboard = render_dashboard()
    review = render_review_packet()
    ai_review = render_ai_review()
    packet = build_review_packet(load_fixture())
    required = [
        'data-testid="demo-overview"',
        'data-testid="review-packet-link"',
        'data-testid="ai-review-link"',
        'data-testid="review-packet-page"',
        'data-testid="ai-review-page"',
        'data-testid="provider-status"',
        "AI-assisted explanation only.",
        'data-testid="packet-blocking-reasons"',
        'data-testid="packet-prohibited-actions"',
        'data-testid="reviewer-checklist"',
        'data-testid="next-inspection"',
        "Synthetic demo data only.",
        "Deterministic rules are authoritative.",
        "Final disposition blocked.",
        "Human review required.",
        "No autonomous release.",
        "not a validated pharmaceutical, medical, or compliance product",
        "PAL-SYN-1004 has missing zone mapping.",
    ]
    combined = dashboard + review + ai_review + json.dumps(packet, sort_keys=True)
    for text in required:
        assert text in combined, text
    assert packet["result"]["excursion"]["durationMinutes"] == 45
    assert packet["result"]["finalDisposition"] == "BLOCKED"
    assert packet["result"]["unresolvedPalletIds"] == ["PAL-SYN-1004"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ColdChain Sentinel deterministic dashboard.")
    parser.add_argument("--check", action="store_true", help="Render dashboard/review packet and run assertions.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    if args.check:
        self_check()
        print("dashboard and review packet self-check passed")
        return

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"ColdChain Sentinel dashboard: http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
