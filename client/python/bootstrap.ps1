$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\\..")
$envFile = Join-Path $repoRoot ".env"

if (-not (Test-Path $envFile)) {
  throw ".env not found in repo root. Copy .env.example to .env and edit it first."
}

Write-Host "Fetching RunPod endpoint and updating VLLM_BASE_URL..."
& (Join-Path $scriptDir "get_runpod_endpoint.ps1")

Write-Host "Starting client..."
& (Join-Path $scriptDir "run.ps1")
