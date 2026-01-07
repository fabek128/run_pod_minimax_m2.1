$ErrorActionPreference = "Stop"

param(
  [string]$PodId = $env:RUNPOD_POD_ID,
  [string]$PodName = $env:RUNPOD_POD_NAME,
  [int]$PrivatePort = 8000,
  [string]$EnvFile = (Join-Path $PSScriptRoot "..\\..\\.env")
)

function Load-EnvFile {
  param([string]$Path)
  $map = @{}
  if (-not (Test-Path $Path)) { return $map }
  Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $parts = $line.Split("=", 2)
    if ($parts.Length -eq 2) {
      $name = $parts[0].Trim()
      $value = $parts[1].Trim()
      if ($name) { $map[$name] = $value }
    }
  }
  return $map
}

$envMap = Load-EnvFile -Path $EnvFile
if (-not $env:RUNPOD_API_KEY -and $envMap.ContainsKey("RUNPOD_API_KEY")) {
  $env:RUNPOD_API_KEY = $envMap["RUNPOD_API_KEY"]
}

if (-not $env:RUNPOD_API_KEY) {
  throw "RUNPOD_API_KEY is required. Set it in the environment or in $EnvFile."
}

$query = @"
query Pods {
  myself {
    pods {
      id
      name
      status
      endpoint {
        host
        ports {
          privatePort
          publicPort
        }
      }
    }
  }
}
"@

$body = @{ query = $query } | ConvertTo-Json -Depth 5
$resp = Invoke-RestMethod `
  -Method Post `
  -Uri "https://api.runpod.io/graphql" `
  -Headers @{ Authorization = "Bearer $env:RUNPOD_API_KEY" } `
  -ContentType "application/json" `
  -Body $body

if ($resp.errors) {
  $err = $resp.errors | ConvertTo-Json -Depth 5
  throw "RunPod API error: $err"
}

$pods = $resp.data.myself.pods
if (-not $pods) {
  throw "No pods found for this account."
}

$selected = $null
if ($PodId) {
  $selected = $pods | Where-Object { $_.id -eq $PodId } | Select-Object -First 1
} elseif ($PodName) {
  $selected = $pods | Where-Object { $_.name -eq $PodName } | Select-Object -First 1
} else {
  $selected = $pods | Where-Object { $_.endpoint -and $_.endpoint.host } | Select-Object -First 1
}

if (-not $selected) {
  throw "Pod not found. Provide -PodId or -PodName, or set RUNPOD_POD_ID/RUNPOD_POD_NAME."
}

$endpoint = $selected.endpoint
if (-not $endpoint -or -not $endpoint.host) {
  throw "Pod has no endpoint host yet."
}

$host = $endpoint.host
if ($host -notmatch '^https?://') {
  $host = "https://$host"
}

$publicPort = $null
if ($endpoint.ports) {
  $match = $endpoint.ports | Where-Object { $_.privatePort -eq $PrivatePort } | Select-Object -First 1
  if ($match) {
    $publicPort = $match.publicPort
  } else {
    $publicPort = ($endpoint.ports | Select-Object -First 1).publicPort
  }
}

try {
  $uri = [Uri]$host
} catch {
  throw "Invalid endpoint host: $host"
}

$hasPortInHost = -not $uri.IsDefaultPort
if ($publicPort -and -not $hasPortInHost -and ($publicPort -notin 80, 443)) {
  $host = "$($uri.Scheme)://$($uri.Host):$publicPort"
}

$baseUrl = $host.TrimEnd("/") + "/v1"

$lines = @()
if (Test-Path $EnvFile) {
  $lines = Get-Content $EnvFile
}

$found = $false
$updated = $lines | ForEach-Object {
  if ($_ -match '^VLLM_BASE_URL=') {
    $found = $true
    "VLLM_BASE_URL=$baseUrl"
  } else {
    $_
  }
}

if (-not $lines) { $updated = @() }
if (-not $found) { $updated += "VLLM_BASE_URL=$baseUrl" }

$updated | Set-Content -Path $EnvFile -Encoding ascii

Write-Host "Updated VLLM_BASE_URL in $EnvFile"
Write-Host "Pod: $($selected.name) ($($selected.id))"
Write-Host "Base URL: $baseUrl"
