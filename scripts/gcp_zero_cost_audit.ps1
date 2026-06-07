param(
    [string]$ProjectId = 'atlas-capital-research-stg'
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$Bq = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\bq.cmd'

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}

$findings = [System.Collections.Generic.List[string]]::new()

$billing = & $Gcloud billing projects describe $ProjectId `
    '--format=value(billingEnabled)'
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read billing status for project: $ProjectId"
}
if ($billing -ne 'False') {
    $findings.Add("Billing is enabled: $billing")
}

$buckets = & $Gcloud storage buckets list `
    "--project=$ProjectId" `
    '--format=value(name)'
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list storage buckets for project: $ProjectId"
}
if (($buckets | Out-String).Trim()) {
    $findings.Add('One or more Cloud Storage buckets exist.')
}

$enabledServices = & $Gcloud services list `
    '--enabled' `
    "--project=$ProjectId" `
    '--format=value(config.name)'
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list enabled services for project: $ProjectId"
}
$deploymentServices = @(
    'artifactregistry.googleapis.com',
    'billingbudgets.googleapis.com',
    'cloudbuild.googleapis.com',
    'cloudscheduler.googleapis.com',
    'iap.googleapis.com',
    'run.googleapis.com',
    'secretmanager.googleapis.com'
)
foreach ($service in $deploymentServices) {
    if ($enabledServices -contains $service) {
        $findings.Add("Deployment service is enabled: $service")
    }
}

if (Test-Path $Bq) {
    $datasets = & $Bq ls "--project_id=$ProjectId" '--format=prettyjson'
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to list BigQuery datasets for project: $ProjectId"
    }
    $parsed = if (($datasets | Out-String).Trim()) {
        $datasets | ConvertFrom-Json
    } else {
        @()
    }
    if (@($parsed).Count -gt 0) {
        $findings.Add('One or more BigQuery datasets exist.')
    }
}

Write-Host 'Atlas Google Cloud zero-cost audit'
Write-Host "  Project: $ProjectId"
Write-Host "  Billing enabled: $billing"
Write-Host "  Buckets: $(if (($buckets | Out-String).Trim()) { 'present' } else { 'none' })"
Write-Host "  Deployment APIs: $(if ($findings | Where-Object { $_ -like 'Deployment service*' }) { 'enabled' } else { 'none' })"

if ($findings.Count -gt 0) {
    foreach ($finding in $findings) {
        Write-Host "  [warning] $finding"
    }
    throw 'Atlas zero-cost audit failed.'
}

Write-Host '[ok] Zero-cost gate verified. No billing link or Atlas cloud resources detected.'
