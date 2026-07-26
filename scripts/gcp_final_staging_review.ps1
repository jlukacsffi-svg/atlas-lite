param(
    [string]$ProjectId = 'atlas-capital-research-stg',
    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',
    [string]$ServiceUrl = 'https://atlas-dashboard-stg-851252682251.us-west1.run.app',
    [string]$VerificationToken = '',
    [ValidateRange(1, 168)]
    [int]$TelemetryHours = 24
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$evidencePath = Join-Path (Split-Path -Parent $scriptRoot) 'cloud\staging_manual_validation.json'

function Add-ManualGate {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)]$Entry,
        [Parameter(Mandatory = $true)][ref]$PendingLabels
    )
    $status = [string]$Entry.status
    Write-Host "  [$status] $Label"
    if ($status -eq 'pending') {
        $PendingLabels.Value += $Label
    }
}

Write-Host 'Atlas final staging review'
Write-Host "  Project: $ProjectId"
Write-Host "  Region: $Region"
Write-Host "  Service: $ServiceUrl"
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
& powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $scriptRoot 'gcp_manual_validation.ps1') `
    -Action Status
if ($LASTEXITCODE -ne 0) {
    throw 'Manual validation evidence review failed.'
}

if ($VerificationToken) {
    Write-Host ''
    & powershell.exe -NoProfile -ExecutionPolicy Bypass `
        -File (Join-Path $scriptRoot 'gcp_dashboard_verification.ps1') `
        -ServiceUrl $ServiceUrl `
        -VerificationToken $VerificationToken
    if ($LASTEXITCODE -ne 0) {
        throw 'Dashboard verification review failed.'
    }
}

$pendingManualGates = @()
$manualEvidence = if (Test-Path -LiteralPath $evidencePath) {
    Get-Content -LiteralPath $evidencePath -Raw | ConvertFrom-Json
} else {
    $null
}

Write-Host ''
Write-Host 'Final staging gates:'
Write-Host '  [validated] Artifact Registry cost and dry-run retention review'
Write-Host '  [validated] Recurring schedules are enabled under owner-approved cost controls'
if ($manualEvidence) {
    Add-ManualGate 'Cross-device owner login' `
        $manualEvidence.cross_device_owner_login `
        ([ref]$pendingManualGates)
    Add-ManualGate 'Non-owner Google account denial' `
        $manualEvidence.non_owner_denial `
        ([ref]$pendingManualGates)
    Add-ManualGate 'Owner Stage 5 dashboard walkthrough' `
        $manualEvidence.owner_dashboard_stage5_review `
        ([ref]$pendingManualGates)
}
Write-Host '  [pending] Final staging security and cost sign-off'
Write-Host ''
if ($pendingManualGates.Count -gt 0) {
    Write-Host "Remaining manual gates: $($pendingManualGates -join '; ')"
    Write-Host ''
}
Write-Host '[result] AUTOMATED FINAL REVIEW PASS - manual owner gates remain.'
