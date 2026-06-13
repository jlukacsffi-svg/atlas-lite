param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9A-Fa-f]{6}-[0-9A-Fa-f]{6}-[0-9A-Fa-f]{6}$')]
    [string]$BillingAccount,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[^@\s]+@[^@\s]+\.[^@\s]+$')]
    [string]$OwnerEmail,

    [ValidateSet('us-west1', 'us-central1', 'us-east1')]
    [string]$Region = 'us-west1',

    [ValidateRange(5, 100)]
    [int]$MonthlyBudgetUsd = 10,

    [switch]$Apply,
    [switch]$ConfirmCosts,
    [switch]$BillingAndBudgetOnly
)

$ErrorActionPreference = 'Stop'
$Gcloud = Join-Path $env:LOCALAPPDATA 'Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
$Bucket = "$ProjectId-atlas-private"
$Repository = 'atlas-containers'
$DashboardServiceAccount = "atlas-dashboard-stg@$ProjectId.iam.gserviceaccount.com"
$JobServiceAccount = "atlas-jobs-stg@$ProjectId.iam.gserviceaccount.com"
$SchedulerServiceAccount = "atlas-scheduler-stg@$ProjectId.iam.gserviceaccount.com"

if (-not (Test-Path $Gcloud)) {
    throw 'Google Cloud CLI is not installed.'
}
if ($Apply -and -not $ConfirmCosts) {
    throw 'Applying creates billing-linked resources. Re-run with -Apply -ConfirmCosts.'
}

function Invoke-Gcloud {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$AllowFailure
    )

    $display = 'gcloud ' + ($Arguments -join ' ')
    if (-not $Apply) {
        Write-Host "[plan] $display"
        return $null
    }

    Write-Host "[apply] $display"
    & $Gcloud @Arguments
    if ($LASTEXITCODE -ne 0 -and -not $AllowFailure) {
        throw "Command failed: $display"
    }
}

function Test-GcloudResource {
    param([string[]]$Arguments)
    if (-not $Apply) {
        return $false
    }
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        & $Gcloud @Arguments *> $null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

$activeAccount = & $Gcloud auth list --filter=status:ACTIVE --format='value(account)'
if (-not $activeAccount) {
    throw 'No active Google Cloud login. Run gcloud auth login first.'
}

Write-Host "Atlas staging bootstrap"
Write-Host "  Account: $activeAccount"
Write-Host "  Project: $ProjectId"
Write-Host "  Region: $Region"
Write-Host "  Bucket: gs://$Bucket"
Write-Host "  Budget: $MonthlyBudgetUsd USD/month"
Write-Host "  Owner: $OwnerEmail"
Write-Host "  Scope: $(if ($BillingAndBudgetOnly) { 'BILLING AND BUDGET ONLY' } else { 'FULL FOUNDATION' })"
Write-Host "  Mode: $(if ($Apply) { 'APPLY' } else { 'PLAN ONLY' })"

if (-not (Test-GcloudResource @('projects', 'describe', $ProjectId))) {
    Invoke-Gcloud @('projects', 'create', $ProjectId, '--name=Atlas Staging')
}

Invoke-Gcloud @(
    'billing', 'projects', 'link', $ProjectId,
    "--billing-account=$BillingAccount"
)
Invoke-Gcloud @('config', 'set', 'project', $ProjectId)

$ProjectNumber = if ($Apply) {
    & $Gcloud projects describe $ProjectId '--format=value(projectNumber)'
} else {
    '<PROJECT_NUMBER>'
}
if ($Apply -and -not $ProjectNumber) {
    throw "Unable to resolve project number for: $ProjectId"
}

Invoke-Gcloud -AllowFailure -Arguments @(
    'projects', 'remove-iam-policy-binding', $ProjectId,
    "--member=serviceAccount:$ProjectNumber-compute@developer.gserviceaccount.com",
    '--role=roles/editor'
)
Invoke-Gcloud @(
    'projects', 'add-iam-policy-binding', $ProjectId,
    "--member=serviceAccount:$ProjectNumber-compute@developer.gserviceaccount.com",
    '--role=roles/cloudbuild.builds.builder'
)

Invoke-Gcloud @(
    'services', 'enable',
    'billingbudgets.googleapis.com',
    "--project=$ProjectId"
)

$budgetExists = $false
if ($Apply) {
    $budgetJson = & $Gcloud billing budgets list `
        "--billing-account=$BillingAccount" `
        '--format=json'
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to list existing billing budgets.'
    }
    $budgets = @($budgetJson | ConvertFrom-Json)
    $budgetExists = [bool](
        $budgets | Where-Object {
            $_.displayName -eq 'atlas-staging-monthly'
        }
    )
}
if (-not $budgetExists) {
    Invoke-Gcloud @(
        'billing', 'budgets', 'create',
        "--billing-account=$BillingAccount",
        '--display-name=atlas-staging-monthly',
        "--budget-amount=${MonthlyBudgetUsd}USD",
        '--calendar-period=month',
        "--filter-projects=projects/$ProjectId",
        '--credit-types-treatment=exclude-all-credits',
        '--threshold-rule=percent=0.25',
        '--threshold-rule=percent=0.50',
        '--threshold-rule=percent=0.80',
        '--threshold-rule=percent=1.00',
        '--threshold-rule=percent=1.00,basis=forecasted-spend'
    )
}

