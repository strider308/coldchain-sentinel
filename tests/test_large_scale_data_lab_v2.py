import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from large_scale_data_lab_v2 import (  # noqa: E402
    get_large_scale_data_lab_payload,
    get_large_scale_profiles_payload,
    get_throughput_summary_payload,
    render_large_scale_data_lab_html,
)


def test_large_scale_payload_profiles_and_safety():
    payload = get_large_scale_data_lab_payload()
    assert payload["phase"] == "Phase 40 - Large-Scale Synthetic Data Demonstration"
    assert payload["status"] == "READY"
    assert payload["syntheticOnly"] is payload["advisoryOnly"] is True
    for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed", "rawLargeDatasetsCommitted"):
        assert payload[key] is False
    assert payload["deterministicRulesAuthoritative"] is True
    assert payload["generationIsDeterministic"] is True
    counts = {row.get("syntheticReadingCount", row.get("syntheticWindowCount")) for row in payload["summaryProfiles"]}
    assert {10000, 100000, 171000, 1000000} <= counts
    assert len(payload["summaryProfiles"]) == 7


def test_profiles_throughput_and_html():
    assert get_large_scale_profiles_payload()["profileCount"] == 7
    summary = get_throughput_summary_payload()
    assert summary["rawLargeDatasetsCommitted"] is False
    assert summary["generationIsDeterministic"] is True
    assert summary["streamingFriendlyDesignNotes"] and summary["futureRealIngestionChanges"]
    page = render_large_scale_data_lab_html()
    for text in ("Large-Scale Synthetic Data Demonstration", "1,000,000", "huge raw datasets", "Synthetic-only", "Advisory-only"):
        assert text in page
    assert "https://" not in page and "<script" not in page.lower()
