import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from demo_script_qna_v2 import get_demo_script_final_payload, get_judge_qna_payload, get_safe_claims_guide_payload, render_demo_script_qna_html


def test_demo_script_payload():
    payload = get_demo_script_final_payload()
    assert payload["phase"] == "Phase 45 - Demo Script and Judge Q&A"
    assert payload["status"] == "READY"
    assert set(payload["scripts"]) == {"60SecondPitch", "3MinuteDemo", "5MinuteDemo", "technicalDeepDive"}
    assert len(payload["routeOrder"]) == 6
    for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed"):
        assert payload[key] is False
    assert payload["syntheticOnly"] and payload["advisoryOnly"] and payload["deterministicRulesAuthoritative"]


def test_qna_claims_and_html():
    assert len(get_judge_qna_payload()["questions"]) >= 18
    guide = get_safe_claims_guide_payload()
    assert guide["whatWeCanSay"] and guide["whatWeCannotSay"] and guide["approvedPhrases"]
    source = Path(__file__).resolve().parents[1] / "src" / "demo_script_qna_v2.py"
    forbidden = ["production" + "-ready", "pharma" + " validated", "real-world" + " validated", "compliance" + " certified", "autonomous" + " release", "customer" + " notification"]
    text = source.read_text(encoding="utf-8").lower()
    assert not any(phrase in text for phrase in forbidden)
    page = render_demo_script_qna_html()
    for label in ("Demo Script and Judge Q&amp;A", "60SecondPitch", "Judge Q&amp;A", "Approved language", "Synthetic-only", "Advisory-only"):
        assert label in page
    assert "<script" not in page.lower()
