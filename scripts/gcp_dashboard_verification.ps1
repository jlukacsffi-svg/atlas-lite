param(
    [Parameter(Mandatory = $true)]
    [string]$ServiceUrl,

    [Parameter(Mandatory = $true)]
    [string]$VerificationToken
)

$ErrorActionPreference = 'Stop'

Write-Host 'Atlas dashboard verification'
Write-Host "  Service: $ServiceUrl"
Write-Host '  Mode: READ ONLY'

$headers = @{
    'X-Atlas-Verification' = $VerificationToken
}

$response = Invoke-RestMethod `
    -Uri ($ServiceUrl.TrimEnd('/') + '/api/dashboard/verification') `
    -Headers $headers `
    -Method Get

Write-Host "  Revision: $($response.workspace.deployment.revision)"
Write-Host ''
Write-Host 'Verification checks:'

$failed = 0
foreach ($entry in $response.checks.PSObject.Properties) {
    $name = $entry.Name
    $value = $entry.Value
    $ok = [bool]$value.ok
    $status = if ($ok) { 'pass' } else { 'fail' }
    Write-Host "  [$status] $name - $($value.detail)"
    if (-not $ok) {
        $failed += 1
    }
}

if ($failed -gt 0) {
    Write-Host ''
    Write-Host "[result] VERIFICATION FAILED - $failed check(s) need attention."
    exit 1
}

Write-Host ''
Write-Host '[result] VERIFICATION PASS - Stage 5 dashboard contract is present.'