if ($BillingAndBudgetOnly) {
    Write-Host ''
    if ($Apply) {
        Write-Host '[ok] Billing linked and staging budget configured.'
        Write-Host 'No Atlas storage, compute, build, scheduler, or image resources were created.'
    } else {
        Write-Host '[plan] Billing and budget only. No cloud settings were changed.'
    }
    exit 0
}

$services = @(
    'artifactregistry.googleapis.com',
    'cloudbuild.googleapis.com',
    'cloudresourcemanager.googleapis.com',
    'cloudscheduler.googleapis.com',
    'iap.googleapis.com',
    'iam.googleapis.com',
    'logging.googleapis.com',
    'monitoring.googleapis.com',
    'run.googleapis.com',
    'secretmanager.googleapis.com',
    'storage.googleapis.com'
)
Invoke-Gcloud (@('services', 'enable') + $services + @("--project=$ProjectId"))

if (-not (Test-GcloudResource @('storage', 'buckets', 'describe', "gs://$Bucket"))) {
    Invoke-Gcloud @(
        'storage', 'buckets', 'create', "gs://$Bucket",
        "--project=$ProjectId",
        "--location=$Region",
        '--default-storage-class=STANDARD',
        '--uniform-bucket-level-access',
        '--public-access-prevention',
        '--soft-delete-duration=7d'
    )
}

Invoke-Gcloud @(
    'storage', 'buckets', 'add-iam-policy-binding', "gs://$Bucket",
    "--member=user:$OwnerEmail",
    '--role=roles/storage.admin'
)

foreach ($legacyBinding in @(
    @{
        Member = "projectViewer:$ProjectId"
        Role = 'roles/storage.legacyBucketReader'
    },
    @{
        Member = "projectViewer:$ProjectId"
        Role = 'roles/storage.legacyObjectReader'
    },
    @{
        Member = "projectEditor:$ProjectId"
        Role = 'roles/storage.legacyBucketOwner'
    },
    @{
        Member = "projectEditor:$ProjectId"
        Role = 'roles/storage.legacyObjectOwner'
    },
    @{
        Member = "projectOwner:$ProjectId"
        Role = 'roles/storage.legacyBucketOwner'
    },
    @{
        Member = "projectOwner:$ProjectId"
        Role = 'roles/storage.legacyObjectOwner'
    }
)) {
    Invoke-Gcloud -AllowFailure -Arguments @(
        'storage', 'buckets', 'remove-iam-policy-binding', "gs://$Bucket",
        "--member=$($legacyBinding.Member)",
        "--role=$($legacyBinding.Role)"
    )
}

foreach ($account in @(
    @{
        Id = 'atlas-dashboard-stg'
        Name = 'Atlas staging dashboard'
        Description = 'Owner-only Atlas staging dashboard identity'
    },
    @{
        Id = 'atlas-jobs-stg'
        Name = 'Atlas staging scheduled jobs'
        Description = 'Atlas staging daily and weekly job identity'
    },
    @{
        Id = 'atlas-scheduler-stg'
        Name = 'Atlas staging scheduler'
        Description = 'Invokes Atlas staging Cloud Run jobs on schedule'
    }
)) {
    $email = "$($account.Id)@$ProjectId.iam.gserviceaccount.com"
    if (-not (Test-GcloudResource @(
        'iam', 'service-accounts', 'describe', $email,
        "--project=$ProjectId"
    ))) {
        Invoke-Gcloud @(
            'iam', 'service-accounts', 'create', $account.Id,
            "--project=$ProjectId",
            "--display-name=$($account.Name)",
            "--description=$($account.Description)"
        )
    }
}

Invoke-Gcloud @(
    'storage', 'buckets', 'add-iam-policy-binding', "gs://$Bucket",
    "--member=serviceAccount:$DashboardServiceAccount",
    '--role=roles/storage.objectUser'
)
Invoke-Gcloud -AllowFailure -Arguments @(
    'storage', 'buckets', 'remove-iam-policy-binding', "gs://$Bucket",
    "--member=serviceAccount:$DashboardServiceAccount",
    '--role=roles/storage.objectViewer'
)
Invoke-Gcloud @(
    'storage', 'buckets', 'add-iam-policy-binding', "gs://$Bucket",
    "--member=serviceAccount:$JobServiceAccount",
    '--role=roles/storage.objectUser'
)

Invoke-Gcloud -AllowFailure -Arguments @(
    'projects', 'remove-iam-policy-binding', $ProjectId,
    "--member=user:$OwnerEmail",
    '--role=roles/storage.admin'
)

if (-not (Test-GcloudResource @(
    'artifacts', 'repositories', 'describe', $Repository,
    "--location=$Region",
    "--project=$ProjectId"
))) {
    Invoke-Gcloud @(
        'artifacts', 'repositories', 'create', $Repository,
        '--repository-format=docker',
        "--location=$Region",
        '--description=Private Atlas staging container images',
        "--project=$ProjectId"
    )
}

Write-Host ''
if ($Apply) {
    Write-Host '[ok] Staging foundation applied.'
} else {
    Write-Host '[plan] No cloud resources were changed.'
    Write-Host 'Re-run with -Apply -ConfirmCosts only after reviewing the plan.'
}
