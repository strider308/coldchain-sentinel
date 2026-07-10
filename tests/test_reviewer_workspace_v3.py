import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reviewer_workspace_v3 import (  # noqa: E402
    ALLOWED_REVIEWER_ACTIONS,
    CASE_IDS,
    REVIEWER_WORKFLOW_STATES,
    get_case_reviewer_workspace_payload,
    get_reviewer_workspace_payload,
    render_reviewer_workspace_html,
)


class ReviewerWorkspaceV3Tests(unittest.TestCase):
    def test_overview_shape_and_safety_boundaries(self):
        payload = get_reviewer_workspace_payload()
        self.assertEqual(payload["phase"], "Phase 17 - Reviewer Workspace v3")
        self.assertEqual(payload["status"], "READY")
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertFalse(payload["runtimeExternalServiceRequired"])
        self.assertFalse(payload["runtimeGpuRequired"])
        self.assertTrue(payload["deterministicRulesAuthoritative"])
        self.assertFalse(payload["autonomousActionsAllowed"])
        self.assertFalse(payload["databaseRequired"])
        self.assertEqual(payload["reviewerWorkflowStates"], list(REVIEWER_WORKFLOW_STATES))
        self.assertEqual([item["caseId"] for item in payload["caseWorkspaces"]], list(CASE_IDS))

    def test_each_case_workspace_is_static_and_action_limited(self):
        for case_id in CASE_IDS:
            payload = get_case_reviewer_workspace_payload(case_id)
            workspace = payload["caseWorkspace"]
            self.assertEqual(workspace["caseId"], case_id)
            self.assertIn(workspace["reviewStatus"], REVIEWER_WORKFLOW_STATES)
            self.assertEqual(workspace["allowedReviewerActions"], list(ALLOWED_REVIEWER_ACTIONS))
            self.assertTrue(workspace["evidenceTabs"])
            self.assertTrue(workspace["checklist"])
            self.assertTrue(workspace["suggestedReviewerNotes"])
            self.assertTrue(workspace["blockedActions"])
            self.assertEqual(
                set(workspace["routeLinks"]),
                {"auditLedger", "incidentReplay", "humanReviewWorkbench", "sers", "fireworksAdvisory"},
            )

    def test_unknown_case_is_rejected(self):
        with self.assertRaises(KeyError):
            get_case_reviewer_workspace_payload("unknown")

    def test_html_has_queue_checklist_and_boundary_language(self):
        page = render_reviewer_workspace_html()
        self.assertIn("Reviewer queue", page)
        self.assertIn("Reviewer checklist", page)
        self.assertIn("Static synthetic reviewer workflow, no operational action.", page)
        self.assertIn("Synthetic-only", page)
        self.assertIn("<style>", page)

    def test_forbidden_positive_claims_absent(self):
        content = (json.dumps(get_reviewer_workspace_payload()) + render_reviewer_workspace_html()).lower()
        forbidden = [
            "production" + " validated",
            "pharma" + " validated",
            "real-world" + " validated",
            "compliance" + " certified",
            "production" + "-ready",
            "production" + " ready",
            "autonomous " + "release",
            "autonomous " + "quarantine",
            "autonomous " + "discard",
            "autonomous " + "reroute",
            "customer" + " notification",
        ]
        for claim in forbidden:
            self.assertNotIn(claim, content)


if __name__ == "__main__":
    unittest.main()
