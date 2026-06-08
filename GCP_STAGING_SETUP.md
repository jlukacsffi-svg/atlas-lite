# Atlas Google Cloud Staging Setup

Atlas has a dedicated empty Google Cloud staging project:

```text
Project ID: atlas-capital-research-stg
Project name: Atlas Staging
Region: us-west1
Owner login: jlukacsffi@gmail.com
```

Current cloud status:

- Google Cloud CLI 571.0.0 installed.
- User login complete.
- Application Default Credentials complete.
- Dedicated staging project created.
- Billing is linked to `My Billing Account`.
- A `$10` monthly gross-usage budget is active with 25%, 50%, 80%, 100%, and
  100% forecast alerts.
- Private Cloud Storage and Artifact Registry resources are active.
- A checksum-verified private artifact bundle is stored in Cloud Storage.
- The first dashboard container image was built successfully.
- Cloud Run service `atlas-dashboard-stg` exists with zero minimum instances
  and one maximum instance.
- Owner-only Google OAuth is working on the live dashboard.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` exist and have each
  completed one successful manual execution.
- Daily and weekly Cloud Scheduler triggers exist but remain paused.
- Schedule changes use a dedicated guarded script; recurring execution cannot
  be resumed without explicit cost and recurring-execution approval flags.
- Artifact Registry is 464.400 MB and has a cleanup policy in dry-run mode.
  The policy keeps the three newest images and observes images older than 14
  days without deleting them.
- Dashboard readiness and failed-job monitoring policies email
  `jlukacsffi@gmail.com`.

The controlling policy is `CLOUD_COST_POLICY.md`. Any additional deployment
still requires plan review plus `-Apply -ConfirmCosts`.

## Billing Gate

The open billing account is named `My Billing Account`.

Before linking it to Atlas:

1. Verify the remaining promotional credit and expiration directly in Google
   Cloud Console.
2. Review `CLOUD_COST_ESTIMATE.md`.
3. Keep the initial Atlas monthly alert budget at `$10`.
4. Confirm the project is `atlas-capital-research-stg`.

Budgets send alerts but do not automatically cap spending. Atlas therefore also
uses zero minimum dashboard instances, one maximum dashboard instance, one task
per scheduled job, conservative memory limits, paused schedules, and
staging-only resources.

## Preview The Staging Plan

The bootstrap command defaults to plan-only mode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_bootstrap_staging.ps1 `
  -ProjectId atlas-capital-research-stg `
  -BillingAccount YOUR-BILLING-ID `
  -OwnerEmail jlukacsffi@gmail.com
```

It creates nothing unless both flags are added:

```text
-Apply -ConfirmCosts
```

The first activation should stop after billing and budget configuration:

```text
-Apply -ConfirmCosts -BillingAndBudgetOnly
```

That scope links the staging project and creates the budget, but does not create
Atlas storage, compute, builds, schedules, or container images.

The guarded bootstrap will:

- Link only the dedicated staging project to billing.
- Create a `$10` monthly budget with 25%, 50%, 80%, 100%, and forecast alerts
  before enabling application deployment services. The alert tracks gross usage
  before promotional credits are applied.
- Enable only required APIs.
- Create a private bucket in `us-west1`.
- Enforce uniform bucket-level access and public access prevention.
- Create separate dashboard, job, and scheduler service accounts.
- Give the dashboard read-only object access.
- Give scheduled jobs object update access.
- Create a private Artifact Registry repository without optional paid
  vulnerability scanning.

## Read-Only Status

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_staging_status.ps1
```

This command changes nothing.

Run the deeper final-staging audit with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_staging_readiness.ps1
```

This command is also read-only. It checks dashboard readiness and scale limits,
OAuth and Secret Manager configuration, dedicated service accounts, bucket
privacy and least-privilege roles, absence of the project `Editor` role, job
limits and successful executions, paused schedules, monitoring, and
non-destructive image retention. On June 8, 2026, all 24 automated checks
passed.

The audit intentionally does not mark the manual cross-device login,
non-owner denial, one-day telemetry review, or schedule approval gates as
complete.

To inspect, pause, or explicitly approve recurring schedules:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_set_schedules_staging.ps1 `
  -ProjectId atlas-capital-research-stg `
  -Action Status
```

`Resume` additionally requires `-Apply -ConfirmCosts
-ApproveRecurringExecution`. Do not use it without Joe's separate approval.

To preview the Artifact Registry retention policy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_configure_artifact_cleanup.ps1 `
  -ProjectId atlas-capital-research-stg
```

Adding `-Apply -ConfirmCosts` installs or refreshes the policy in dry-run mode.
Deletion remains inactive unless `-ActivateDeletion` is also explicitly used.

To verify the pre-activation gate, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_zero_cost_audit.ps1
```

This audit is read-only and exits with an error if billing or Atlas cloud
resources are detected. It is intended for use before the approved deployment.

## Owner Sign-In Setup

Direct Cloud Run IAP was tested and rejected for this personal staging project
because Google requires the project and permitted identities to belong to a
Google Cloud organization. Atlas instead verifies Google OpenID Connect inside
the application and allows only `jlukacsffi@gmail.com`.

One-time Google Console steps:

1. Open Google Auth Platform for `atlas-capital-research-stg`.
2. Configure the app as External and keep it in testing.
3. Add `jlukacsffi@gmail.com` as the only test user.
4. Create an OAuth client of type **Web application**.
5. Add this exact authorized redirect URI:

```text
https://atlas-dashboard-stg-851252682251.us-west1.run.app/oauth/callback
```

6. Download the client JSON. Do not paste its secret into chat or commit it.
7. Preview the secure Secret Manager transfer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_configure_oauth_secrets.ps1 `
  -ProjectId atlas-capital-research-stg `
  -OAuthClientJson "C:\path\to\client_secret.json"
```

8. After reviewing the plan, add `-Apply -ConfirmCosts`. The script creates or
   rotates three redacted secrets and generates a fresh 48-byte session key.
9. Delete the downloaded JSON after deployment is verified.

The client ID, client secret, and session key are injected from Secret Manager.
They are never stored in the image, repository, deployment command, or chat.

## Deployment Order

Completed:

1. Bootstrap the controlled-cost project.
2. Upload and restore-test the initial private artifact bundle.
3. Build the first dashboard image and create the private Cloud Run service.

Next:

1. Review one complete day of uptime and alert telemetry.
2. Complete a cross-device owner login test.
3. Perform a manual non-owner denial test.
4. Obtain separate owner approval before resuming the paused schedules.
5. Review Artifact Registry dry-run observations before considering cleanup.
6. Complete final staging security and cost review.

Public registration and customer accounts remain prohibited in Web Phase 2.

Every mutating deployment command requires:

```text
-Apply -ConfirmCosts
```

Do not add these flags until the cost review and owner approval required by
`CLOUD_COST_POLICY.md` are complete.

## Zero-Cost Restoration Drill

The local drill does not use Google Cloud or create charges:

```powershell
py -3.12 backup_restore.py create
py -3.12 backup_restore.py drill backups\atlas_backup_TIMESTAMP.zip
```

The backup contains private Atlas data. Keep it only in approved private
encrypted storage. The local ZIP is integrity-protected but is not encrypted by
Atlas. The `backups/` folder is ignored by Git.
