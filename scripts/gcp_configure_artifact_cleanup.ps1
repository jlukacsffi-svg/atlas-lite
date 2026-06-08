param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',

    [string]$PolicyFile = '',
    [switch]$Apply,
    [switch]$ConfirmCosts,
    [switch]$ActivateDeletion
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$Repository = 'atlas-containers'
if (-not $PolicyFile) {
    $PolicyFile = Join-Path $PSScriptRoot '..\cloud\artifact_cleanup_policy.json'
}
$PolicyFile = (Resolve-Path $PolicyFile).Path

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}
if ($Apply -and -not $ConfirmCosts) {
    throw 'Repository changes require -Apply -ConfirmCosts after owner review.'
}
if ($ActivateDeletion -and -not $Apply) {
    throw 'Activating deletion requires -Apply.'
}

$mode = if ($ActivateDeletion) { 'ACTIVE DELETION' } else { 'DRY RUN' }
Write-Host 'Atlas Artifact Registry cleanup'
Write-Host "  Project: $ProjectId"
Write-Host "  Repository: $Repository"
Write-Host "  Policy: $PolicyFile"
Write-Host "  Cleanup mode: $mode"
Write-Host "  Command mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"
Write-Host '  Policy keeps the three newest versions and targets only versions older than 14 days.'

$arguments = @(
    'artifacts', 'repositories', 'set-cleanup-policies', $Repository,
    "--project=$ProjectId",
    "--location=$Region",
    "--policy=$PolicyFile"
)
if (-not $ActivateDeletion) {
    $arguments += '--dry-run'
}

if (-not $Apply) {
    Write-Host ('[plan] gcloud ' + ($arguments -join ' '))
    Write-Host '[plan] No cleanup policy was changed.'
    exit 0
}

& $Gcloud @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'Artifact Registry cleanup policy update failed.'
}
if ($ActivateDeletion) {
    Write-Host '[ok] Active cleanup is configured. Artifact Registry applies it asynchronously.'
} else {
    Write-Host '[ok] Cleanup policy is configured in dry-run mode; no images will be deleted.'
}
