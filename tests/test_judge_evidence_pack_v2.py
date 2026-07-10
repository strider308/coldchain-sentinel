import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from judge_evidence_pack_v2 import (  # noqa: E402
    get_claims_boundary_payload,
    get_demo_script_payload,
    get_judge_evidence_pack_payload,
    get_technical_proof_payload,
    render_judge_evidence_pack_html,
)


def test_judge_pack_payload_and_metrics():
    payload = get_judge_evidence_pack_payload()
    assert payload["phase"] == "Phase 39 - Final Judge Evidence Pack"
    assert payload["status"] == "READY"
    for key, expected in {
        "syntheticOnly": True, "advisoryOnly": True, "realWorldDataUsed": False,
        "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False,
        "runtimePyTorchRequired": False, "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False, "databaseRequired": False,
        "persistenceEnabled": False,
    }.items():
        assert payload[key] is expected
    assert payload["headlineMetrics"] == {
        "trainingRows": 171000, "faultPrototypeCount": 38, "featureWeightCount": 19,
        "neuralFaultAccuracy": 0.9551, "neuralBehaviorAccuracy": 0.9952,
        "distilledFaultAccuracy": 0.7725, "distilledBehaviorAccuracy": 0.9406,
    }
    routes = {item["route"] for item in payload["topJudgeRoutes"]}
    assert len(routes) == 11
    assert {"/command-center", "/case-walkthroughs", "/fault-atlas", "/large-scale-data-lab"} <= routes


def test_supporting_evidence_and_html():
    demo = get_demo_script_payload()
    assert {"60SecondPitch", "threeMinuteDemo", "fiveMinuteDemo"} <= demo["pitches"].keys()
    assert demo["exactRouteOrder"][0] == "/command-center"
    proof = get_technical_proof_payload()
    assert proof["runtimeBoundary"]["stdlibOnly"] is True
    assert proof["runtimeBoundary"]["externalServiceRequired"] is False
    boundary = get_claims_boundary_payload()
    assert boundary["whatWeClaim"] and boundary["whatWeDoNotClaim"]
    page = render_judge_evidence_pack_html()
    for text in ("Final Judge Evidence Pack", "Claims boundary", "Demo path", "Synthetic-only", "Advisory-only", "Fault Atlas"):
        assert text in page
    assert "https://" not in page and "<script" not in page.lower()
