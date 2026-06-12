# Atlas Multi-User Production Architecture Review

## Decision

Status: Conditional go for architecture; no deployment approval.

Atlas should use Cloud SQL for PostgreSQL and Google Identity Platform when the
multi-user staging environment is funded and explicitly approved. The existing
owner-only Cloud Run service remains the rollback path and must not be changed
by this work.

Public registration, external invitations, Cloud SQL creation, Identity
Platform activation, and recurring schedules remain disabled.

## Database Decision

Selected direction:

- Cloud SQL for PostgreSQL 16 in `us-west1`.
- Separate tenant staging database and service.
- Zonal instance for invite-only technical staging.
- Regional high availability before a customer beta that requires an uptime
  commitment.
- Cloud SQL Python Connector with automatic IAM database authentication.
- Dedicated Cloud Run service accounts with only Cloud SQL Client/User access.
- No static production database password.
- Small bounded application connection pool.
- Automated backups and point-in-time recovery.
- Migration job runs before traffic moves to a new revision.
- Restore drill and tenant-isolation test run before promotion.

Local adapter validation is complete:

- `app/tenant_postgres.py` reuses the existing authorization repository.
- Native PostgreSQL migrations cover all 13 tenant tables.
- `pg8000` query binding is adapted without interpolating values into SQL.
- Migrations use a transaction-scoped advisory lock.
- Composite tenant keys, partial unique indexes, identity columns, and
  append-only audit triggers are preserved.
- All 22 migration statements pass PostgreSQL parser validation.
- The Cloud SQL connection factory requires automatic IAM authentication.

Run the offline contract check with:

```powershell
py -3.12 tenant_postgres_check.py
```

This command never connects to a database or creates a cloud resource.

Cloud SQL is the correct operational database, but not a scale-to-zero service.
The smallest shared-core price published by Google is `$0.0105/hour`, or about
`$7.67/month` for compute alone at 730 hours, before storage, backups,
operations, and transfer. Atlas therefore estimates:

- Low staging: approximately `$9/month`.
- Expected staging: approximately `$15/month`.
- High staging: approximately `$25/month`.
- A dedicated-core regional high-availability customer beta will cost
  materially more and requires a new estimate.

This exceeds the current `$0-$5` target and can exceed the `$10` alert.
Creating the instance requires a fresh owner approval and revised budget.

## Identity Decision

Selected direction:

- Google Identity Platform using Google/social sign-in initially.
- Application tenant memberships remain authoritative for Atlas authorization.
- Do not create a separate Identity Platform tenant for every Atlas workspace;
  that adds complexity without improving the current personal/team model.
- Keep registration invite-only and disable end-user self-creation.
- Require verified provider subject and email.
- Require TOTP MFA for owners and administrators before external invitations.
- Support centralized session revocation and immediate disabled-account checks.
- Add abuse controls and reCAPTCHA before public registration.

Identity Platform currently lists Tier 1 providers as free through 50,000
monthly active users. SMS MFA is separately metered, so Atlas should prefer
TOTP for privileged accounts.

## Deployment And Rollback

The first multi-user deployment must be a new service, not an in-place change:

```text
atlas-dashboard-stg       existing owner-only service and rollback path
atlas-tenant-stg          future invite-only tenant service
atlas-tenant-stg database future isolated Cloud SQL database
```

Release sequence:

1. Create a fresh cost estimate and obtain explicit approval.
2. Confirm promotional-credit balance and exact expiration.
3. Create the managed identity and database in staging only.
4. Run migrations using a one-off job.
5. Import synthetic tenants only.
6. Run cross-tenant, backup, restore, and session-revocation tests.
7. Invite Joe as the sole tenant-stage user.
8. Observe logs, costs, and database connections for seven days.
9. Invite one trusted non-owner tester only after manual sign-off.

Rollback means routing users back to the unchanged owner service and disabling
the tenant service. A database migration must have a tested backward-data
strategy before traffic promotion.

## Privacy And Legal Gates

This document is an engineering review, not legal advice.

Before any external user is invited, Atlas needs:

- Privacy policy describing collected identity, portfolio, research, device,
  log, and communication data.
- Terms of service, acceptable-use rules, account termination, and limitation
  of liability.
- Written retention schedule and incident-response procedure.
- Disclosure of export/deletion exceptions for security and tenant-owned audit
  records.
- Market-data and news licensing review; public endpoints cannot rely on
  unlicensed scraping or redistribution.
- Counsel review of investment-adviser status and financial disclaimers.

The SEC notes that compensated securities analysis can meet the investment
adviser definition, while a publisher exclusion depends on facts such as
general, impersonal, bona fide, regular publication. Atlas plans personalized
portfolio and recommendation features, so it must not assume that an ordinary
website disclaimer resolves this question.

California privacy law may not apply to Atlas at its present size, but the
product should continue to support access, deletion, correction, and limited
retention by design. Applicability and exceptions require counsel review.

## Release Verdict

Architecture: approved conditionally.

Deployment: blocked.

Blocking items:

- Fresh Cloud SQL and Identity Platform cost approval.
- Exact cloud-credit expiration confirmation.
- Privacy policy and terms.
- Investment-adviser counsel review.
- Market-data licensing review.
- Incident-response and retention policies.
- Invite-only staging sign-off.

Run the fail-closed local audit with:

```powershell
py -3.12 tenant_readiness.py
```

The expected exit code is `2`: the architecture checks pass while deployment
remains intentionally unapproved.
