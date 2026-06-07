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
    [string]$GoogleClientIdSecret = 'atlas-google-oauth-client-id',
    [string]$GoogleClientSecretSecret = 'atlas-google-oauth-client-secret',
    [string]$SessionSecret = 'atlas-session-secret',
    [switch]$Apply,
    [switch]$ConfirmCosts
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$Repository = 'atlas-containers'
$Service = 'atlas-dashboard-stg'
$Bucket = "$ProjectId-atlas-private"
$DashboardServiceAccount = "atlas-dashboard-stg@$ProjectId.iam.gserviceaccount.com"
$OAuthSecrets = @(
    $GoogleClientIdSecret,
    $GoogleClientSecretSecret,
    $SessionSecret
)

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
$ServiceUrl = "https://$Service-$projectNumber.$Region.run.app"
$RedirectUri = "$ServiceUrl/oauth/callback"

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
Write-Host "  OAuth callback: $RedirectUri"
Write-Host "  Mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"

foreach ($secretName in $OAuthSecrets) {
    Invoke-Gcloud @(
        'secrets', 'describe', $secretName,
        "--project=$ProjectId"
    )
}

foreach ($secretName in $OAuthSecrets) {
    Invoke-Gcloud @(
        'secrets', 'add-iam-policy-binding', $secretName,
        "--project=$ProjectId",
        "--member=serviceAccount:$DashboardServiceAccount",
        '--role=roles/secretmanager.secretAccessor'
    )
}

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
    '--allow-unauthenticated',
    '--no-iap',
    '--min=0',
    '--max=1',
    '--cpu=1',
    '--memory=512Mi',
    '--concurrency=20',
    '--timeout=60',
    "--set-env-vars=ATLAS_WEB_MODE=cloud,ATLAS_AUTH_MODE=google_oauth,ATLAS_OWNER_EMAIL=$OwnerEmail,ATLAS_OAUTH_REDIRECT_URI=$RedirectUri,ATLAS_GCS_BUCKET=$Bucket,ATLAS_GCS_PREFIX=owner-v1,ATLAS_DATA_ROOT=/tmp/atlas-data",
    "--set-secrets=ATLAS_GOOGLE_CLIENT_ID=$GoogleClientIdSecret`:latest,ATLAS_GOOGLE_CLIENT_SECRET=$GoogleClientSecretSecret`:latest,ATLAS_SESSION_SECRET=$SessionSecret`:latest"
)

Write-Host ''
if ($Apply) {
    Write-Host '[ok] Staging dashboard deployment requested.'
    Write-Host "Open $ServiceUrl and verify owner-only Google sign-in."
} else {
    Write-Host '[plan] No image was built and no service was deployed.'
    Write-Host 'Re-run with -Apply -ConfirmCosts only after owner cost approval.'
}
