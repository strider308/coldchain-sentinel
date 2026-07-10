import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from final_freeze_v2 import get_final_freeze_payload, get_owner_freeze_decision_payload, render_final_freeze_html


def test_final_freeze_payload():
    payload = get_final_freeze_payload()
    assert payload["phase"] == "Phase 47 - Final Freeze"
    assert payload["status"] == "READY_FOR_OWNER_FREEZE_DECISION"
    assert payload["ownerFreezeDecisionRequired"] is True
    assert payload["demoFreezeActive"] is False
    assert payload["automaticFreezeEnabled"] is False
    assert payload["finalNoGoConditions"] and payload["ownerChecklist"]
    for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed"):
        assert payload[key] is False
    assert payload["syntheticOnly"] and payload["advisoryOnly"] and payload["deterministicRulesAuthoritative"]


def test_owner_decision_and_html():
    decision = get_owner_freeze_decision_payload()
    assert decision["ownerFreezeDecisionRequired"] is True
    assert decision["demoFreezeActive"] is False
    assert decision["decisionOptions"] == ["HOLD", "FREEZE_AFTER_LIVE_QA", "REOPEN_FOR_FIXES"]
    page = render_final_freeze_html()
    for text in ("Final Freeze", "Owner decision required", "Demo freeze active: false", "Automatic freeze enabled: false", "Synthetic-only", "Advisory-only"):
        assert text in page
    assert "https://" not in page and "<script" not in page.lower()
