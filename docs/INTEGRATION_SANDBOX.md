# Integration Sandbox

Phase 15 presents static synthetic request, advisory response, and rejection examples without making external calls.

## Routes

- `/integration-sandbox`
- `/integration-sandbox.json`
- `/integration-sandbox/sample-request.json`
- `/integration-sandbox/sample-response.json`
- `/integration-sandbox/rejection-example.json`

The request sample follows the Phase 2 synthetic sensor-window fields. The response is advisory-only and requires human review. The rejection example shows deterministic schema and safety checks.

## Boundaries

- Synthetic sample data only; no real customer, shipment, pharma, logistics, patient, or sensor data.
- No external calls, webhook delivery, secrets, GPU, notebooks, or external services.
- Deterministic rules remain authoritative and SERS remains advisory-only.
- No operational action or customer messaging automation.

Run the focused check with:

```text
python -m pytest -p no:cacheprovider tests/test_integration_sandbox_v2.py
```
