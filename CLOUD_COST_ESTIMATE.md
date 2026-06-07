# Atlas Staging Cloud Cost Estimate

Estimate date: June 7, 2026

This estimate covers the first private, owner-only Atlas staging deployment in
`us-west1`. It does not authorize deployment.

## Proposed Limit

- Target monthly usage: `$0-$5`
- Monthly budget alert: `$10`
- Budget measurement: gross usage before promotional credits
- Expected promotional-credit impact: minimal
- Dashboard minimum instances: `0`
- Dashboard maximum instances: `1`
- Daily and weekly schedules: paused during initial validation

Google Cloud budgets notify; they do not stop usage automatically. Promotional
credits can expire or exclude some products. Joe must verify the displayed
credit balance and expiration date before billing is linked.

## Expected Services

| Service | Planned use | Cost expectation |
|---|---|---|
| Cloud Run | One small private dashboard, scaling to zero | Usually within the monthly free allowance at owner-only traffic; usage above the allowance is metered |
| Cloud Run Jobs | One manual daily job and one manual weekly job during validation | Usually negligible; jobs are not scheduled until separately approved |
| Cloud Storage | Approximately 10-25 MB of private Atlas state initially | Less than one cent per month at current regional storage rates, excluding operations and transfer |
| Artifact Registry | One small container image with old images cleaned up | First 0.5 GB is currently free; storage above that is metered |
| Cloud Build | Occasional small staging builds | Expected within the billing-account monthly free build-minute allowance |
| Cloud Scheduler | Two jobs, initially paused | Currently within the first three jobs free per billing account; paused jobs still count |
| Logging and Monitoring | Basic staging logs and health signals | Expected to be small; verbose logging and long retention can create charges |
| Identity-Aware Proxy and IAM | Owner-only authentication and authorization | No meaningful usage charge expected for this design |
| Secret Manager | Small number of secrets, only if required | Small metered storage/access cost may apply |

Automatic Artifact Registry vulnerability scanning is excluded from the first
deployment because it can add a separate charge.

## Monthly Scenarios

These are engineering estimates, not Google quotes:

- Low: `$0-$1` when traffic is light and schedules remain paused.
- Expected: `$1-$5` with daily owner use and limited job executions.
- High alert scenario: `$10` if usage, logging, builds, or retained images are
  greater than expected.

If forecast or actual spend approaches `$5`, pause jobs and investigate. If it
approaches `$10`, disable Atlas billing unless Joe explicitly approves a new
budget.

## Before Activation

1. Confirm the remaining promotional credit and expiration in Billing.
2. Confirm the billing account is `My Billing Account`.
3. Approve the `$10` monthly alert budget.
4. Run the pre-activation audit.
5. Apply only the foundation and budget.
6. Review Billing reports before deploying the dashboard.
7. Deploy the dashboard with schedules paused.
8. Review costs again after 24 hours and after 7 days.

## Official Pricing References

- Google Cloud Free Program:
  https://docs.cloud.google.com/free/docs/free-cloud-features
- Cloud Billing budgets:
  https://docs.cloud.google.com/billing/docs/how-to/budgets
- Cloud Run pricing:
  https://cloud.google.com/run
- Cloud Storage pricing:
  https://cloud.google.com/storage/pricing
- Artifact Registry pricing:
  https://cloud.google.com/artifact-registry/pricing
- Cloud Scheduler pricing:
  https://cloud.google.com/scheduler/pricing
- Cloud Build pricing:
  https://cloud.google.com/build/pricing
