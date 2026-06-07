# Atlas Cloud Cost Policy

Atlas may use a small amount of Google Cloud credit for controlled staging.
The goal is minimum practical cost, not an absolute zero-cost requirement.

## Current Cost Envelope

- Google Cloud project: `atlas-capital-research-stg`
- Available promotional credit reported by Joe: approximately `$300`.
- Initial target usage: `$0-$5` per month.
- Initial recurring alert budget: `$10` per month.
- Billing remains disabled until Joe approves the written deployment estimate.
- Staging is the only environment authorized for initial cloud spending.

Promotional credit is a cushion, not a spending control. Its remaining balance,
expiration date, and eligible services must be checked in Google Cloud Billing
before activation. A payment method can be charged after credits expire, are
exhausted, or do not apply to a service.

## Required Owner Approval

Before linking billing or creating a cloud resource, Codex must:

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
- Dashboard instances remain at minimum `0` and maximum `1`.
- Scheduled jobs use one task and conservative resource limits.
- Scheduler triggers are created or updated, then left paused.
- Container vulnerability scanning is disabled for the initial staging launch.
- Schedules and optional paid features require separate approval.
- Staging and production must use separate projects and budgets.

## Cost Review

The current estimate is maintained in `CLOUD_COST_ESTIMATE.md`.

Before the first deployment, record:

- Credit balance and expiration date observed in Google Cloud.
- Approved monthly alert budget.
- Estimated low, expected, and high monthly cost.
- Billing account selected.
- Services and regions being enabled.
- Alert recipients and thresholds.
- Manual disable-billing procedure.
- Resource cleanup procedure.

## Pre-Activation Audit

Verify that the project has not crossed the billing gate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_zero_cost_audit.ps1
```

The audit fails if billing is linked, Atlas storage exists, BigQuery datasets
exist, or deployment APIs have been enabled. After approved deployment, use the
normal staging status and billing reports instead.

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
