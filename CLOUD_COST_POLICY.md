# Atlas Cloud Cost Policy

Atlas may use a small amount of Google Cloud credit for controlled staging.
The goal is minimum practical cost, not an absolute zero-cost requirement.

## Current Cost Envelope

- Google Cloud project: `atlas-capital-research-stg`
- Available promotional credit reported by Joe: approximately `$300`.
- Initial target usage: `$0-$5` per month.
- Initial recurring alert budget: `$10` per month.
- Billing is linked only to the dedicated staging project.
- A `$10` monthly gross-usage budget is active.
- Staging is the only environment authorized for initial cloud spending.

Promotional credit is a cushion, not a spending control. Its remaining balance,
expiration date, and eligible services must be checked in Google Cloud Billing
before activation. A payment method can be charged after credits expire, are
exhausted, or do not apply to a service.

## Required Owner Approval

Before creating a new billable service or materially increasing usage, Codex
must:

1. Give Joe a plain-language low, expected, and high monthly estimate.
2. Identify every planned service that can create charges.
3. Explain relevant free allowances and what can exceed them.
4. Explain that Google Cloud budgets are alerts, not hard spending caps.
5. Confirm the credit balance and expiration shown in the Billing console.
6. State the monthly alert budget and shutdown procedure.
7. Receive Joe's explicit approval for that deployment and budget.

Approval to incur some future staging cost is not approval for unlimited
spending, production deployment, or a changed architecture.

## Deployment Controls

- All cloud scripts default to plan-only mode.
- Mutating commands require both `-Apply` and `-ConfirmCosts`.
- The initial bootstrap defaults to a `$10` monthly alert budget.
- Budget alerts track gross usage before promotional credits are applied.
- The budget is created before application deployment services are enabled.
- Billing and the budget were activated before Atlas runtime resources.
- Dashboard instances remain at minimum `0` and maximum `1`.
- Scheduled jobs use one task and conservative resource limits.
- Scheduler triggers are created or updated, then left paused.
- Schedule resume requires `-Apply -ConfirmCosts
  -ApproveRecurringExecution` and verifies successful manual jobs plus active
  monitoring before changing either trigger.
- Artifact Registry cleanup defaults to dry-run mode, keeps the three newest
  image versions, and only considers versions older than 14 days.
- Active image deletion requires a separate `-ActivateDeletion` flag.
- Container vulnerability scanning is disabled for the initial staging launch.
- Schedules and optional paid features require separate approval.
- Staging and production must use separate projects and budgets.

## Cost Review

The current estimate is maintained in `CLOUD_COST_ESTIMATE.md`.

Current Artifact Registry status on June 8, 2026:

- Repository size: `464.400 MB`.
- Cleanup policy: installed in dry-run mode.
- Deletion behavior: inactive; no images are deleted by the policy.

For each deployment stage, record:

- Credit balance and expiration date observed in Google Cloud.
- Approved monthly alert budget.
- Estimated low, expected, and high monthly cost.
- Billing account selected.
- Services and regions being enabled.
- Alert recipients and thresholds.
- Manual disable-billing procedure.
- Resource cleanup procedure.

## Historical Pre-Activation Audit

Verify that the project has not crossed the billing gate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_zero_cost_audit.ps1
```

The audit now fails by design because the approved staging foundation exists.
Use `scripts/gcp_staging_status.ps1` and Google Cloud Billing reports for the
active staging environment.

## Emergency Stop

Preview the billing-disable command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_disable_billing.ps1 `
  -ProjectId atlas-capital-research-stg
```

Only add `-Apply` when Joe explicitly requests billing to be disabled or an
unapproved billing link is detected. Disabling billing stops billable services
and can make cloud resources unavailable or cause data loss.
