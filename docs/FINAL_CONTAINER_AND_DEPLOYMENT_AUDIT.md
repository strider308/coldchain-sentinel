# Final Container and Deployment Audit

Audit date: 2026-07-11
Audited baseline: `f97e58c1527c7b5f015ab2bec7930ff639ff9ad8` plus the final Alpine container hardening

This report records source, clean-build, runtime, read-only, cleanup, and Docker Scout evidence. It does not treat local container results as proof of deployed Render configuration.

## Executive result

The Dockerfile is a small single-stage stdlib runtime: official `python:3.12-alpine`, no package installation, fixed copies, non-root `appuser`, predictable `/app` workdir, one port, health check, unbuffered/no-bytecode environment, and the required unchanged command. `.dockerignore` excludes repository metadata, environment files, tests, caches, logs, build output, and local submission material.

The no-cache image build, normal container, read-only-plus-tmpfs container, runtime identity, write boundaries, health, 12-route smoke, shutdown/cleanup, and Docker Scout scan all completed. Scout reported **0 Critical, 0 High, 4 Medium, and 1 Low**. Trivy was unavailable and was not installed.

## Dockerfile and build-context evidence

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Dockerfile exists | PASS | Root `Dockerfile` reviewed. |
| Runtime command unchanged | PASS | `CMD ["python", "src/serve_dashboard_amd.py", "--host", "0.0.0.0", "--port", "8080"]`. |
| Explicit base image | PARTIAL | `python:3.12-alpine` fixes the language minor/Alpine family and eliminated the prior Debian-image Critical/High findings, but remains a mutable tag without patch version or digest. Pin a verified digest only with an owner-managed update process. |
| Multi-stage/minimal build | PASS | No compiler, build stage, or package manager is used because the app has no external runtime packages. A second stage would add no value. |
| Secret build args | PASS | No `ARG`, build secret, token, or credential declaration. |
| Fixed copy set | PASS | Only `fixtures`, `artifacts`, and `src` are copied. README, docs, tests, Git metadata, and local output are not copied. |
| `.env` excluded | PASS | `.dockerignore` excludes `.env` and `.env.*` while allowing an optional `.env.example`; Dockerfile does not copy that file. |
| `.git` excluded | PASS | `.dockerignore` excludes `.git/`; Dockerfile fixed-copy paths also exclude it. |
| Minimal context | PASS | Excludes `.codegraph`, virtual environments, caches, bytecode, logs, temp/build/coverage/browser reports, tests, and submission directories. |
| Predictable workdir | PASS | `WORKDIR /app`. |
| Non-root runtime user | PASS | Build creates `appuser` with a non-login shell and switches with `USER appuser` before runtime. |
| Application write access | PASS | As `appuser`, writing under `/app` failed in both normal and read-only runs; `/tmp` remained writable and removable for bounded temporary use. |
| Python unbuffered | PASS | `PYTHONUNBUFFERED=1`. |
| Bytecode/cache pollution | PASS | `PYTHONDONTWRITEBYTECODE=1`; `.dockerignore` also excludes existing bytecode/cache. |
| Exposed port | PASS | Only `EXPOSE 8080`; no debug/management port. |
| Health check | PASS | Both normal and read-only containers progressed to `healthy` using the bounded local `/health` check. |
| Runtime GPU/AI package | PASS | No CUDA, GPU, notebook, PyTorch, Fireworks package, compiler, or package install is present. |
| External provider required to boot | PASS | Both containers booted and served all sampled routes without provider configuration or egress. |

## Runtime and scanner evidence

| Command/evidence | Status | Result |
|---|---|---|
| `docker build --no-cache -t coldchain-sentinel-final-audit .` | PASS | Exit 0; context 1.17 MB; image `sha256:1584c24403c5bd60012542be157063b8f1e273c7d97a2a6ba0c1852188970690`; size 18,622,006 bytes. |
| Normal container smoke on host 8091 | PASS | Healthy; 12/12 positive HTML/JSON routes returned 200, five hardened paths returned typed 404, and POST returned typed 405 with defensive headers. |
| `--read-only --tmpfs /tmp` smoke | PASS | Healthy; the same positive/error/method checks passed; `/app` write failed and `/tmp` create/remove passed. |
| Runtime identity (`whoami` / inspect user) | PASS | `uid=1000(appuser)`; inspect reported `User=appuser`. |
| Graceful stop and cleanup | PASS | Both exact-name containers stopped and were removed; no audit container remains and port 8091 is free. |
| Docker Scout vulnerability scan | PARTIAL | Scout indexed 52 packages and reported 0 Critical, 0 High, 4 Medium, and 1 Low; no scanner was installed for the audit. |
| Trivy scan | NA | Trivy is not available and should not be installed solely for this audit. |

The Scout result is a point-in-time finding set, not a guarantee that the mutable base tag remains unchanged or vulnerability-free.

## Deployment controls

| Area | Status | Evidence / limitation |
|---|---|---|
| Listen interface/port | PASS | Container command listens on `0.0.0.0:8080`, matching Render expectations and the sole exposed port. |
| Debug mode | PASS | No debug flag, development reloader, management UI, or debug route is configured. |
| State/persistence | PASS | Read-only synthetic service; no database, upload, or runtime artifact write. |
| Provider egress | PASS | Fireworks calls require explicit `FIREWORKS_LIVE_ENABLED`; app boot and ordinary pages do not require egress. Platform egress restriction is external. |
| TLS termination | NOT VERIFIED | Docker serves HTTP. Render TLS/proxy configuration is external and must be validated live. |
| HSTS proxy condition | NOT VERIFIED | Handler emits HSTS only when forwarded protocol is HTTPS; trusted proxy metadata and live response require post-deploy verification. |
| Environment-secret injection | NOT VERIFIED | Dockerfile contains none; Render environment configuration and access controls are outside this repository. |
| Read-only root filesystem in deployment | PARTIAL | Local read-only-plus-tmpfs smoke passed. Whether Render enables an equivalent filesystem policy remains external. |
| Resource limits/restarts | NOT VERIFIED | CPU/memory quotas, instance count, restart policy, and request limits are Render configuration, not present in the image. |

## OpenSSF/container supply-chain considerations

| Area | Status | Evidence / action |
|---|---|---|
| Base image provenance | PARTIAL | Official Docker Hub Python Alpine image family is named, but digest/signature provenance was not recorded. |
| Dependency inventory | PASS | No application package dependencies; copied runtime is source plus JSON fixtures/artifacts. |
| Image reproducibility | PARTIAL | Mutable base tag prevents byte-for-byte reproducibility. No build-time package downloads reduce drift. |
| SBOM | NOT VERIFIED | No SBOM generation was performed. Add only if submission/deployment policy requires it. |
| Image signature | NOT VERIFIED | No signed image/release workflow is present. |
| Vulnerability state | PARTIAL | Final image: 0 Critical, 0 High, 4 Medium, 1 Low in Docker Scout. Findings and the mutable tag require normal owner review. |

## Remaining deployment verification

Local container evidence is complete. After the owner deploys the final commit, verify live TLS, headers, health, provider fallback, content types, 404 behavior, and primary routes before assigning a live verdict. Render environment-secret access, resource quotas/restarts, proxy metadata, and read-only filesystem policy remain platform settings rather than image properties.
