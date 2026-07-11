from __future__ import annotations

import html
from typing import Any

from ui_design_system_v2 import unified_page


PHASE = "Phase 40 - Large-Scale Synthetic Data Demonstration"

PROFILES = [
    {"profileId": "readings-10k", "description": "Compact deterministic sensor-reading demonstration.", "syntheticReadingCount": 10000, "sensorCount": 24, "shipmentCount": 2, "zoneCount": 8, "expectedQualityEvents": 35, "expectedFaultFamilies": 8, "estimatedMemoryNote": "Estimated compact JSON memory footprint: tens of MB before streaming.", "routeToInspect": "/data-pipeline"},
    {"profileId": "readings-100k", "description": "High-volume multi-sensor reasoning profile.", "syntheticReadingCount": 100000, "sensorCount": 96, "shipmentCount": 8, "zoneCount": 32, "expectedQualityEvents": 310, "expectedFaultFamilies": 20, "estimatedMemoryNote": "Estimated compact JSON memory footprint: hundreds of MB; stream in bounded batches.", "routeToInspect": "/large-scale-data-lab/throughput-summary.json"},
    {"profileId": "training-windows-171k", "description": "Committed STBL offline synthetic training corpus summary.", "syntheticWindowCount": 171000, "sensorCount": 152, "shipmentCount": 38, "zoneCount": 76, "expectedQualityEvents": 1200, "expectedFaultFamilies": 38, "estimatedMemoryNote": "Only aggregate artifacts are committed; raw generated windows are excluded.", "routeToInspect": "/algorithm-console"},
    {"profileId": "readings-1m", "description": "One-million-reading simulated ingestion profile.", "syntheticReadingCount": 1000000, "sensorCount": 480, "shipmentCount": 40, "zoneCount": 160, "expectedQualityEvents": 4200, "expectedFaultFamilies": 38, "estimatedMemoryNote": "Designed for generator-to-stream processing rather than one in-memory payload.", "routeToInspect": "/large-scale-data-lab/throughput-summary.json"},
    {"profileId": "multi-shipment-stream", "description": "Interleaved deterministic readings across many synthetic shipments.", "syntheticReadingCount": 250000, "sensorCount": 240, "shipmentCount": 50, "zoneCount": 200, "expectedQualityEvents": 950, "expectedFaultFamilies": 24, "estimatedMemoryNote": "Bounded shipment partitions keep working sets small.", "routeToInspect": "/scenario-library-v4"},
    {"profileId": "multi-zone-stream", "description": "Zone-consensus stress profile with cross-zone disagreement.", "syntheticReadingCount": 180000, "sensorCount": 320, "shipmentCount": 20, "zoneCount": 240, "expectedQualityEvents": 780, "expectedFaultFamilies": 18, "estimatedMemoryNote": "Zone partitions support incremental consensus summaries.", "routeToInspect": "/evaluation-matrix-v2"},
    {"profileId": "failure-heavy-stream", "description": "Quality-event-heavy stream spanning the synthetic fault universe.", "syntheticReadingCount": 120000, "sensorCount": 144, "shipmentCount": 12, "zoneCount": 48, "expectedQualityEvents": 12000, "expectedFaultFamilies": 38, "estimatedMemoryNote": "Failure events are summarized incrementally; raw bulk output is not committed.", "routeToInspect": "/fault-atlas"},
]


def get_large_scale_profiles_payload() -> dict[str, Any]:
    return {"phase": PHASE, "syntheticOnly": True, "advisoryOnly": True, "profileCount": len(PROFILES), "profiles": [dict(profile) for profile in PROFILES]}


def get_throughput_summary_payload() -> dict[str, Any]:
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "rawLargeDatasetsCommitted": False, "generationIsDeterministic": True,
        "dependenciesAdded": False, "externalCallsRequired": False,
        "deterministicGeneratorDesign": ["seeded scenario templates", "bounded reading batches", "incremental quality summaries", "shipment and zone partitioning"],
        "streamingFriendlyDesignNotes": ["process one bounded batch at a time", "retain aggregate counters instead of raw history", "partition consensus by shipment and zone", "persist only reviewed evidence when a future data store exists"],
        "futureRealIngestionChanges": ["validated connector contracts", "durable queue and backpressure", "idempotency and replay controls", "security and retention policy", "field validation and operational monitoring"],
        "productionClaimed": False,
    }


