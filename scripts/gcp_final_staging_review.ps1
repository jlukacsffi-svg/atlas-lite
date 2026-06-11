param(
    [string]$ProjectId = 'atlas-capital-research-stg',
    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',
    [ValidateRange(1, 168)]
    [int]$TelemetryHours = 24
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host 'Atlas final staging review'
Write-Host "  Project: $ProjectId"
Write-Host "  Region: $Region"
Write-Host "  Telemetry window: $TelemetryHours hours"
Write-Host '  Mode: READ ONLY'
Write-Host ''

& powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $scriptRoot 'gcp_staging_status.ps1') `
    -ProjectId $ProjectId `
    -Region $Region
if ($LASTEXITCODE -ne 0) {
    throw 'Staging status review failed.'
}

Write-Host ''
& powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $scriptRoot 'gcp_staging_readiness.ps1') `
    -ProjectId $ProjectId `
    -Region $Region
if ($LASTEXITCODE -ne 0) {
    throw 'Staging readiness review failed.'
}

Write-Host ''
& powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $scriptRoot 'gcp_uptime_report.ps1') `
    -ProjectId $ProjectId `
    -Hours $TelemetryHours
$uptimeExitCode = $LASTEXITCODE
if ($uptimeExitCode -eq 1) {
    throw 'Uptime review returned no telemetry data.'
}
if ($uptimeExitCode -eq 2) {
    throw 'Uptime review reported failed samples.'
}
if ($uptimeExitCode -ne 0) {
    throw 'Uptime review failed unexpectedly.'
}

Write-Host ''
Write-Host 'Manual gates still require owner action:'
Write-Host '  [pending] Cross-device owner login'
Write-Host '  [pending] Non-owner Google account denial'
Write-Host '  [pending] Artifact Registry dry-run observation review'
Write-Host '  [pending] Separate owner approval before schedule resume'
Write-Host '  [pending] Final staging security and cost sign-off'
Write-Host ''
Write-Host '[result] AUTOMATED FINAL REVIEW PASS - manual owner gates remain.'
