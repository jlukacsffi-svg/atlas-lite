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
- No Atlas cloud charges have been authorized.

The controlling policy is `CLOUD_COST_POLICY.md`. Billing must remain disabled
until Joe reviews the cost estimate and explicitly approves activation.

## Billing Gate

The next owner action is to create or select a Google Cloud billing account.

Before linking it to Atlas:

1. Verify the payment method directly in Google Cloud Console.
2. Record the billing account ID, which looks like
   `000000-000000-000000`.
3. Keep the initial Atlas monthly budget at `$25`.
4. Do not reuse the unrelated `MusterApp` project.

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
- Create a `$25` monthly budget with 50%, 80%, 100%, and forecast alerts.
- Enable only required APIs.
- Create a private bucket in `us-west1`.
- Enforce uniform bucket-level access and public access prevention.
- Create separate dashboard, job, and scheduler service accounts.
- Give the dashboard read-only object access.
- Give scheduled jobs object update access.
- Create a private vulnerability-scanned Artifact Registry repository.

## Read-Only Status

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_staging_status.ps1
```

This command changes nothing.

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
8. Configure monitoring and test backup restoration.

Public registration and customer accounts remain prohibited in Web Phase 2.

Every mutating deployment command requires:

```text
-Apply -ConfirmCosts
```

Do not add these flags until the cost review and owner approval required by
`CLOUD_COST_POLICY.md` are complete.
