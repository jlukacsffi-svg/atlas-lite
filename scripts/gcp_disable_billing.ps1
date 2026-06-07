param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}

$billingEnabled = & $Gcloud billing projects describe $ProjectId `
    '--format=value(billingEnabled)'
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read billing status for project: $ProjectId"
}

Write-Host 'Atlas emergency billing stop'
Write-Host "  Project: $ProjectId"
Write-Host "  Billing enabled: $billingEnabled"
Write-Host "  Mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"

if ($billingEnabled -ne 'True') {
    Write-Host '[ok] Billing is already disabled. No change is needed.'
    exit 0
}

if (-not $Apply) {
    Write-Host "[plan] gcloud billing projects unlink $ProjectId"
    Write-Host '[plan] No cloud settings were changed.'
    Write-Host 'Warning: applying this command stops billable services and may cause data loss.'
    exit 0
}

& $Gcloud billing projects unlink $ProjectId
if ($LASTEXITCODE -ne 0) {
    throw "Failed to disable billing for project: $ProjectId"
}

Write-Host '[ok] Billing was disabled for the project.'
Write-Host 'Check for delayed charges incurred before billing was disabled.'
