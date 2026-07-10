import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from final_route_manifest_v2 import get_final_route_manifest_payload, get_live_qa_checklist_payload, get_live_validation_script, render_final_route_manifest_html


def test_manifest_payload_and_safety():
    payload = get_final_route_manifest_payload()
    assert payload["phase"] == "Phase 43 - Final Route Manifest and Live QA Sweep"
    assert payload["status"] == "READY"
    assert len(payload["requiredRoutes"]) >= 35
    assert len(payload["expected404Routes"]) >= 5
    for key, expected in {"syntheticOnly": True, "advisoryOnly": True, "realWorldDataUsed": False, "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False, "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True}.items():
        assert payload[key] is expected


def test_live_qa_script_and_html():
    checklist = get_live_qa_checklist_payload()
    assert checklist["ownerSignoffRequired"] is True
    assert len(checklist["checklistSections"]) == 9
    script = get_live_validation_script()
    assert '$base = "https://coldchain-sentinel-35ex.onrender.com"' in script
    assert script.rstrip().endswith('Write-Host "FINAL LIVE QA SWEEP PASSED"')
    page = render_final_route_manifest_html()
    for text in ("Final Route Manifest and Live QA Sweep", "Pass criteria", "No-go criteria", "Synthetic-only", "Advisory-only"):
        assert text in page
    assert "https://" not in page and "<script" not in page.lower()
