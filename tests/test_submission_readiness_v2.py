import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from submission_readiness_v2 import get_submission_checklist_payload, get_submission_copy_payload, get_submission_readiness_payload, render_submission_readiness_html


def test_submission_payload():
    payload = get_submission_readiness_payload()
    assert payload["phase"] == "Phase 44 - Submission Readiness Pack"
    assert payload["status"] == "READY_FOR_OWNER_SUBMISSION"
    assert payload["ownerSubmissionRequired"] is True
    assert payload["submissionNotAutomated"] is True
    assert payload["liveDemoUrl"] == "https://coldchain-sentinel-35ex.onrender.com"
    assert payload["repositoryUrl"] == "https://github.com/strider308/coldchain-sentinel"
    assert payload["oneLineDescription"] and payload["shortDescription"] and payload["longDescription"]
    assert payload["headlineMetrics"]["trainingRows"] == 171000
    assert payload["headlineMetrics"]["faultCount"] == 38
    for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed"):
        assert payload[key] is False
    assert payload["syntheticOnly"] and payload["advisoryOnly"] and payload["deterministicRulesAuthoritative"]


def test_submission_supporting_payloads_and_html():
    assert get_submission_checklist_payload()["ownerSignoffRequired"] is True
    copy = get_submission_copy_payload()
    assert all(copy[key] for key in ("technicalSummary", "aiUsageDisclosure", "safetyDisclosure", "limitationsDisclosure"))
    page = render_submission_readiness_html()
    for text in ("Submission Readiness Pack", "One-line description", "Screenshot list", "Owner checklist", "Claims boundary", "Synthetic-only", "Advisory-only"):
        assert text in page
    assert "<script" not in page.lower()
