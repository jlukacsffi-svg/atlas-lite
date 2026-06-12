# Atlas Staging Cloud Cost Estimate

Estimate date: June 12, 2026

This estimate covers the private, owner-only Atlas staging deployment in
`us-west1`. The initial foundation has been explicitly authorized and created;
new services or higher recurring usage still require review.

## Proposed Limit

- Target monthly usage: `$0-$5`
- Monthly budget alert: `$10`
- Budget measurement: gross usage before promotional credits
- Expected promotional-credit impact: minimal
- Dashboard minimum instances: `0`
- Dashboard maximum instances: `1`
- Daily and weekly schedules: paused during initial validation

Google Cloud budgets notify; they do not stop usage automatically. Promotional
credits can expire or exclude some products. Joe should verify the displayed
credit balance and expiration date during each cost review.

## Expected Services

| Service | Planned use | Cost expectation |
|---|---|---|
| Cloud Run | One small private dashboard, scaling to zero | Usually within the monthly free allowance at owner-only traffic; usage above the allowance is metered |
| Cloud Run Jobs | One manual daily job and one manual weekly job during validation | Usually negligible; jobs are not scheduled until separately approved |
| Cloud Storage | Approximately 10-25 MB of private Atlas state initially | Less than one cent per month at current regional storage rates, excluding operations and transfer |
| Artifact Registry | Private dashboard images with conservative retention | Repository is 464.400 MB, just below the current 0.5 GB free allowance; a dry-run policy keeps three newest versions and considers only versions older than 14 days |
| Cloud Build | Occasional small staging builds | Expected within the billing-account monthly free build-minute allowance |
| Cloud Scheduler | Two jobs, initially paused | Currently within the first three jobs free per billing account; paused jobs still count |
| Logging and Monitoring | Basic logs, one 10-minute uptime check from three regions, and two alert policies | Approximately 12,960 uptime executions per month, below the current one-million-execution project allowance; the Cloud Run job metric condition may add about `$0.10` per month |
| Google OAuth and IAM | Owner-only authentication and authorization | No meaningful usage charge expected for this design |
| Secret Manager | Three small OAuth/session secrets | Small metered storage/access cost may apply; expected within the free allowance at this scale |

Automatic Artifact Registry vulnerability scanning is excluded from the first
deployment because it can add a separate charge.

The cleanup policy is observation-only. It cannot delete images unless its
guarded script is rerun with explicit active-deletion approval.

## Monthly Scenarios

These are engineering estimates, not Google quotes:

- Low: `$0-$1` when traffic is light and schedules remain paused.
- Expected: `$1-$5` with daily owner use and limited job executions.
- High alert scenario: `$10` if usage, logging, builds, or retained images are
  greater than expected.

If forecast or actual spend approaches `$5`, pause jobs and investigate. If it
approaches `$10`, disable Atlas billing unless Joe explicitly approves a new
budget.

## Proposed Multi-User Staging

The production architecture review selects Cloud SQL for PostgreSQL and Google
Identity Platform, but neither service is approved for activation.

Engineering estimate:

- Low: approximately `$9/month`.
- Expected: approximately `$15/month`.
- High: approximately `$25/month`.

The smallest published shared-core Cloud SQL compute price is approximately
`$7.67/month` at 730 hours before storage, backups, operations, and transfer.
Identity Platform Tier 1 providers are currently free through 50,000 monthly
active users; SMS and some MFA usage are separately metered. Atlas plans TOTP
for privileged roles.

This proposal exceeds the current `$0-$5` target and may exceed the `$10`
alert. It requires a revised budget, exact promotional-credit expiration
confirmation, and explicit owner approval before any resource is created.

## Before The Next Activation

1. Confirm the remaining promotional credit and exact expiration in Billing.
2. Review current gross cost against the `$10` alert budget.
3. Create the owner-only OAuth client and three Secret Manager values.
4. Deploy the authenticated dashboard at zero minimum and one maximum instance.
5. Keep daily and weekly schedules paused.
6. Review costs after 24 hours and after 7 days.

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
