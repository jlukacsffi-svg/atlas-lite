param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[^@\s]+@[^@\s]+\.[^@\s]+$')]
    [string]$OwnerEmail,

    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',

    [string]$ImageTag = '',
    [switch]$Apply,
    [switch]$ConfirmCosts
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$Repository = 'atlas-containers'
$Service = 'atlas-dashboard-stg'
$Bucket = "$ProjectId-atlas-private"
$DashboardServiceAccount = "atlas-dashboard-stg@$ProjectId.iam.gserviceaccount.com"

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}
if ($Apply -and -not $ConfirmCosts) {
    throw 'Deployment can create charges. Re-run with -Apply -ConfirmCosts only after owner approval.'
}
if (-not $ImageTag) {
    $ImageTag = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss')
}

$projectNumber = if ($Apply) {
    & $Gcloud projects describe $ProjectId --format='value(projectNumber)'
} else {
    '<PROJECT_NUMBER>'
}
if ($Apply -and -not $projectNumber) {
    throw "Project not found: $ProjectId"
}

$Image = "$Region-docker.pkg.dev/$ProjectId/$Repository/atlas:$ImageTag"
$Audience = "/projects/$projectNumber/locations/$Region/services/$Service"

function Invoke-Gcloud {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $display = 'gcloud ' + ($Arguments -join ' ')
    if (-not $Apply) {
        Write-Host "[plan] $display"
        return
    }
    Write-Host "[apply] $display"
    & $Gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $display"
    }
}

Write-Host "Atlas staging deployment"
Write-Host "  Project: $ProjectId"
Write-Host "  Region: $Region"
Write-Host "  Image: $Image"
Write-Host "  Service: $Service"
Write-Host "  Owner: $OwnerEmail"
Write-Host "  Mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"

Invoke-Gcloud @(
    'builds', 'submit', '.',
    "--tag=$Image",
    "--project=$ProjectId",
    "--region=$Region"
)

Invoke-Gcloud @(
    'run', 'deploy', $Service,
    "--project=$ProjectId",
    "--region=$Region",
    "--image=$Image",
    "--service-account=$DashboardServiceAccount",
    '--no-allow-unauthenticated',
    '--iap',
    '--min=0',
    '--max=1',
    '--cpu=1',
    '--memory=512Mi',
    '--concurrency=20',
    '--timeout=60',
    "--set-env-vars=ATLAS_WEB_MODE=cloud,ATLAS_AUTH_MODE=iap,ATLAS_OWNER_EMAIL=$OwnerEmail,ATLAS_IAP_AUDIENCE=$Audience,ATLAS_GCS_BUCKET=$Bucket,ATLAS_GCS_PREFIX=owner-v1,ATLAS_DATA_ROOT=/tmp/atlas-data"
)

Invoke-Gcloud @(
    'run', 'services', 'add-iam-policy-binding', $Service,
    "--project=$ProjectId",
    "--region=$Region",
    "--member=serviceAccount:service-$projectNumber@gcp-sa-iap.iam.gserviceaccount.com",
    '--role=roles/run.invoker'
)

Invoke-Gcloud @(
    'iap', 'web', 'add-iam-policy-binding',
    "--resource-type=cloud-run",
    "--service=$Service",
    "--region=$Region",
    "--member=user:$OwnerEmail",
    '--role=roles/iap.httpsResourceAccessor',
    "--project=$ProjectId"
)

Write-Host ''
if ($Apply) {
    Write-Host '[ok] Staging dashboard deployment requested.'
    Write-Host 'Verify IAP in the Cloud Run console before sharing the URL.'
} else {
    Write-Host '[plan] No image was built and no service was deployed.'
    Write-Host 'Re-run with -Apply -ConfirmCosts only after owner cost approval.'
}
