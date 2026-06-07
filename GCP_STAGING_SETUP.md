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
- Billing is disabled.
- No bucket, image repository, Cloud Run service, scheduled job, or public URL
  exists yet.
- Joe has authorized a future minimal-cost staging deployment after reviewing
  its estimate and explicitly approving the `$10` monthly alert budget.

The controlling policy is `CLOUD_COST_POLICY.md`. Billing must remain disabled
until Joe verifies the promotional-credit balance and expiration, reviews
`CLOUD_COST_ESTIMATE.md`, and explicitly approves activation.

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

To verify the pre-activation gate, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_zero_cost_audit.ps1
```

This audit is read-only and exits with an error if billing or Atlas cloud
resources are detected. It is intended for use before the approved deployment.

## Deployment Order

After bootstrap:

1. Upload the initial private artifact bundle with `cloud_sync.py push`.
2. Build and deploy the owner-only dashboard with
   `gcp_deploy_staging.ps1`.
3. Complete the first direct-IAP setup in Google Cloud Console if Google
   requires OAuth consent configuration.
4. Verify only Joe can access the dashboard.
5. Deploy daily and weekly Cloud Run jobs with
   `gcp_deploy_jobs_staging.ps1`.
6. Execute each job manually once.
7. Obtain separate owner approval before resuming the paused schedules.
8. Create a private backup and run the local restoration drill.
9. Configure monitoring and repeat restoration against the cloud bundle.

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
