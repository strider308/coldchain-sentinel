"""Stdlib-only ColdChain Sentinel dashboard and review packet."""

from __future__ import annotations

import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from ai_review_assistant import build_ai_review
from case_engine import case_packet, evidence_json, export_markdown, get_case, load_cases
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


def timeline_items(values: list[dict[str, str]]) -> str:
    return "\n".join(
        f'<li data-testid="timeline-{html.escape(row["time"])}"><strong>{html.escape(row["time"])}</strong> - {html.escape(row["event"])}</li>'
        for row in values
    )


def table(headers: list[str], rows: list[list[str]], testid: str) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>" for row in rows
    )
    return f'<table data-testid="{html.escape(testid)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


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
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ text-align: left; border-bottom: 1px solid var(--line); padding: 8px 6px; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 13px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }}
    .check-row {{ display: flex; gap: 8px; align-items: flex-start; margin: 8px 0; }}
    .check-row input {{ margin-top: 4px; }}
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
    <nav><a href="/">Dashboard</a><a href="/cases">Cases</a><a href="/review" data-testid="review-packet-link">Review packet</a><a href="/ai-review" data-testid="ai-review-link">AI review</a><a href="/review.json">Review JSON</a></nav>
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


def render_cases() -> str:
    cases = load_cases()
    cards = "\n".join(
        f"""
      <article class="panel" data-testid="case-{html.escape(case["caseId"])}">
        <h2>{html.escape(case["caseTitle"])}</h2>
        <p>{html.escape(case["scenarioSummary"])}</p>
        {badge(case["reviewStatus"], "warn")}{badge(case["finalDisposition"], "danger" if case["finalDisposition"] == "BLOCKED" else "warn")}
        <p>Blockers: {len(case["blockers"])}. Unresolved pallets: {len(case["unresolvedPalletIds"])}.</p>
        <div class="toolbar">
          <a class="button" href="/cases/{html.escape(case["caseId"])}">Open case</a>
          <a class="button" href="/cases/{html.escape(case["caseId"])}/review">Review workspace</a>
          <a class="button" href="/cases/{html.escape(case["caseId"])}/evidence.json">Evidence JSON</a>
          <a class="button" href="/cases/{html.escape(case["caseId"])}/export.md">Export</a>
          <a class="button" href="/ai-review?caseId={html.escape(case["caseId"])}">Fireworks brief</a>
        </div>
      </article>
"""
        for case in cases
    )
    comparison = table(
        ["Case", "Excursion?", "Pallet mapping complete?", "Human review?", "Autonomous actions allowed?", "Demo-only limitation"],
        [
            [
                case["caseId"],
                "yes" if case["excursion"] else "no",
                "yes" if not case["unresolvedPalletIds"] else "no",
                "yes" if "HUMAN_REVIEW" in case["reviewStatus"] or "REVIEW" in case["reviewStatus"] else "yes",
                str(case["autonomousActionsAllowed"]).lower(),
                "Synthetic only; no operational action.",
            ]
            for case in cases
        ],
        "case-comparison",
    )
    body = f"""
  <header data-testid="cases-page">
    <h1>Synthetic Case Workspace</h1>
    <p>Synthetic demo data only. No operational action is authorized.</p>
    <nav><a href="/">Dashboard</a><a href="/cases">Cases</a><a href="/review">Baseline review</a></nav>
  </header>
  <main>
    <section class="grid" aria-label="Synthetic cases">{cards}</section>
    <section class="panel" data-testid="scenario-comparison"><h2>Scenario comparison</h2>{comparison}</section>
  </main>
"""
    return page("ColdChain Sentinel Cases", body)


