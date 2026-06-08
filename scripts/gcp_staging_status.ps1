param(
    [string]$ProjectId = 'atlas-capital-research-stg',
    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1'
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$Bucket = "$ProjectId-atlas-private"

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}

function Get-GcloudValue {
    param([string[]]$Arguments)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    $value = & $Gcloud @Arguments 2>$null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($exitCode -ne 0) {
        return 'missing'
    }
    $text = ($value | Out-String).Trim()
    return $(if ($text) { $text } else { 'not configured' })
}

$account = Get-GcloudValue @(
    'auth', 'list',
    '--filter=status:ACTIVE',
    '--format=value(account)'
)
$project = Get-GcloudValue @(
    'projects', 'describe', $ProjectId,
    '--format=value(lifecycleState)'
)
$billing = Get-GcloudValue @(
    'billing', 'projects', 'describe', $ProjectId,
    '--format=value(billingEnabled)'
)
$bucket = Get-GcloudValue @(
    'storage', 'buckets', 'describe', "gs://$Bucket",
    '--format=value(name)'
)
$repository = Get-GcloudValue @(
    'artifacts', 'repositories', 'describe', 'atlas-containers',
    "--project=$ProjectId",
    "--location=$Region",
    '--format=value(name)'
)
$repositoryImageCount = Get-GcloudValue @(
    'artifacts', 'docker', 'images', 'list',
    "$Region-docker.pkg.dev/$ProjectId/atlas-containers",
    "--project=$ProjectId",
    "--format=value(version)"
)
$repositoryImageCount = if ($repositoryImageCount -in @(
    'missing', 'not configured'
)) {
    $repositoryImageCount
} else {
    @($repositoryImageCount -split '\r?\n').Count
}
$cleanupDryRun = Get-GcloudValue @(
    'artifacts', 'repositories', 'describe', 'atlas-containers',
    "--project=$ProjectId",
    "--location=$Region",
    '--format=value(cleanupPolicyDryRun)'
)
$service = Get-GcloudValue @(
    'run', 'services', 'describe', 'atlas-dashboard-stg',
    "--project=$ProjectId",
    "--region=$Region",
    '--format=value(status.url)'
)
$dailyJob = Get-GcloudValue @(
    'run', 'jobs', 'describe', 'atlas-daily-stg',
    "--project=$ProjectId",
    "--region=$Region",
    '--format=value(metadata.name)'
)
$weeklyJob = Get-GcloudValue @(
    'run', 'jobs', 'describe', 'atlas-weekly-stg',
    "--project=$ProjectId",
    "--region=$Region",
    '--format=value(metadata.name)'
)
$dailySchedule = Get-GcloudValue @(
    'scheduler', 'jobs', 'describe', 'atlas-daily-stg',
    "--project=$ProjectId",
    "--location=$Region",
    '--format=value(state)'
)
$weeklySchedule = Get-GcloudValue @(
    'scheduler', 'jobs', 'describe', 'atlas-weekly-stg',
    "--project=$ProjectId",
    "--location=$Region",
    '--format=value(state)'
)
$dailyExecution = Get-GcloudValue @(
    'run', 'jobs', 'executions', 'list',
    '--job=atlas-daily-stg',
    "--project=$ProjectId",
    "--region=$Region",
    '--limit=1',
    '--format=value(metadata.name,status.completionTime,status.succeededCount,status.failedCount)'
)
$weeklyExecution = Get-GcloudValue @(
    'run', 'jobs', 'executions', 'list',
    '--job=atlas-weekly-stg',
    "--project=$ProjectId",
    "--region=$Region",
    '--limit=1',
    '--format=value(metadata.name,status.completionTime,status.succeededCount,status.failedCount)'
)
$uptimeChecks = Get-GcloudValue @(
    'monitoring', 'uptime', 'list-configs',
    "--project=$ProjectId",
    '--format=value(displayName)'
)
$alertPolicies = Get-GcloudValue @(
    'monitoring', 'policies', 'list',
    "--project=$ProjectId",
    '--format=value(displayName)'
)

Write-Host 'Atlas Google Cloud staging status'
Write-Host "  Account: $account"
Write-Host "  Project: $project"
Write-Host "  Billing enabled: $billing"
Write-Host "  Private bucket: $bucket"
Write-Host "  Artifact repository: $repository"
Write-Host "  Artifact image count: $repositoryImageCount"
Write-Host "  Artifact cleanup dry run: $cleanupDryRun"
Write-Host "  Dashboard service: $service"
Write-Host "  Daily job: $dailyJob"
Write-Host "  Daily schedule: $dailySchedule"
Write-Host "  Latest daily execution: $dailyExecution"
Write-Host "  Weekly job: $weeklyJob"
Write-Host "  Weekly schedule: $weeklySchedule"
Write-Host "  Latest weekly execution: $weeklyExecution"
Write-Host "  Uptime checks: $uptimeChecks"
Write-Host "  Alert policies: $alertPolicies"
if ($billing -eq 'True') {
    Write-Warning 'Billing is enabled. Review CLOUD_COST_POLICY.md before continuing.'
}
