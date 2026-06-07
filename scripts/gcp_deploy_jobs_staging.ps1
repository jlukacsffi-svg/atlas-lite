param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [string]$ImageTag,

    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',

    [string]$DailySchedule = '0 7 * * *',
    [string]$WeeklySchedule = '0 8 * * 0',
    [string]$TimeZone = 'America/Los_Angeles',
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$Repository = 'atlas-containers'
$Bucket = "$ProjectId-atlas-private"
$JobServiceAccount = "atlas-jobs-stg@$ProjectId.iam.gserviceaccount.com"
$SchedulerServiceAccount = "atlas-scheduler-stg@$ProjectId.iam.gserviceaccount.com"
$DailyJob = 'atlas-daily-stg'
$WeeklyJob = 'atlas-weekly-stg'
$Image = "$Region-docker.pkg.dev/$ProjectId/$Repository/atlas:$ImageTag"

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}

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

function Test-GcloudResource {
    param([string[]]$Arguments)
    if (-not $Apply) {
        return $false
    }
    & $Gcloud @Arguments *> $null
    return $LASTEXITCODE -eq 0
}

Write-Host "Atlas staging scheduled jobs"
Write-Host "  Project: $ProjectId"
Write-Host "  Image: $Image"
Write-Host "  Daily: $DailySchedule $TimeZone"
Write-Host "  Weekly: $WeeklySchedule $TimeZone"
Write-Host "  Mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"

$commonEnvironment = (
    "ATLAS_DATA_ROOT=/tmp/atlas-data," +
    "ATLAS_GCS_BUCKET=$Bucket," +
    'ATLAS_GCS_PREFIX=owner-v1,' +
    'ATLAS_EMAIL_ENABLED=false'
)

Invoke-Gcloud @(
    'run', 'jobs', 'deploy', $DailyJob,
    "--project=$ProjectId",
    "--region=$Region",
    "--image=$Image",
    "--service-account=$JobServiceAccount",
    '--command=python',
    '--args=cloud_daily.py',
    "--set-env-vars=$commonEnvironment",
    '--tasks=1',
    '--max-retries=1',
    '--task-timeout=30m',
    '--cpu=1',
    '--memory=1Gi'
)

Invoke-Gcloud @(
    'run', 'jobs', 'deploy', $WeeklyJob,
    "--project=$ProjectId",
    "--region=$Region",
    "--image=$Image",
    "--service-account=$JobServiceAccount",
    '--command=python',
    '--args=cloud_weekly.py',
    "--set-env-vars=$commonEnvironment",
    '--tasks=1',
    '--max-retries=1',
    '--task-timeout=15m',
    '--cpu=1',
    '--memory=512Mi'
)

foreach ($job in @($DailyJob, $WeeklyJob)) {
    Invoke-Gcloud @(
        'run', 'jobs', 'add-iam-policy-binding', $job,
        "--project=$ProjectId",
        "--region=$Region",
        "--member=serviceAccount:$SchedulerServiceAccount",
        '--role=roles/run.invoker'
    )
}

$dailyUri = "https://run.googleapis.com/v2/projects/$ProjectId/locations/$Region/jobs/${DailyJob}:run"
$weeklyUri = "https://run.googleapis.com/v2/projects/$ProjectId/locations/$Region/jobs/${WeeklyJob}:run"

$dailySchedulerAction = if (Test-GcloudResource @(
    'scheduler', 'jobs', 'describe', 'atlas-daily-stg',
    "--project=$ProjectId",
    "--location=$Region"
)) { 'update' } else { 'create' }
$weeklySchedulerAction = if (Test-GcloudResource @(
    'scheduler', 'jobs', 'describe', 'atlas-weekly-stg',
    "--project=$ProjectId",
    "--location=$Region"
)) { 'update' } else { 'create' }

Invoke-Gcloud @(
    'scheduler', 'jobs', $dailySchedulerAction, 'http', 'atlas-daily-stg',
    "--project=$ProjectId",
    "--location=$Region",
    "--schedule=$DailySchedule",
    "--time-zone=$TimeZone",
    "--uri=$dailyUri",
    '--http-method=POST',
    "--oauth-service-account-email=$SchedulerServiceAccount",
    '--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform',
    '--max-retry-attempts=1',
    '--attempt-deadline=180s'
)

Invoke-Gcloud @(
    'scheduler', 'jobs', $weeklySchedulerAction, 'http', 'atlas-weekly-stg',
    "--project=$ProjectId",
    "--location=$Region",
    "--schedule=$WeeklySchedule",
    "--time-zone=$TimeZone",
    "--uri=$weeklyUri",
    '--http-method=POST',
    "--oauth-service-account-email=$SchedulerServiceAccount",
    '--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform',
    '--max-retry-attempts=1',
    '--attempt-deadline=180s'
)

Write-Host ''
if ($Apply) {
    Write-Host '[ok] Staging jobs and schedules deployed.'
} else {
    Write-Host '[plan] No jobs or schedules were changed.'
}
