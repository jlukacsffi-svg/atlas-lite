param(
    [ValidateSet('Status', 'RecordCrossDevice', 'RecordNonOwnerDenial', 'RecordOwnerDashboardReview', 'RecordScheduleDecision')]
    [string]$Action = 'Status',

    [string]$ObservedAt = '',
    [string]$Notes = '',
    [switch]$ConfirmedExpectedResult,

    [string]$EvidencePath = (
        Join-Path (Split-Path -Parent $PSScriptRoot) `
            'cloud\staging_manual_validation.json'
    )
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $EvidencePath)) {
    throw "Manual validation evidence file not found: $EvidencePath"
}

$evidence = Get-Content -LiteralPath $EvidencePath -Raw |
    ConvertFrom-Json
if ($evidence.schema_version -ne 1) {
    throw 'Unsupported manual validation evidence schema.'
}

function Write-ValidationStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)]$Entry
    )
    $status = [string]$Entry.status
    Write-Host "  [$status] $Label"
    if ($status -eq 'validated' -and $Entry.observed_at) {
        Write-Host "    Observed: $($Entry.observed_at)"
    }
    if ($Entry.notes) {
        Write-Host "    Notes: $($Entry.notes)"
    }
    if ($Entry.expected_checks) {
        Write-Host '    Expected checks:'
        foreach ($check in $Entry.expected_checks) {
            Write-Host "      - $check"
        }
    }
}

if ($Action -eq 'Status') {
    Write-Host 'Atlas manual staging validation evidence'
    Write-Host "  Project: $($evidence.project_id)"
    Write-Host '  Mode: READ ONLY'
    Write-ValidationStatus 'Cross-device owner login' `
        $evidence.cross_device_owner_login
    Write-ValidationStatus 'Non-owner Google account denial' `
        $evidence.non_owner_denial
    Write-ValidationStatus 'Owner Stage 5 dashboard walkthrough' `
        $evidence.owner_dashboard_stage5_review
    Write-ValidationStatus 'Recurring schedule decision' `
        $evidence.schedule_decision
    exit 0
}

if (-not $ConfirmedExpectedResult) {
    throw 'Recording a result requires -ConfirmedExpectedResult.'
}
if (-not $ObservedAt) {
    throw 'Recording a result requires -ObservedAt with an ISO 8601 timestamp.'
}

$parsedObservedAt = [DateTimeOffset]::MinValue
if (-not [DateTimeOffset]::TryParse(
    $ObservedAt,
    [ref]$parsedObservedAt
)) {
    throw 'ObservedAt must be a valid ISO 8601 timestamp.'
}
$normalizedObservedAt = $parsedObservedAt.ToString('o')

if ($Action -eq 'RecordCrossDevice') {
    $entry = $evidence.cross_device_owner_login
    $entry.status = 'validated'
    $entry.observed_at = $normalizedObservedAt
    $entry.notes = if ($Notes) {
        $Notes
    } else {
        'Owner reached the authenticated dashboard from a second device.'
    }
}
if ($Action -eq 'RecordNonOwnerDenial') {
    $entry = $evidence.non_owner_denial
    $entry.status = 'validated'
    $entry.observed_at = $normalizedObservedAt
    $entry.notes = if ($Notes) {
        $Notes
    } else {
        'A Google account outside the Atlas allowlist was denied access.'
    }
}
if ($Action -eq 'RecordOwnerDashboardReview') {
    $entry = $evidence.owner_dashboard_stage5_review
    $entry.status = 'validated'
    $entry.observed_at = $normalizedObservedAt
    $entry.notes = if ($Notes) {
        $Notes
    } else {
        'Owner confirmed the signed-in dashboard shows the Stage 5 scoreboard, persistence learning, benchmark-relative performance, and autonomous paper flow without approval queues.'
    }
}
if ($Action -eq 'RecordScheduleDecision') {
    $entry = $evidence.schedule_decision
    $entry.status = 'validated'
    $entry.decision = 'enabled'
    $entry.observed_at = $normalizedObservedAt
    $entry.notes = if ($Notes) {
        $Notes
    } else {
        'Recurring daily and weekly staging schedules are enabled under the approved cost controls.'
    }
}

$evidence | ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath $EvidencePath -Encoding UTF8
Write-Host "Recorded $Action in $EvidencePath"
