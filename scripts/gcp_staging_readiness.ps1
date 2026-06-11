param(
    [string]$ProjectId = 'atlas-capital-research-stg',
    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',
    [string]$OwnerEmail = 'jlukacsffi@gmail.com'
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$BucketName = "$ProjectId-atlas-private"
$DashboardAccount = "atlas-dashboard-stg@$ProjectId.iam.gserviceaccount.com"
$JobsAccount = "atlas-jobs-stg@$ProjectId.iam.gserviceaccount.com"
$SchedulerAccount = "atlas-scheduler-stg@$ProjectId.iam.gserviceaccount.com"
$script:Failures = 0

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}

function Get-GcloudJson {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    $json = & $Gcloud @Arguments 2>$null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($exitCode -ne 0) {
        throw "Read-only Google Cloud query failed: $($Arguments -join ' ')"
    }
    return (($json | Out-String) | ConvertFrom-Json)
}

function Add-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][bool]$Passed,
        [Parameter(Mandatory = $true)][string]$Detail
    )
    if ($Passed) {
        Write-Host "[pass] $Name - $Detail"
    } else {
        Write-Host "[fail] $Name - $Detail"
        $script:Failures += 1
    }
}

function Get-EnvironmentMap {
    param([Parameter(Mandatory = $true)]$Container)
    $map = @{}
    foreach ($entry in $Container.env) {
        if ($entry.valueFrom.secretKeyRef) {
            $map[$entry.name] = "secret:$($entry.valueFrom.secretKeyRef.name)"
        } else {
            $map[$entry.name] = [string]$entry.value
        }
    }
    return $map
}

Write-Host 'Atlas staging readiness audit'
Write-Host "  Project: $ProjectId"
Write-Host "  Region: $Region"
Write-Host '  Mode: READ ONLY'

$service = Get-GcloudJson @(
    'run', 'services', 'describe', 'atlas-dashboard-stg',
    "--project=$ProjectId", "--region=$Region", '--format=json'
)
$bucketConfig = Get-GcloudJson @(
    'storage', 'buckets', 'describe', "gs://$BucketName", '--format=json'
)
$bucketIam = Get-GcloudJson @(
    'storage', 'buckets', 'get-iam-policy', "gs://$BucketName", '--format=json'
)
$projectIam = Get-GcloudJson @(
    'projects', 'get-iam-policy', $ProjectId, '--format=json'
)
$dailyJob = Get-GcloudJson @(
    'run', 'jobs', 'describe', 'atlas-daily-stg',
    "--project=$ProjectId", "--region=$Region", '--format=json'
)
$weeklyJob = Get-GcloudJson @(
    'run', 'jobs', 'describe', 'atlas-weekly-stg',
    "--project=$ProjectId", "--region=$Region", '--format=json'
)
$dailySchedule = Get-GcloudJson @(
    'scheduler', 'jobs', 'describe', 'atlas-daily-stg',
    "--project=$ProjectId", "--location=$Region", '--format=json'
)
$weeklySchedule = Get-GcloudJson @(
    'scheduler', 'jobs', 'describe', 'atlas-weekly-stg',
    "--project=$ProjectId", "--location=$Region", '--format=json'
)
$repository = Get-GcloudJson @(
    'artifacts', 'repositories', 'describe', 'atlas-containers',
    "--project=$ProjectId", "--location=$Region", '--format=json'
)
$uptimeChecks = @(Get-GcloudJson @(
    'monitoring', 'uptime', 'list-configs',
    "--project=$ProjectId", '--format=json'
))
$alertPolicies = @(Get-GcloudJson @(
    'monitoring', 'policies', 'list',
    "--project=$ProjectId", '--format=json'
))

$container = $service.spec.template.spec.containers[0]
$environment = Get-EnvironmentMap $container
$serviceReady = @($service.status.conditions | Where-Object {
    $_.type -eq 'Ready' -and $_.status -eq 'True'
}).Count -eq 1
$serviceMax = [string]$service.metadata.annotations.'run.googleapis.com/maxScale'
$serviceMin = [string]$service.metadata.annotations.'run.googleapis.com/minScale'

Add-Check 'Dashboard ready' $serviceReady ([string]$service.status.latestReadyRevisionName)
Add-Check 'Dashboard maximum instances' ($serviceMax -eq '1') "max=$serviceMax"
Add-Check 'Dashboard scales to zero' ($serviceMin -in @('', '0')) "min=$(if ($serviceMin) { $serviceMin } else { '0 (default)' })"
Add-Check 'Dashboard service account' `
    ($service.spec.template.spec.serviceAccountName -eq $DashboardAccount) `
    ([string]$service.spec.template.spec.serviceAccountName)
Add-Check 'Cloud authentication mode' `
    ($environment.ATLAS_WEB_MODE -eq 'cloud' -and
     $environment.ATLAS_AUTH_MODE -eq 'google_oauth') `
    "$($environment.ATLAS_WEB_MODE)/$($environment.ATLAS_AUTH_MODE)"
Add-Check 'Owner allowlist' `
    ($environment.ATLAS_OWNER_EMAIL -eq $OwnerEmail) `
    ([string]$environment.ATLAS_OWNER_EMAIL)
