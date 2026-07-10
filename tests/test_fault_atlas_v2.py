import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fault_atlas_v2 import (  # noqa: E402
    get_fault_atlas_coverage_payload,
    get_fault_atlas_payload,
    get_fault_detail_payload,
    render_fault_atlas_html,
)


def test_fault_atlas_payload_and_coverage():
    payload = get_fault_atlas_payload()
    assert payload["phase"] == "Phase 41 - Fault Universe Error Atlas"
    assert payload["status"] == "READY"
    assert payload["faultCount"] == len(payload["faultRows"]) == 38
    assert payload["featureCount"] == 19
    assert payload["syntheticOnly"] is payload["advisoryOnly"] is True
    for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed"):
        assert payload[key] is False
    expected = {"thermal_behavior", "environmental_exposure", "handling_event", "sensor_device_fault", "network_gateway_fault", "data_quality_fault", "identity_mapping_fault", "mixed_evidence_fault"}
    assert set(payload["categoryGroups"]) == expected
    coverage = get_fault_atlas_coverage_payload()
    assert sum(coverage["categoryCounts"].values()) == 38
    assert len(coverage["faults"]) == 38


@pytest.mark.parametrize("fault_id", ["door_open_warming", "gateway_delay", "unresolved_mapping_risk", "single_sensor_false_spike", "mixed_quality_evidence"])
def test_fault_detail(fault_id):
    detail = get_fault_detail_payload(fault_id)
    assert detail["faultId"] == fault_id
    assert detail["featureSignals"] and detail["inspectFirst"]
    assert len(detail["blockedOperationalActions"]) == 5
    assert detail["syntheticOnly"] is detail["advisoryOnly"] is True


def test_unknown_fault_and_html():
    with pytest.raises(KeyError):
        get_fault_detail_payload("unknown-fault")
    page = render_fault_atlas_html()
    assert "Fault Universe / Error Atlas" in page
    assert page.count('scope="row"') == 38
    assert "Synthetic-only" in page and "Advisory-only" in page
    assert "https://" not in page and "<script" not in page.lower()
