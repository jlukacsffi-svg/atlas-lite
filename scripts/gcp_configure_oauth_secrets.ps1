param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [string]$OAuthClientJson,

    [string]$GoogleClientIdSecret = 'atlas-google-oauth-client-id',
    [string]$GoogleClientSecretSecret = 'atlas-google-oauth-client-secret',
    [string]$SessionSecret = 'atlas-session-secret',
    [switch]$Apply,
    [switch]$ConfirmCosts
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}
if ($Apply -and -not $ConfirmCosts) {
    throw 'Secret Manager can create charges. Re-run with -Apply -ConfirmCosts only after owner approval.'
}

Write-Host 'Atlas Google OAuth secret configuration'
Write-Host "  Project: $ProjectId"
Write-Host "  OAuth file: $OAuthClientJson"
Write-Host "  Mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"

if (-not $Apply) {
    Write-Host "[plan] Validate the downloaded Google OAuth web-client JSON."
    Write-Host "[plan] Create these Secret Manager secrets if absent:"
    Write-Host "       $GoogleClientIdSecret"
    Write-Host "       $GoogleClientSecretSecret"
    Write-Host "       $SessionSecret"
    Write-Host '[plan] Add one new version to each secret without printing values.'
    Write-Host '[plan] No cloud resources or secret versions were changed.'
    exit 0
}

if (-not (Test-Path -LiteralPath $OAuthClientJson -PathType Leaf)) {
    throw "OAuth client file not found: $OAuthClientJson"
}

$credentials = Get-Content -LiteralPath $OAuthClientJson -Raw | ConvertFrom-Json
if (-not $credentials.web.client_id -or -not $credentials.web.client_secret) {
    throw 'Expected a Google OAuth Web application client JSON file.'
}
$clientId = [string]$credentials.web.client_id
$clientSecret = [string]$credentials.web.client_secret
$sessionBytes = New-Object byte[] 48
[System.Security.Cryptography.RandomNumberGenerator]::Fill($sessionBytes)
$sessionValue = [Convert]::ToBase64String($sessionBytes)

function Ensure-Secret {
    param([Parameter(Mandatory = $true)][string]$Name)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    & $Gcloud secrets describe $Name --project=$ProjectId --quiet *> $null
    $exists = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $previousPreference
    if ($exists) {
        Write-Host "[ok] Secret exists: $Name"
        return
    }
    Write-Host "[apply] Creating secret: $Name"
    & $Gcloud secrets create $Name `
        --project=$ProjectId `
        --replication-policy=automatic `
        --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create secret: $Name"
    }
}

function Add-SecretVersion {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )
    $tempPath = Join-Path (
        [System.IO.Path]::GetTempPath()
    ) ("atlas-secret-" + [Guid]::NewGuid().ToString('N'))
    try {
        [System.IO.File]::WriteAllText(
            $tempPath,
            $Value,
            [System.Text.UTF8Encoding]::new($false)
        )
        Write-Host "[apply] Adding redacted secret version: $Name"
        & $Gcloud secrets versions add $Name `
            --project=$ProjectId `
            "--data-file=$tempPath" `
            --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Could not add secret version: $Name"
        }
    } finally {
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force
        }
    }
}

foreach ($name in @(
    $GoogleClientIdSecret,
    $GoogleClientSecretSecret,
    $SessionSecret
)) {
    Ensure-Secret -Name $name
}

Add-SecretVersion -Name $GoogleClientIdSecret -Value $clientId
Add-SecretVersion -Name $GoogleClientSecretSecret -Value $clientSecret
Add-SecretVersion -Name $SessionSecret -Value $sessionValue

Write-Host ''
Write-Host '[ok] OAuth and session secrets are stored in Secret Manager.'
Write-Host 'Delete the downloaded OAuth JSON after the dashboard is verified.'
