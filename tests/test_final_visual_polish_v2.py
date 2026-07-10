import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from final_visual_polish_v2 import get_screenshot_checklist_payload, get_screenshot_route_map_payload, get_visual_polish_payload, render_visual_polish_html


def test_visual_polish_payload():
    payload = get_visual_polish_payload()
    assert payload["phase"] == "Phase 46 - Visual Polish and Screenshot Pass"
    assert payload["polishOnly"] is True
    assert payload["architectureChanged"] is False
    assert payload["dependenciesAdded"] is False
    assert len(payload["screenshotReadyRoutes"]) >= 8
    for key in ("runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed"):
        assert payload[key] is False
    assert payload["syntheticOnly"] and payload["advisoryOnly"] and payload["deterministicRulesAuthoritative"]


def test_screenshot_payloads_and_html():
    checklist = get_screenshot_checklist_payload()
    routes = get_screenshot_route_map_payload()
    assert checklist["screenshotChecklist"] and checklist["noGoVisualIssues"]
    assert len(routes["routes"]) == 9
    page = render_visual_polish_html()
    for text in ("Visual Polish and Screenshot Pass", "Capture checks", "Capture order", "Synthetic-only", "Advisory-only"):
        assert text in page
    assert "https://" not in page and "<script" not in page.lower()