def render_case_detail(case_id: str) -> str:
    case = get_case(case_id)
    packet = case_packet(case)
    result = packet["result"]
    body = f"""
  <header data-testid="case-detail">
    <h1>{html.escape(case["caseTitle"])}</h1>
    <p>{html.escape(case["scenarioSummary"])}</p>
    <nav><a href="/cases">Cases</a><a href="/cases/{html.escape(case_id)}/review">Reviewer workspace</a><a href="/cases/{html.escape(case_id)}/evidence.json">Evidence JSON</a><a href="/cases/{html.escape(case_id)}/export.md">Export packet</a><a href="/ai-review?caseId={html.escape(case_id)}">AI Review</a><a href="/ai-review.json?caseId={html.escape(case_id)}">AI JSON</a></nav>
    {badge(result["reviewStatus"], "warn")}{badge(result["finalDisposition"], "danger" if result["finalDisposition"] == "BLOCKED" else "warn")}{badge("No autonomous action", "warn")}
  </header>
  <main>
    <section class="grid">
      <article class="panel"><h2>Shipment</h2><p class="metric">{html.escape(result["shipmentId"])}</p></article>
      <article class="panel"><h2>Review status</h2><p>{html.escape(result["reviewStatus"])}</p></article>
      <article class="panel"><h2>Final disposition</h2><p>{html.escape(result["finalDisposition"])}</p></article>
      <article class="panel status-block"><h2>Autonomous actions allowed</h2><p>{str(result["autonomousActionsAllowed"]).lower()}</p></article>
    </section>
  </main>
"""
    return page(case["caseTitle"], body)


