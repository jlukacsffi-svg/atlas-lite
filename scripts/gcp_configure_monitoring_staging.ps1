param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[^@\s]+@[^@\s]+\.[^@\s]+$')]
    [string]$OwnerEmail,

    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',

    [switch]$Apply,
    [switch]$ConfirmCosts
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$DashboardHost = "atlas-dashboard-stg-$((& $Gcloud projects describe $ProjectId --format='value(projectNumber)')).$Region.run.app"
$UptimeDisplayName = 'Atlas dashboard readiness'
$ChannelDisplayName = 'Atlas staging alerts'
$DashboardPolicyName = 'Atlas dashboard unavailable'
$JobPolicyName = 'Atlas cloud job failed'
$UptimeTimeoutSeconds = 30
$DashboardAlertThreshold = 0.67
$DashboardAlertDuration = '600s'

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}
if ($Apply -and -not $ConfirmCosts) {
    throw 'Monitoring can create charges. Re-run with -Apply -ConfirmCosts only after owner approval.'
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

function Get-MonitoringHeaders {
    $token = & $Gcloud auth print-access-token
    if ($LASTEXITCODE -ne 0 -or -not $token) {
        throw 'Unable to obtain a Google Cloud access token.'
    }
    return @{
        Authorization = "Bearer $token"
        'Content-Type' = 'application/json'
    }
}

function Get-MonitoringCollection {
    param(
        [Parameter(Mandatory = $true)][string]$Collection,
        [Parameter(Mandatory = $true)][hashtable]$Headers
    )
    $uri = "https://monitoring.googleapis.com/v3/projects/$ProjectId/$Collection"
    return Invoke-RestMethod -Method Get -Uri $uri -Headers $Headers
}

function New-MonitoringResource {
    param(
        [Parameter(Mandatory = $true)][string]$Collection,
        [Parameter(Mandatory = $true)][hashtable]$Payload,
        [Parameter(Mandatory = $true)][hashtable]$Headers
    )
    $uri = "https://monitoring.googleapis.com/v3/projects/$ProjectId/$Collection"
    $body = $Payload | ConvertTo-Json -Depth 12
    return Invoke-RestMethod -Method Post -Uri $uri -Headers $Headers -Body $body
}

function New-AlertPolicy {
    param(
        [Parameter(Mandatory = $true)][string]$DisplayName,
        [Parameter(Mandatory = $true)][string]$ConditionName,
        [Parameter(Mandatory = $true)][string]$Filter,
        [Parameter(Mandatory = $true)][string]$Comparison,
        [Parameter(Mandatory = $true)][double]$Threshold,
        [Parameter(Mandatory = $true)][string]$Duration,
        [Parameter(Mandatory = $true)][string]$Aligner,
        [Parameter(Mandatory = $true)][string]$Documentation,
        [Parameter(Mandatory = $true)][string]$ServiceLabel,
        [Parameter(Mandatory = $true)][string]$ChannelName,
        [Parameter(Mandatory = $true)][hashtable]$Headers
    )
    return New-MonitoringResource -Collection 'alertPolicies' -Headers $Headers -Payload @{
        displayName = $DisplayName
        combiner = 'OR'
        enabled = $true
        notificationChannels = @($ChannelName)
        documentation = @{
            content = $Documentation
            mimeType = 'text/markdown'
        }
        userLabels = @{
            environment = 'staging'
            service = $ServiceLabel
        }
        conditions = @(
            @{
                displayName = $ConditionName
                conditionThreshold = @{
                    filter = $Filter
                    comparison = $Comparison
                    thresholdValue = $Threshold
                    duration = $Duration
                    trigger = @{ count = 1 }
                    aggregations = @(
                        @{
                            alignmentPeriod = '300s'
                            perSeriesAligner = $Aligner
                        }
                    )
                }
            }
        )
    }
}

function Update-AlertPolicy {
    param(
        [Parameter(Mandatory = $true)][object]$Policy,
        [Parameter(Mandatory = $true)][hashtable]$Headers
    )
    $uri = (
        "https://monitoring.googleapis.com/v3/$($Policy.name)" +
        "?updateMask=conditions,documentation,enabled,notificationChannels,userLabels,combiner"
    )
    $body = $Policy | ConvertTo-Json -Depth 20
    return Invoke-RestMethod -Method Patch -Uri $uri -Headers $Headers -Body $body
}

Write-Host 'Atlas staging monitoring'
Write-Host "  Project: $ProjectId"
Write-Host "  Dashboard: https://$DashboardHost/readyz"
Write-Host "  Alerts: $OwnerEmail"
Write-Host '  Uptime: every 10 minutes from three US regions'
Write-Host '  Estimated monitoring cost: $0-$0.10 per month at current scale'
Write-Host "  Mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"

if (-not $Apply) {
    Invoke-Gcloud @(
        'monitoring', 'uptime', 'create', $UptimeDisplayName,
        "--project=$ProjectId",
        '--resource-type=uptime-url',
        "--resource-labels=host=$DashboardHost,project_id=$ProjectId",
        '--protocol=https',
        '--path=/readyz',
        '--request-method=get',
        '--validate-ssl=true',
        '--status-codes=200',
        '--matcher-content=ready',
        '--matcher-type=contains-string',
        '--period=10',
        "--timeout=$UptimeTimeoutSeconds",
        '--regions=usa-oregon,usa-iowa,usa-virginia',
        '--user-labels=environment=staging,service=atlas-dashboard'
    )
    Write-Host '[plan] Create or reuse the owner email notification channel.'
    Write-Host '[plan] Create or reuse dashboard-unavailable and job-failure policies.'
    Write-Host '[plan] No monitoring resources were changed.'
    exit 0
}

$headers = Get-MonitoringHeaders
$channels = Get-MonitoringCollection -Collection 'notificationChannels' -Headers $headers
$channel = @($channels.notificationChannels) | Where-Object {
    $_.displayName -eq $ChannelDisplayName -and
    $_.type -eq 'email' -and
    $_.labels.email_address -eq $OwnerEmail
} | Select-Object -First 1
if (-not $channel) {
    $channel = New-MonitoringResource -Collection 'notificationChannels' -Headers $headers -Payload @{
        type = 'email'
        displayName = $ChannelDisplayName
        labels = @{ email_address = $OwnerEmail }
        enabled = $true
    }
    Write-Host '[ok] Created owner email notification channel.'
} else {
    Write-Host '[ok] Owner email notification channel already exists.'
}

$uptimeConfigs = & $Gcloud monitoring uptime list-configs "--project=$ProjectId" --format=json |
    ConvertFrom-Json
$uptime = @($uptimeConfigs) | Where-Object {
    $_.displayName -eq $UptimeDisplayName
} | Select-Object -First 1
if (-not $uptime) {
    Invoke-Gcloud @(
        'monitoring', 'uptime', 'create', $UptimeDisplayName,
        "--project=$ProjectId",
        '--resource-type=uptime-url',
        "--resource-labels=host=$DashboardHost,project_id=$ProjectId",
        '--protocol=https',
        '--path=/readyz',
        '--request-method=get',
        '--validate-ssl=true',
        '--status-codes=200',
        '--matcher-content=ready',
        '--matcher-type=contains-string',
        '--period=10',
        "--timeout=$UptimeTimeoutSeconds",
        '--regions=usa-oregon,usa-iowa,usa-virginia',
        '--user-labels=environment=staging,service=atlas-dashboard'
    )
    $uptimeConfigs = & $Gcloud monitoring uptime list-configs "--project=$ProjectId" --format=json |
        ConvertFrom-Json
    $uptime = @($uptimeConfigs) | Where-Object {
        $_.displayName -eq $UptimeDisplayName
    } | Select-Object -First 1
} else {
    $checkId = ($uptime.name -split '/')[-1]
    Invoke-Gcloud @(
        'monitoring', 'uptime', 'update', $checkId,
        "--project=$ProjectId",
        "--timeout=$UptimeTimeoutSeconds"
    )
    Write-Host "[ok] Dashboard readiness uptime check uses a ${UptimeTimeoutSeconds}-second timeout."
}
if (-not $uptime) {
    throw 'Dashboard readiness uptime check could not be resolved.'
}

$policies = Get-MonitoringCollection -Collection 'alertPolicies' -Headers $headers
$policyList = @($policies.alertPolicies)
$checkId = ($uptime.name -split '/')[-1]

$dashboardFilter = (
    'metric.type="monitoring.googleapis.com/uptime_check/check_passed" ' +
    'AND resource.type="uptime_url" ' +
    "AND metric.label.`"check_id`"=`"$checkId`""
)
$dashboardDocumentation = (
    'The Atlas staging readiness endpoint is failing from multiple checkers ' +
    'for a sustained period. Verify Cloud Run revision health before enabling schedules.'
)
$dashboardPolicy = $policyList | Where-Object displayName -eq $DashboardPolicyName | Select-Object -First 1
if (-not $dashboardPolicy) {
    New-AlertPolicy `
        -DisplayName $DashboardPolicyName `
        -ConditionName 'Dashboard readiness check is failing' `
        -Filter $dashboardFilter `
        -Comparison 'COMPARISON_LT' `
        -Threshold $DashboardAlertThreshold `
        -Duration $DashboardAlertDuration `
        -Aligner 'ALIGN_FRACTION_TRUE' `
        -Documentation $dashboardDocumentation `
        -ServiceLabel 'atlas-dashboard' `
        -ChannelName $channel.name `
        -Headers $headers > $null
    Write-Host '[ok] Created dashboard availability alert.'
} else {
    $dashboardPolicy.conditions[0].conditionThreshold.filter = $dashboardFilter
    $dashboardPolicy.conditions[0].conditionThreshold.comparison = 'COMPARISON_LT'
    $dashboardPolicy.conditions[0].conditionThreshold.thresholdValue = $DashboardAlertThreshold
    $dashboardPolicy.conditions[0].conditionThreshold.duration = $DashboardAlertDuration
    $dashboardPolicy.conditions[0].conditionThreshold.trigger = @{ count = 1 }
    $dashboardPolicy.conditions[0].conditionThreshold.aggregations = @(
        @{
            alignmentPeriod = '300s'
            perSeriesAligner = 'ALIGN_FRACTION_TRUE'
        }
    )
    $dashboardPolicy.documentation = @{
        content = $dashboardDocumentation
        mimeType = 'text/markdown'
    }
    Update-AlertPolicy -Policy $dashboardPolicy -Headers $headers > $null
    Write-Host (
        "[ok] Dashboard availability alert requires sustained multi-region " +
        "failure below $DashboardAlertThreshold for $DashboardAlertDuration."
    )
}

if (-not ($policyList | Where-Object displayName -eq $JobPolicyName)) {
    $filter = (
        'metric.type="run.googleapis.com/job/completed_execution_count" ' +
        'AND resource.type="cloud_run_job" ' +
        'AND metric.label."result"="failed" ' +
        'AND (resource.label."job_name"="atlas-daily-stg" ' +
        'OR resource.label."job_name"="atlas-weekly-stg")'
    )
    New-AlertPolicy `
        -DisplayName $JobPolicyName `
        -ConditionName 'Daily or weekly execution reported failure' `
        -Filter $filter `
        -Comparison 'COMPARISON_GT' `
        -Threshold 0 `
        -Duration '0s' `
        -Aligner 'ALIGN_DELTA' `
        -Documentation 'An Atlas daily or weekly Cloud Run execution failed. Keep scheduler triggers paused until the execution logs and private-state integrity are reviewed.' `
        -ServiceLabel 'atlas-jobs' `
        -ChannelName $channel.name `
        -Headers $headers > $null
    Write-Host '[ok] Created Cloud Run job failure alert.'
} else {
    Write-Host '[ok] Cloud Run job failure alert already exists.'
}

Write-Host '[ok] Staging monitoring is configured.'
