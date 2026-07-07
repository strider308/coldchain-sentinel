# ColdChain Sentinel Public Export Manifest

Status: intended public-export file list only. This manifest does not create a public repo, push code, deploy, or publish private history.

## Include

Project app files:

- `projects/coldchain/README.md`
- `projects/coldchain/Dockerfile`
- `projects/coldchain/.dockerignore`
- `projects/coldchain/docker-compose.yml`
- `projects/coldchain/fixtures/baseline-shipment.json`
- `projects/coldchain/src/coldchain_baseline.py`
- `projects/coldchain/src/serve_dashboard.py`
- `projects/coldchain/tests/test_coldchain_validation.py`
- `projects/coldchain/docs/submission-assets.md`
- `projects/coldchain/docs/public-release-readiness.md`
- `projects/coldchain/docs/public-export-manifest.md`

Optional public context after review:

- `specs/002-coldchain-sentinel/implementation/track3-build-plan.md`
- `specs/002-coldchain-sentinel/evaluation/score-summary.md`

## Exclude

- `.git/`
- `.codegraph/`
- scanner output
- local logs
- build/cache folders
- `.env`
- provider credentials
- private planning history
- internal-only artifacts not approved for public submission
- generated slides, video, or cover image unless intentionally created later

## Export Gate

- [ ] Export into a fresh directory or fresh public repo.
- [ ] Confirm only included files are present.
- [ ] Run `gitleaks detect --source . --verbose --redact` inside the export.
- [ ] Run `trufflehog filesystem . --no-update --fail` inside the export.
- [ ] Build Docker image from the export.
- [ ] Run route smoke from the export.
- [ ] Confirm README and docs preserve safety boundaries.
- [ ] Push only after explicit approval.