def render_case_review(case_id: str, simulate_resolved: bool = False) -> str:
    case = get_case(case_id)
    packet = case_packet(case, simulate_resolved)
    before_packet = case_packet(case)
    result = packet["result"]
    excursion = result["excursion"]
    mapped_table = table(
        ["Pallet", "Mapping state"],
        [[pallet_id, "synthetically mapped"] for pallet_id in result["mappedPalletIds"]],
        "mapped-pallet-table",
    )
    unresolved_table = table(
        ["Pallet", "Review state"],
        [[pallet_id, "missing synthetic zone mapping"] for pallet_id in result["unresolvedPalletIds"]]
        or [["None", "no unresolved synthetic pallet mapping"]],
        "unresolved-pallet-table",
    )
    blocker_table = table(
        ["Blocker", "Meaning"],
        [[blocker, blocker.replace("_", " ").title()] for blocker in result["blockers"]]
        or [["None", "review packet completion simulated"]],
        "blocker-table",
    )
    checklist = "\n".join(
        f"""
        <label class="check-row">
          <input type="checkbox" data-check-index="{index}">
          <span>{html.escape(item)}</span>
        </label>
"""
        for index, item in enumerate(packet["reviewerChecklist"])
    )
    disclaimers = items(packet["limitations"], "case-safety")
    timeline = timeline_items(packet["evidenceTimeline"])
    excursion_html = (
        f'<p data-testid="case-excursion">{fmt_time(excursion["startUtc"])} to {fmt_time(excursion["endUtc"])}. Duration: {excursion["durationMinutes"]} minutes. Zone: {html.escape(excursion["zoneId"])}.</p>'
        if excursion
        else '<p data-testid="case-excursion">No temperature excursion in this synthetic control fixture.</p>'
    )
    can_simulate = case_id == "blocked-unresolved-pallet" and not simulate_resolved
    simulation_link = (
        f'<a class="button" href="/cases/{html.escape(case_id)}/review?simulateResolved=true">Simulate resolving missing mapping</a>'
        if can_simulate
        else ""
    )
    sim_note = ""
    comparison = ""
    if simulate_resolved and case_id == "blocked-unresolved-pallet":
        before = before_packet["result"]
        comparison = table(
            ["Field", "Before", "After simulation"],
            [
                ["unresolvedPalletIds", ", ".join(before["unresolvedPalletIds"]), "None; PAL-SYN-1004 synthetically mapped"],
                ["finalDisposition", before["finalDisposition"], result["finalDisposition"]],
                ["reviewStatus", before["reviewStatus"], result["reviewStatus"]],
                ["autonomousActionsAllowed", str(before["autonomousActionsAllowed"]).lower(), str(result["autonomousActionsAllowed"]).lower()],
            ],
            "simulation-comparison",
        )
        sim_note = (
            '<section class="panel status-block" data-testid="simulated-resolution">'
            "<h2>Simulated mapping resolution</h2>"
            "<p>PAL-SYN-1004 is synthetically mapped for review packet completion.</p>"
            "<p>This is a synthetic review packet completion, not shipment approval.</p>"
            f"{comparison}</section>"
        )
    checklist_count = len(packet["reviewerChecklist"])
    checklist_script = f"""
  <script>
    (() => {{
      const key = "coldchain-checklist:{html.escape(case_id)}";
      const boxes = Array.from(document.querySelectorAll("[data-check-index]"));
      const progress = document.querySelector("[data-check-progress]");
      const saved = JSON.parse(localStorage.getItem(key) || "{{}}");
      function render() {{
        const reviewed = boxes.filter((box) => box.checked).length;
        progress.textContent = reviewed + "/{checklist_count} reviewed";
        const state = Object.fromEntries(boxes.map((box) => [box.dataset.checkIndex, box.checked]));
        localStorage.setItem(key, JSON.stringify(state));
      }}
      boxes.forEach((box) => {{
        box.checked = Boolean(saved[box.dataset.checkIndex]);
        box.addEventListener("change", render);
      }});
      render();
    }})();
  </script>
"""
    ai_href = f"/ai-review?caseId={html.escape(case_id)}"
    ai_json_href = f"/ai-review.json?caseId={html.escape(case_id)}"
    export_href = f"/cases/{html.escape(case_id)}/export.md"
    if simulate_resolved:
        export_href += "?simulateResolved=true"
    evidence_href = f"/cases/{html.escape(case_id)}/evidence.json"
    if simulate_resolved:
        evidence_href += "?simulateResolved=true"
    fireworks_panel = (
        f'<section class="panel" data-testid="fireworks-panel"><h2>Fireworks assistant</h2>'
        "<p>Optional reviewer explanation only. Deterministic rules remain authoritative.</p>"
        f'<div class="toolbar"><a class="button" href="{ai_href}">Open AI review</a><a class="button" href="{ai_json_href}">AI JSON</a></div></section>'
    )
    export_panel = (
        f'<section class="panel" data-testid="export-panel"><h2>Export packet</h2>'
        "<p>Markdown and JSON exports contain synthetic review evidence only.</p>"
        f'<div class="toolbar"><a class="button" href="{evidence_href}">Evidence JSON</a><a class="button" href="{export_href}">Export markdown</a></div></section>'
    )
    body = f"""
  <header data-testid="case-review">
    <h1>{html.escape(case["caseTitle"])}</h1>
    <p>{html.escape(case["scenarioSummary"])}</p>
    <nav><a href="/cases">Cases</a><a href="{evidence_href}">Evidence JSON</a><a href="{export_href}">Export packet</a><a href="{ai_href}">AI Review Assistant</a><a href="{ai_json_href}">AI JSON</a></nav>
    {badge(result["reviewStatus"], "warn")}{badge(result["finalDisposition"], "danger" if result["finalDisposition"] == "BLOCKED" else "warn")}{badge("Autonomous actions: false", "warn")}
  </header>
  <main>
    {sim_note}
    <section class="grid" data-testid="case-header">
      <article class="panel"><h2>Shipment facts</h2><p class="metric">{html.escape(result["shipmentId"])}</p><p>Case ID: {html.escape(case_id)}</p></article>
      <article class="panel status-block" data-testid="deterministic-status-card"><h2>Deterministic status</h2><p>finalDisposition: {html.escape(result["finalDisposition"])}</p><p>reviewStatus: {html.escape(result["reviewStatus"])}</p><p>autonomousActionsAllowed: {str(result["autonomousActionsAllowed"]).lower()}</p></article>
    </section>
    <section class="panel" data-testid="manual-resolution-panel"><h2>Manual resolution simulation</h2><p>Current unresolved pallet: {html.escape(", ".join(before_packet["result"]["unresolvedPalletIds"]) or "None")}</p><div class="toolbar">{simulation_link}</div></section>
    <section class="panel" data-testid="case-excursion-panel"><h2>Excursion</h2>{excursion_html}</section>
    <section class="panel" data-testid="evidence-timeline"><h2>Evidence timeline</h2><ul>{timeline}</ul></section>
    <section class="grid">
      <article class="panel"><h2>Mapped pallet table</h2>{mapped_table}</article>
      <article class="panel status-block"><h2>Unresolved pallet table</h2>{unresolved_table}</article>
      <article class="panel status-block"><h2>Blocker explanation</h2>{blocker_table}</article>
      <article class="panel" data-testid="reviewer-checklist-workspace"><h2>Reviewer checklist</h2><p data-check-progress>0/{checklist_count} reviewed</p>{checklist}</article>
      {fireworks_panel}
      {export_panel}
      <article class="panel status-block"><h2>Safety disclaimers</h2><ul>{disclaimers}</ul></article>
    </section>
  </main>
  {checklist_script}
"""
    return page(f"{case['caseTitle']} Review", body)


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


