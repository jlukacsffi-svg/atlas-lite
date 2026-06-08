param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',

    [ValidateSet('Status', 'Pause', 'Resume')]
    [string]$Action = 'Status',

    [switch]$Apply,
    [switch]$ConfirmCosts,
    [switch]$ApproveRecurringExecution
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$Schedules = @('atlas-daily-stg', 'atlas-weekly-stg')

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}
if ($Action -eq 'Resume') {
    if (-not $Apply -or -not $ConfirmCosts -or -not $ApproveRecurringExecution) {
        throw 'Resuming schedules requires -Apply -ConfirmCosts -ApproveRecurringExecution.'
    }
}
if ($Action -eq 'Pause' -and -not $Apply) {
    throw 'Pausing schedules requires -Apply.'
}

function Get-GcloudValue {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $value = & $Gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to read required staging state.'
    }
    return ($value | Out-String).Trim()
}

function Show-Status {
    foreach ($schedule in $Schedules) {
        $state = Get-GcloudValue @(
            'scheduler', 'jobs', 'describe', $schedule,
            "--project=$ProjectId",
            "--location=$Region",
            '--format=value(state)'
        )
        Write-Host "  $schedule`: $state"
    }
}

Write-Host 'Atlas recurring schedule control'
Write-Host "  Project: $ProjectId"
Write-Host "  Requested action: $Action"

if ($Action -eq 'Status') {
    Show-Status
    exit 0
}

if ($Action -eq 'Resume') {
    foreach ($job in @('atlas-daily-stg', 'atlas-weekly-stg')) {
        $successCount = Get-GcloudValue @(
            'run', 'jobs', 'executions', 'list',
            "--job=$job",
            "--project=$ProjectId",
            "--region=$Region",
            '--limit=1',
            '--format=value(status.succeededCount)'
        )
        if ($successCount -ne '1') {
            throw "Latest execution for $job is not a confirmed success."
        }
    }
    $uptime = Get-GcloudValue @(
        'monitoring', 'uptime', 'list-configs',
        "--project=$ProjectId",
        '--filter=displayName=Atlas dashboard readiness',
        '--format=value(displayName)'
    )
    $policies = Get-GcloudValue @(
        'monitoring', 'policies', 'list',
        "--project=$ProjectId",
        '--filter=enabled=true',
        '--format=value(displayName)'
    )
    if (-not $uptime -or $policies -notmatch 'Atlas dashboard unavailable' -or
        $policies -notmatch 'Atlas cloud job failed') {
        throw 'Required staging monitoring is not configured.'
    }
}

$verb = $Action.ToLowerInvariant()
foreach ($schedule in $Schedules) {
    Write-Host "[apply] $verb $schedule"
    & $Gcloud scheduler jobs $verb $schedule `
        "--project=$ProjectId" `
        "--location=$Region"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to $verb $schedule."
    }
}

Show-Status
if ($Action -eq 'Resume') {
    Write-Host '[ok] Recurring execution is active under the approved cost envelope.'
} else {
    Write-Host '[ok] Recurring execution is paused.'
}
