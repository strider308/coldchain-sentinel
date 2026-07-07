# ColdChain Sentinel Public Release Readiness

Status: Batch 7 readiness plan only. No public repo was created, no deployment was created, and no private Git history was pushed.

## Public Repo Approach

Use a clean export or fresh public repository from the approved ColdChain source tree. Do not publish the full private planning history because the private history contains one old unverified local Postgres placeholder in commit `f1a870f...`; verified secrets remain 0.

Manual gate before public repo creation:

- Confirm the official submission deadline from dashboard/Discord.
- Confirm the final public repository name and visibility.
- Create the public GitHub repository manually or with explicit approval.
- Copy only the approved export manifest contents.
- Run final scans on the export before first push.
- Push only the clean export, not private history.

## Pre-Public Hygiene Checklist

- [ ] `.codegraph/` is ignored.
- [ ] `.codegraph/` is not tracked.
- [ ] Scanner output is absent.
- [ ] Local logs are absent.
- [ ] Build/cache folders are absent.
- [ ] `.env` files are absent.
- [ ] Provider credentials are absent.
- [ ] Internal-only planning artifacts are excluded unless explicitly approved.
- [ ] Generated slides, cover image, and video are absent unless intentionally created later.
- [ ] Gitleaks passes.
- [ ] TruffleHog filesystem scan passes.
- [ ] Docker build passes.
- [ ] Container route smoke passes for `/`, `/review`, `/review.json`, and `/health`.
- [ ] Validation suite passes.
- [ ] README and submission docs do not claim AMD success, Fireworks success, deployment completion, public repo creation, production readiness, real-world compliance validation, or autonomous decisions.

## Local Preflight Commands

Run from repo root:

```powershell
git status --short
git check-ignore -v .codegraph/
git ls-files .codegraph/
python projects/coldchain/src/coldchain_baseline.py
python projects/coldchain/src/serve_dashboard.py --check
python projects/coldchain/tests/test_coldchain_validation.py
& ".\scripts\validation\validate-json.ps1"
git diff --check
docker build -t coldchain-sentinel:local projects/coldchain
gitleaks detect --source . --verbose --redact
trufflehog filesystem . --no-update --fail
```

Container route smoke:

```powershell
docker run --rm -p 8080:8080 coldchain-sentinel:local
```

Then check:

- `http://127.0.0.1:8080/`
- `http://127.0.0.1:8080/review`
- `http://127.0.0.1:8080/review.json`
- `http://127.0.0.1:8080/health`

## Deployment Readiness

No deployment is created in Batch 7. Demo app URL/platform remains pending.

Recommended target options:

- Container host that can run the existing Docker image.
- App host that can run the Python stdlib server behind an HTTPS endpoint.
- Static hosting only if a later approved batch converts the demo into static assets.

Container-based deployment path:

- Build from `projects/coldchain/Dockerfile`.
- Expose container port `8080`.
- Route platform traffic to the app root.
- Keep provider-disabled baseline mode.
- Set no environment variables for the baseline deterministic demo.
- Do not add provider credentials.

Required health route:

- `/health`

Smoke-test checklist after deployment:

- [ ] `/` returns 200 and shows synthetic demo data.
- [ ] `/review` returns 200 and shows human review required.
- [ ] `/review.json` returns 200 and valid JSON.
- [ ] `/health` returns 200 and provider-disabled status.
- [ ] `PAL-SYN-1004` unresolved mapping remains visible.
- [ ] Final disposition remains blocked.
- [ ] No autonomous release, quarantine, discard, reroute, or customer notification wording is present.

Rollback plan:

- Keep the last locally validated image tag.
- Disable or remove any future provider addendum path if it fails.
- Revert public demo to the provider-disabled deterministic baseline.
- Re-run route smoke and security scans after rollback.

Public demo safety wording:

- Synthetic demo data only.
- Deterministic rules are authoritative.
- Human review required.
- Final disposition blocked.
- No autonomous release, quarantine, discard, reroute, or customer notification.
- Not a validated pharmaceutical, medical, or logistics compliance product.
- No AMD or Fireworks success is claimed unless provider addendum evidence exists.

## Manual Deployment Checklist

- [ ] Public repo/export decision complete.
- [ ] Final scans pass on export.
- [x] Hosting platform selected: Render.
- [x] Baseline deployment configured without secrets.
- [x] Health route passes on Render.
- [x] Route smoke passes on Render.
- [x] Demo URL recorded in submission assets.
- [ ] Rollback path documented.

Demo app URL/platform: https://coldchain-sentinel-35ex.onrender.com on Render. Status: live provider-disabled baseline smoke-tested.
## Vercel Compatibility Decision

Vercel CLI dry-run detected framework `Other` and prepared a file upload/static-style deployment. It did not use the existing Dockerfile as a long-running container web service. Do not deploy this app to Vercel unless Vercel container support is explicitly available and verified for this project without converting the app to Next.js/serverless.

## Render Manual Fallback

Use Render for the provider-disabled container deployment unless another container-capable host is explicitly selected.

Manual Render steps:

1. Open Render dashboard.
2. Create a new Web Service.
3. Connect `https://github.com/strider308/coldchain-sentinel`.
4. Select Docker using the existing `Dockerfile`.
5. Branch: `master` unless Render shows `main`.
6. Root directory: repository root.
7. Port: `8080`.
8. Environment variables: none.
9. Confirm no secrets are added.
10. Deploy.
11. Smoke-test `/`, `/review`, `/review.json`, and `/health`.

Required smoke result:

- `/` returns 200 and shows the synthetic deterministic dashboard.
- `/review` returns 200 and shows the human review packet.
- `/review.json` returns 200 and includes unresolved `PAL-SYN-1004`.
- `/health` returns 200 and confirms provider-disabled baseline.
- No AMD, Fireworks, production-readiness, real-world compliance, or autonomous-action claim appears.