def get_large_scale_data_lab_payload() -> dict[str, Any]:
    return {
        "phase": PHASE, "status": "READY", "syntheticOnly": True, "advisoryOnly": True,
        "realWorldDataUsed": False, "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False,
        "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True,
        "rawLargeDatasetsCommitted": False, "generationIsDeterministic": True,
        "dependenciesAdded": False, "externalCallsRequired": False,
        "summaryProfiles": [dict(profile) for profile in PROFILES],
        "routeMap": {"largeScaleDataLab": "/large-scale-data-lab", "profiles": "/large-scale-data-lab/profiles.json", "throughputSummary": "/large-scale-data-lab/throughput-summary.json", "behaviorPredictor": "/behavior-predictor", "dataQuality": "/data-pipeline", "algorithmConsole": "/algorithm-console", "faultAtlas": "/fault-atlas"},
        "safetyBoundary": {"syntheticOnly": True, "advisoryOnly": True, "noRawBulkDataCommitted": True, "noDeploymentPerformanceClaim": True},
    }


@unified_page
def render_large_scale_data_lab_html() -> str:
    payload = get_large_scale_data_lab_payload()
    rows = "".join(
        f'<article><div><strong>{html.escape(profile["profileId"])}</strong><p>{html.escape(profile["description"])}</p></div>'
        f'<dl><div><dt>Scale</dt><dd>{profile.get("syntheticReadingCount", profile.get("syntheticWindowCount")):,}</dd></div><div><dt>Sensors</dt><dd>{profile["sensorCount"]}</dd></div><div><dt>Shipments</dt><dd>{profile["shipmentCount"]}</dd></div><div><dt>Fault families</dt><dd>{profile["expectedFaultFamilies"]}</dd></div></dl>'
        f'<div><p>{html.escape(profile["estimatedMemoryNote"])}</p><a href="{html.escape(profile["routeToInspect"])}">Inspect evidence</a></div></article>'
        for profile in payload["summaryProfiles"]
    )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Large-Scale Synthetic Data Lab</title><style>
    :root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:12px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1180px,100%);margin:auto;padding:28px 18px 60px}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}h1{{font-size:46px;line-height:1.05;letter-spacing:-.035em;text-wrap:balance;margin:0 0 14px}}h2{{font-size:25px;text-wrap:balance}}.intro{{max-width:74ch;color:var(--muted)}}.badges,.routes{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 38px}}.badges span,.routes a{{border:1px solid var(--line);border-radius:8px;padding:7px 10px}}.summary{{display:flex;flex-wrap:wrap;gap:22px;border-block:1px solid var(--line);padding:18px 0;margin-bottom:42px}}.summary div{{min-width:150px}}.summary strong{{display:block;color:var(--accent);font-size:26px}}.profiles{{border-top:1px solid var(--line)}}.profiles article{{display:grid;grid-template-columns:1.1fr 1fr .9fr;gap:24px;padding:22px 0;border-bottom:1px solid var(--line);align-items:start}}.profiles article>div{{min-width:0}}.profiles strong{{font-size:19px}}.profiles p{{color:var(--muted);text-wrap:pretty}}dl{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0}}dl div{{background:var(--surface);padding:9px;border-radius:8px}}dt{{color:var(--muted);font-size:13px}}dd{{margin:0;font-weight:750}}.boundary{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:22px;margin-top:38px}}@media(max-width:760px){{main{{padding:18px 12px 44px}}h1{{font-size:36px}}.profiles article{{grid-template-columns:1fr;gap:8px}}.summary{{gap:14px}}}}
    </style></head><body><main><header><h1>Large-Scale Synthetic Data Demonstration</h1><p class="intro">High-volume reasoning profiles show the intended data shape without committing huge raw datasets or claiming deployment throughput.</p></header><div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>Deterministic generation</span><span>Raw large datasets committed: false</span><span>Runtime GPU required: false</span></div><section class="summary"><div><strong>10,000</strong><span>compact profile</span></div><div><strong>100,000</strong><span>high-volume profile</span></div><div><strong>171,000</strong><span>training windows</span></div><div><strong>1,000,000</strong><span>simulated profile</span></div></section><section><h2>Scale profiles</h2><div class="profiles">{rows}</div></section><section class="boundary"><h2>Storage and runtime boundary</h2><p>Only small aggregate evidence is committed. Large profiles describe deterministic generation and streaming-oriented processing, not measured deployment performance.</p></section><nav class="routes"><a href="/behavior-predictor">Behavior Predictor</a><a href="/data-pipeline">Data Quality</a><a href="/algorithm-console">Algorithm Console</a><a href="/fault-atlas">Fault Atlas</a></nav></main></body></html>'''
