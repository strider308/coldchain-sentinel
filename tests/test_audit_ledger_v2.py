import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_ledger_v2 import CASE_IDS, get_audit_ledger_payload, get_case_audit_ledger_payload, render_audit_ledger_html


class AuditLedgerV2Tests(unittest.TestCase):
    def test_payload_shape_and_boundaries(self):
        payload = get_audit_ledger_payload()
        self.assertEqual(payload["phase"], "Phase 16 - Evidence Audit Ledger")
        self.assertEqual(payload["status"], "READY")
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"):
            self.assertTrue(payload[key])
        for key in ("runtimeExternalServiceRequired", "runtimeGpuRequired", "autonomousActionsAllowed"):
            self.assertFalse(payload[key])

    def test_case_ledgers_and_required_step_fields(self):
        required = {"stepId", "label", "sourceModule", "evidenceRoute", "status", "humanMeaning", "safetyBoundary"}
        route_suffixes = (
            "raw-sensor-window.json", "normalized-sensor-window.json", "quality-events.json",
            "consensus-report.json", "risk-timeline.json", "review-workbench", "fireworks-advisory.json", "trace.json",
        )
        self.assertEqual({item["caseId"] for item in get_audit_ledger_payload()["caseLedgers"]}, set(CASE_IDS))
        for case_id in CASE_IDS:
            payload = get_case_audit_ledger_payload(case_id)
            self.assertEqual(payload["caseId"], case_id)
            self.assertEqual(len(payload["ledgerSteps"]), 8)
            self.assertTrue(all(required <= step.keys() for step in payload["ledgerSteps"]))
            self.assertEqual([step["sequenceLabel"] for step in payload["ledgerSteps"]], [f"SEQ-{n:02d}" for n in range(1, 9)])
            self.assertTrue(all(expected in step["evidenceRoute"] for step, expected in zip(payload["ledgerSteps"], route_suffixes)))

    def test_route_map_and_html_boundary(self):
        payload = get_audit_ledger_payload()
        self.assertEqual(payload["routeMap"]["auditLedger"], "/audit-ledger")
        self.assertEqual(payload["routeMap"]["auditLedgerJson"], "/audit-ledger.json")
        self.assertIn("audit-style synthetic evidence trail, not compliance certification", render_audit_ledger_html().lower())

    def test_forbidden_positive_claims_absent(self):
        text = json.dumps(get_audit_ledger_payload(), sort_keys=True).lower()
        text += "".join(json.dumps(get_case_audit_ledger_payload(case_id), sort_keys=True).lower() for case_id in CASE_IDS)
        forbidden = [
            "production" + "-ready",
            "pharma" + " validated",
            "real-world" + " validated",
            "compliance" + " certified",
            "autonomous" + " release",
            "autonomous" + " quarantine",
            "autonomous" + " discard",
            "autonomous" + " reroute",
            "customer" + " notification",
        ]
        for claim in forbidden:
            self.assertNotIn(claim, text)


if __name__ == "__main__":
    unittest.main()
