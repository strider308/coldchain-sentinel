param(
  [string]$Repo = "C:\dev\ColdChainSentinel",
  [string]$RenderCli = "C:\tools\render\render.exe"
)

$ErrorActionPreference = "Continue"

function Section($Name) {
  Write-Host "`n=== $Name ===" -ForegroundColor Cyan
}

function Pass($Message) {
  Write-Host "PASS: $Message" -ForegroundColor Green
}

function Warn($Message) {
  Write-Host "WARN: $Message" -ForegroundColor Yellow
}

function Fail($Message) {
  Write-Host "FAIL: $Message" -ForegroundColor Red
}

Section "Folder and git repo"

if (!(Test-Path $Repo)) {
  Fail "Repo folder missing: $Repo"
  exit 1
}

Set-Location $Repo

git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -eq 0) {
  Pass "Inside git repo"
  Write-Host "Git root:"
  git rev-parse --show-toplevel
  Write-Host "Branch:"
  git branch --show-current
  Write-Host "Remote:"
  git remote -v
} else {
  Fail "Not inside git repo"
}

Section "Local-only CodeGraph ignore rules"

$gitignore = ""
if (Test-Path ".gitignore") {
  $gitignore = Get-Content ".gitignore" -Raw
}

foreach ($pattern in @(".codegraph/", ".gortex/", ".repograph/")) {
  if ($gitignore -match [regex]::Escape($pattern)) {
    Pass "$pattern ignored"
  } else {
    Fail "$pattern not ignored"
  }
}

Section "Required files"

$requiredFiles = @(
  "Dockerfile",
  "src\serve_dashboard.py",
  "src\serve_dashboard_amd.py",
  "src\sensor_data_model_v2.py",
  "src\data_quality_v2.py",
  "src\consensus_v2.py",
  "docs\TOOLING_INITIALIZATION.md",
  "docs\PLANNED_TOOL_ADOPTION_MATRIX.md"
)

foreach ($file in $requiredFiles) {
  if (Test-Path $file) {
    Pass $file
  } else {
    Fail "Missing $file"
  }
}

Section "Tool detection"

$tools = @("git", "python", "docker", "node", "npm", "npx", "gitleaks", "trufflehog", "gortex", "codegraph")

foreach ($tool in $tools) {
  $cmd = Get-Command $tool -ErrorAction SilentlyContinue
  if ($cmd) {
    Pass "$tool found at $($cmd.Source)"
    try {
      if ($tool -eq "gortex") {
        & $tool version 2>&1 | Select-Object -First 3
      } else {
        & $tool --version 2>&1 | Select-Object -First 3
      }
    } catch {
      Warn "$tool exists but --version failed"
    }
  } else {
    Warn "$tool not found"
  }
}

if (Test-Path $RenderCli) {
  Pass "Render CLI found at $RenderCli"
  & $RenderCli --version 2>&1 | Select-Object -First 3
} else {
  Warn "Render CLI not found at $RenderCli"
}

Section "CodeGraph / gortex discovery"

New-Item -ItemType Directory -Force artifacts\tooling | Out-Null

$gortex = Get-Command gortex -ErrorAction SilentlyContinue
$codegraph = Get-Command codegraph -ErrorAction SilentlyContinue

if ($gortex) {
  Pass "gortex detected"
  "=== gortex --help ===" | Set-Content artifacts\tooling\codegraph-discovery.log
  gortex --help 2>&1 | Tee-Object -Append artifacts\tooling\codegraph-discovery.log
  "`n=== gortex repos ===" | Tee-Object -Append artifacts\tooling\codegraph-discovery.log
  gortex repos 2>&1 | Tee-Object -Append artifacts\tooling\codegraph-discovery.log
} elseif ($codegraph) {
  Pass "codegraph detected"
  "=== codegraph --help ===" | Set-Content artifacts\tooling\codegraph-discovery.log
  codegraph --help 2>&1 | Tee-Object -Append artifacts\tooling\codegraph-discovery.log
} else {
  Warn "No gortex/codegraph command detected. Install/init cannot be safely guessed."
}

Section "App self-checks"

python src\serve_dashboard.py --check
if ($LASTEXITCODE -eq 0) {
  Pass "Base dashboard self-check"
} else {
  Fail "Base dashboard self-check failed"
}

python src\serve_dashboard_amd.py --check
if ($LASTEXITCODE -eq 0) {
  Pass "AMD wrapper dashboard self-check"
} else {
  Fail "AMD wrapper dashboard self-check failed"
}

Section "Docker availability"

docker --version
docker info *> $null
if ($LASTEXITCODE -eq 0) {
  Pass "Docker engine running"
} else {
  Warn "Docker installed but engine may not be running"
}

Section "Git status"

git status --short

Write-Host "`nTooling health check complete." -ForegroundColor Cyan

