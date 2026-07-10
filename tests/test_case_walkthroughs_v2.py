import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from case_walkthroughs_v2 import (  # noqa: E402
    get_case_walkthrough_payload,
    get_case_walkthroughs_payload,
    render_case_walkthroughs_html,
)


CASES = {"door-open-warming", "gateway-delay", "unresolved-mapping-risk", "single-sensor-spike", "multi-sensor-confirmed-warming", "mixed-quality-evidence"}


def test_walkthrough_catalog_and_safety():
    payload = get_case_walkthroughs_payload()
    assert payload["phase"] == "Phase 42 - End-to-End Case Walkthroughs"
    assert payload["status"] == "READY"
    assert payload["supportedWalkthroughCount"] == 6
    assert {item["caseId"] for item in payload["walkthroughs"]} == CASES
    assert payload["syntheticOnly"] is payload["advisoryOnly"] is True
    for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed"):
        assert payload[key] is False
    assert payload["deterministicRulesAuthoritative"] is True


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_each_walkthrough_has_complete_narrative(case_id):
    payload = get_case_walkthrough_payload(case_id)
    assert payload["caseId"] == case_id
    assert len(payload["stepTimeline"]) == 10
    assert [item["sequence"] for item in payload["stepTimeline"]] == list(range(1, 11))
    assert payload["demoNarration"] and len(payload["evidenceRoutes"]) == 7
    assert payload["safetyBoundary"] and payload["whatNotToDo"]
    assert payload["stblPrediction"] and payload["inspectionPlan"]


def test_unknown_walkthrough_and_html():
    with pytest.raises(KeyError):
        get_case_walkthrough_payload("unknown-case")
    catalog = render_case_walkthroughs_html()
    detail = render_case_walkthroughs_html("door-open-warming")
    assert "End-to-End Case Walkthroughs" in catalog
    assert catalog.count("Open walkthrough") == 6
    for text in ("Door-Open Warming", "STBL prediction", "Inspection plan", "Safety boundary", "Synthetic-only", "Advisory-only"):
        assert text in detail
    assert "https://" not in catalog + detail and "<script" not in (catalog + detail).lower()