def render_ai_review(case: dict[str, Any] | None = None, case_id: str | None = None) -> str:
    packet = case_packet(get_case(case_id)) if case_id else build_review_packet(case or load_fixture())
    ai_review = build_ai_review(packet)
    result = ai_review["deterministicResult"]
    provider = ai_review["assistant"]["provider"]
    brief = ai_review["assistant"]["brief"]
    safety_items = items(ai_review["safety"], "ai-safety")
    checklist_items = items([str(value) for value in brief["reviewerChecklist"]], "ai-check")
    missing_items = items([str(value) for value in brief["missingEvidence"]], "ai-missing")
    root_cause_items = items([str(value) for value in brief["rootCauseHypotheses"]], "ai-root-cause")
    why_items = items([str(value) for value in brief["whyBlocked"]], "ai-why-blocked")
    source = provider["displayedBriefSource"]
    source_label = (
        "<p><strong>Sanitized Fireworks-generated reviewer brief, non-authoritative.</strong></p>"
        if source == "sanitized_fireworks_text"
        else ""
    )
    case_identity = f'<p data-testid="ai-selected-case">Selected case: {html.escape(packet.get("caseId", "baseline"))} - {html.escape(packet.get("caseTitle", "Baseline review packet"))}</p>'
    body = f"""
  <header data-testid="ai-review-page">
    <h1>AI Review Assistant</h1>
    <p data-testid="ai-scope-note">AI-assisted explanation only. Deterministic rules remain authoritative.</p>
    {case_identity}
    <nav><a href="/">Dashboard</a><a href="/review">Review packet</a><a href="/ai-review.json">AI Review JSON</a></nav>
    {badge("Fireworks configured: " + ("yes" if provider["fireworksConfigured"] else "no"), "good" if provider["fireworksConfigured"] else "warn")}
    {badge("Fireworks call succeeded: " + ("yes" if provider["fireworksCallSucceeded"] else "no"), "good" if provider["fireworksCallSucceeded"] else "warn")}
    {badge("Structured output verified: " + ("yes" if provider["fireworksStructuredOutputVerified"] else "no"), "good" if provider["fireworksStructuredOutputVerified"] else "warn")}
    {badge("Displayed brief source: " + source, "good" if source != "deterministic_fallback" else "warn")}
    {badge("AMD status: pending/not configured", "warn")}
  </header>
  <main>
    <section class="grid" aria-label="Provider status">
      <article class="panel" data-testid="provider-status"><h2>Provider status</h2><p>{html.escape(provider["status"])}</p><p>Model: {html.escape(provider["fireworksModel"])}</p><p>Displayed brief source: {html.escape(source)}</p><p>AMD status: pending/not configured.</p></article>
      <article class="panel status-block" data-testid="ai-safety-boundary"><h2>Safety boundary</h2><ul>{safety_items}</ul></article>
    </section>

    <section class="grid" aria-label="Deterministic facts">
      <article class="panel" data-testid="ai-shipment-id"><h2>Shipment</h2><p class="metric">{html.escape(result["shipmentId"])}</p></article>
      <article class="panel" data-testid="ai-duration"><h2>Excursion duration</h2><p class="metric">{result["excursion"]["durationMinutes"] if result["excursion"] else "None"}{ " minutes" if result["excursion"] else ""}</p></article>
      <article class="panel status-block" data-testid="ai-final-disposition"><h2>Final disposition</h2><p class="metric">{html.escape(result["finalDisposition"])}</p></article>
      <article class="panel status-block" data-testid="ai-review-status"><h2>Review status</h2><p>{html.escape(result["reviewStatus"])}</p></article>
      <article class="panel status-block" data-testid="ai-unresolved-pallet"><h2>Unresolved pallet</h2><p>{html.escape(", ".join(result["unresolvedPalletIds"]))}</p></article>
      <article class="panel status-block" data-testid="ai-autonomous-actions"><h2>Autonomous actions allowed</h2><p>{str(result["autonomousActionsAllowed"]).lower()}</p></article>
    </section>

    <section class="grid" aria-label="AI reviewer brief">
      <article class="panel" data-testid="ai-summary"><h2>Reviewer brief</h2>{source_label}<p>{html.escape(str(brief["summary"]))}</p></article>
      <article class="panel status-block" data-testid="ai-why-blocked"><h2>Why blocked</h2><ul>{why_items}</ul></article>
      <article class="panel status-block" data-testid="ai-missing-evidence"><h2>Missing evidence</h2><ul>{missing_items}</ul></article>
      <article class="panel" data-testid="ai-reviewer-checklist"><h2>Reviewer checklist</h2><ul>{checklist_items}</ul></article>
      <article class="panel" data-testid="ai-root-cause"><h2>Root-cause hypotheses</h2><ul>{root_cause_items}</ul></article>
      <article class="panel" data-testid="ai-safety-note"><h2>Safety note</h2><p>{html.escape(str(brief["safetyNote"]))}</p></article>
    </section>
  </main>
"""
    return page("ColdChain Sentinel AI Review Assistant", body)

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        case_id = query.get("caseId", [None])[0]
        simulate_resolved = query.get("simulateResolved", ["false"])[0].lower() == "true"
        if path in ("/", "/index.html"):
            self.respond_text(render_dashboard())
            return
        if path == "/cases":
            self.respond_text(render_cases())
            return
        if path.startswith("/cases/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 2:
                try:
                    selected = parts[1]
                    if len(parts) == 2:
                        self.respond_text(render_case_detail(selected))
                        return
                    if parts[2] == "review":
                        self.respond_text(render_case_review(selected, simulate_resolved))
                        return
                    if parts[2] == "evidence.json":
                        self.respond_json(evidence_json(get_case(selected), simulate_resolved))
                        return
                    if parts[2] == "export.md":
                        self.respond_markdown(export_markdown(get_case(selected), simulate_resolved))
                        return
                except KeyError:
                    self.send_response(404)
                    self.end_headers()
                    return
        if path == "/review":
            self.respond_text(render_review_packet())
            return
        if path == "/ai-review":
            try:
                self.respond_text(render_ai_review(case_id=case_id))
            except KeyError:
                self.send_response(404)
                self.end_headers()
            return
        if path == "/api/baseline":
            self.respond_json(evaluate_case(load_fixture()))
            return
        if path == "/review.json":
            self.respond_json(build_review_packet(load_fixture()))
            return
        if path == "/ai-review.json":
            try:
                packet = case_packet(get_case(case_id)) if case_id else build_review_packet(load_fixture())
            except KeyError:
                self.send_response(404)
                self.end_headers()
                return
            self.respond_json(build_ai_review(packet))
            return
        if path == "/health":
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

    def respond_markdown(self, content: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

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
