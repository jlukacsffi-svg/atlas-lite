# Atlas Cloud Cost Policy

Atlas cloud infrastructure must remain at zero authorized spend until Joe
explicitly approves a reviewed staging budget and billing activation.

## Current Gate

- Google Cloud project: `atlas-capital-research-stg`
- Billing must remain disabled.
- No billable Atlas resources may be created.
- Plan-only commands and read-only status checks are allowed.
- Installing local tools and keeping an empty Google Cloud project are allowed.

Enabling an API does not by itself authorize Atlas to consume paid resources.
No deployment may rely on a free tier as its only cost control.

## Required Owner Approval

Before linking billing or creating any cloud resource, Codex must:

1. Give Joe a plain-language estimate of expected monthly costs.
2. Identify each service that can create charges.
3. Explain the free allowance, if any, and what can exceed it.
4. Explain that Google Cloud budgets are alerts, not hard spending caps.
5. State the proposed monthly alert budget and shutdown procedure.
6. Receive Joe's explicit approval to enable billing and accept that budget.

Approval for planning, local development, or creating this policy is not
approval to enable billing.

## Deployment Controls

- All cloud scripts default to plan-only mode.
- Mutating commands require both `-Apply` and `-ConfirmCosts`.
- Bootstrap requires a monthly budget of at least `$5`.
- Dashboard instances remain at minimum `0` and maximum `1`.
- Scheduled jobs use one task and conservative resource limits.
- Scheduler triggers are created or updated, then left paused.
- Schedules may be resumed only after manual tests and separate owner approval.
- Staging and production must use separate projects and budgets.

## Before Go-Live

Before any first paid staging deployment, record:

- Approved monthly alert budget.
- Estimated low, expected, and high monthly cost.
- Billing account selected.
- Services and regions being enabled.
- Alert recipients and thresholds.
- Manual disable-billing procedure.
- Resource cleanup procedure.

## Emergency Stop

Verify that the project remains behind the zero-cost gate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_zero_cost_audit.ps1
```

The audit fails if billing is linked, Atlas storage exists, BigQuery datasets
exist, or deployment APIs have been enabled.

Preview the billing-disable command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_disable_billing.ps1 `
  -ProjectId atlas-capital-research-stg
```

Only add `-Apply` when Joe explicitly requests billing to be disabled. Disabling
billing stops billable services and can make cloud resources unavailable or
cause data loss, so it is an emergency control rather than a routine cleanup
command.
