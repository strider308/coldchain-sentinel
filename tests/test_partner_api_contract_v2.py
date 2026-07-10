import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from partner_api_contract_v2 import *
class PartnerContractTests(unittest.TestCase):
 def test_payload_contract_and_boundaries(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_partner_api_contract_payload(); h=render_partner_api_contract_html()
  self.assertEqual(p["phase"],"Phase 29 - Partner API Contract v2"); self.assertEqual(p["contractMode"],"static-demo-contract")
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative"): self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed","externalCallsMade","webhooksEnabled","secretsRequired","realPartnerIntegrationEnabled","databaseRequired","persistenceEnabled"): self.assertFalse(p[k])
  self.assertEqual(set(p["inboundContract"]["requiredFields"]),set(get_partner_sample_request_payload())); self.assertTrue(get_partner_sample_response_payload()["humanReviewRequired"]); self.assertIn("not a live partner API",h)
 def test_openapi_errors_routes_and_claims(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_partner_api_contract_payload(); api=get_openapi_preview_payload(); errors=get_partner_error_catalog_payload()["errorCatalog"]
  self.assertEqual(api["openapi"],"3.1.0"); self.assertTrue(api["staticPreviewOnly"]); self.assertIn("title",api["info"]); self.assertIn("/synthetic/advisory",api["paths"]); self.assertEqual(set(api["components"]["schemas"]),{"SyntheticSensorReading","AdvisoryResponse","ErrorResponse"}); self.assertEqual({e["code"] for e in errors},{"malformed_payload","missing_required_field","unsupported_case","unsafe_action_requested","external_service_unavailable","evidence_incomplete"}); self.assertEqual(p["routeMap"]["demoFlow"],"/demo-flow")
  self.assertEqual(p["outboundContract"]["fields"],list(get_partner_sample_response_payload()))
  for route in ("integrationSandbox","integrationReadiness","partnerApiContract","openapiPreview","errors","scenarioLibraryV4","evaluationMatrixV2","demoFlow","productionGapAnalysis"): self.assertIn(route,p["routeMap"])
  t=json.dumps(p).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(s,t)
if __name__=="__main__": unittest.main()
