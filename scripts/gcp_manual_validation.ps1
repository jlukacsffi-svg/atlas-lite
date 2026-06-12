param(
    [ValidateSet('Status', 'RecordCrossDevice', 'RecordNonOwnerDenial')]
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
}

if ($Action -eq 'Status') {
    Write-Host 'Atlas manual staging validation evidence'
    Write-Host "  Project: $($evidence.project_id)"
    Write-Host '  Mode: READ ONLY'
    Write-ValidationStatus 'Cross-device owner login' `
        $evidence.cross_device_owner_login
    Write-ValidationStatus 'Non-owner Google account denial' `
        $evidence.non_owner_denial
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

$evidence | ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath $EvidencePath -Encoding UTF8
Write-Host "Recorded $Action in $EvidencePath"