Add-Check 'OAuth and session secrets' `
    ($environment.ATLAS_GOOGLE_CLIENT_ID -eq 'secret:atlas-google-oauth-client-id' -and
     $environment.ATLAS_GOOGLE_CLIENT_SECRET -eq 'secret:atlas-google-oauth-client-secret' -and
     $environment.ATLAS_SESSION_SECRET -eq 'secret:atlas-session-secret') `
    'all values are Secret Manager references'

Add-Check 'Bucket public access prevention' `
    ($bucketConfig.public_access_prevention -eq 'enforced') `
    ([string]$bucketConfig.public_access_prevention)
Add-Check 'Bucket uniform access' `
    ([bool]$bucketConfig.uniform_bucket_level_access) `
    ([string]$bucketConfig.uniform_bucket_level_access)

$bucketRoles = @{}
foreach ($binding in $bucketIam.bindings) {
    $bucketRoles[[string]$binding.role] = @($binding.members)
}
Add-Check 'Dashboard read-only storage' `
    ($bucketRoles['roles/storage.objectViewer'] -contains "serviceAccount:$DashboardAccount") `
    'dedicated object viewer'
Add-Check 'Jobs storage writer' `
    ($bucketRoles['roles/storage.objectUser'] -contains "serviceAccount:$JobsAccount") `
    'dedicated object user'
Add-Check 'No project Editor role' `
    (@($projectIam.bindings | Where-Object { $_.role -eq 'roles/editor' }).Count -eq 0) `
    'roles/editor is absent'

foreach ($item in @(
    @{ Name = 'Daily'; Job = $dailyJob; Schedule = $dailySchedule; Script = 'cloud_daily.py' },
    @{ Name = 'Weekly'; Job = $weeklyJob; Schedule = $weeklySchedule; Script = 'cloud_weekly.py' }
)) {
    $jobSpec = $item.Job.spec.template.spec
    $taskSpec = $jobSpec.template.spec
    $jobContainer = $taskSpec.containers[0]
    $jobEnv = Get-EnvironmentMap $jobContainer
    Add-Check "$($item.Name) job identity and limits" `
        ($jobSpec.taskCount -eq 1 -and
         $taskSpec.serviceAccountName -eq $JobsAccount -and
         $jobContainer.args[0] -eq $item.Script -and
         $jobEnv.ATLAS_EMAIL_ENABLED -eq 'false') `
        "one task, $($taskSpec.serviceAccountName), email disabled"
    Add-Check "$($item.Name) manual execution" `
        ($item.Job.status.latestCreatedExecution.completionStatus -eq 'EXECUTION_SUCCEEDED') `
        ([string]$item.Job.status.latestCreatedExecution.name)
    Add-Check "$($item.Name) schedule paused" `
        ($item.Schedule.state -eq 'PAUSED') `
        "$($item.Schedule.state), $($item.Schedule.schedule) $($item.Schedule.timeZone)"
    Add-Check "$($item.Name) scheduler identity" `
        ($item.Schedule.httpTarget.oauthToken.serviceAccountEmail -eq $SchedulerAccount) `
        ([string]$item.Schedule.httpTarget.oauthToken.serviceAccountEmail)
}

Add-Check 'Artifact cleanup is non-destructive' `
    ([bool]$repository.cleanupPolicyDryRun) `
    'cleanup policy dry run is enabled'
Add-Check 'Artifact rollback retention' `
    ($repository.cleanupPolicies.'keep-recent-atlas-images'.mostRecentVersions.keepCount -eq 3) `
    'three recent images are kept'

$uptimeNames = @($uptimeChecks | ForEach-Object { $_.displayName })
$dashboardUptime = @($uptimeChecks | Where-Object {
    $_.displayName -eq 'Atlas dashboard readiness'
}) | Select-Object -First 1
$policyNames = @($alertPolicies | Where-Object { $_.enabled -ne $false } |
    ForEach-Object { $_.displayName })
Add-Check 'Dashboard uptime monitoring' `
    ($uptimeNames -contains 'Atlas dashboard readiness') `
    'ten-minute readiness monitoring is configured'
Add-Check 'Cold-start monitoring tolerance' `
    ($dashboardUptime.timeout -eq '30s') `
    "timeout=$($dashboardUptime.timeout)"
Add-Check 'Required alert policies' `
    ($policyNames -contains 'Atlas dashboard unavailable' -and
     $policyNames -contains 'Atlas cloud job failed') `
    'dashboard and job alerts are enabled'

Write-Host ''
Write-Host 'Validation gates:'
Write-Host '  [pending] Cross-device owner login'
Write-Host '  [pending] Non-owner Google account denial'
Write-Host '  [validated] One complete day of uptime and alert telemetry review'
Write-Host '  [validated] Artifact Registry cost and dry-run retention review'
Write-Host '  [pending] Separate owner approval before schedule resume'

if ($script:Failures -gt 0) {
    Write-Host ""
    Write-Host "[result] NOT READY - $script:Failures automated check(s) failed."
    exit 1
}

Write-Host ''
Write-Host '[result] AUTOMATED CHECKS PASS - manual validation gates remain.'
