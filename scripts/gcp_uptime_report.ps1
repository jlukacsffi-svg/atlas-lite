param(
    [string]$ProjectId = 'atlas-capital-research-stg',
    [ValidateRange(1, 168)]
    [int]$Hours = 24
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}

$token = (& $Gcloud auth print-access-token).Trim()
if ($LASTEXITCODE -ne 0 -or -not $token) {
    throw 'Unable to obtain a Google Cloud access token.'
}

$end = (Get-Date).ToUniversalTime()
$start = $end.AddHours(-$Hours)
$filter = [Uri]::EscapeDataString(
    'metric.type="monitoring.googleapis.com/uptime_check/check_passed"'
)
$baseUri = (
    "https://monitoring.googleapis.com/v3/projects/$ProjectId/timeSeries" +
    "?filter=$filter" +
    "&interval.startTime=$([Uri]::EscapeDataString($start.ToString('o')))" +
    "&interval.endTime=$([Uri]::EscapeDataString($end.ToString('o')))" +
    '&view=FULL&pageSize=1000'
)
$headers = @{ Authorization = "Bearer $token" }
$pageToken = $null
$series = @()

do {
    $uri = $baseUri
    if ($pageToken) {
        $uri += "&pageToken=$([Uri]::EscapeDataString($pageToken))"
    }
    $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    $series += @($response.timeSeries)
    $pageToken = $response.nextPageToken
} while ($pageToken)

$rows = @($series | ForEach-Object {
    $points = @($_.points)
    $passed = @($points | Where-Object { [bool]$_.value.boolValue }).Count
    [pscustomobject]@{
        Region = [string]$_.metric.labels.checker_location
        Points = $points.Count
        Passed = $passed
        Failed = $points.Count - $passed
        Earliest = ($points.interval.endTime | Sort-Object | Select-Object -First 1)
        Latest = (
            $points.interval.endTime |
                Sort-Object -Descending |
                Select-Object -First 1
        )
    }
})

$totalPoints = ($rows | Measure-Object Points -Sum).Sum
$totalPassed = ($rows | Measure-Object Passed -Sum).Sum
$totalFailed = ($rows | Measure-Object Failed -Sum).Sum
$availability = if ($totalPoints) {
    [math]::Round(100 * $totalPassed / $totalPoints, 4)
} else {
    0
}

Write-Host 'Atlas dashboard uptime report'
Write-Host "  Project: $ProjectId"
Write-Host "  Requested window: $Hours hours"
Write-Host '  Mode: READ ONLY'
Write-Host ''
$rows | Format-Table -AutoSize
Write-Host "  Total samples: $totalPoints"
Write-Host "  Passed: $totalPassed"
Write-Host "  Failed: $totalFailed"
Write-Host "  Availability: $availability%"

if (-not $totalPoints) {
    Write-Host '[result] NO DATA'
    exit 1
}
if ($totalFailed -gt 0) {
    Write-Host '[result] REVIEW REQUIRED'
    exit 2
}
Write-Host '[result] PASS'
