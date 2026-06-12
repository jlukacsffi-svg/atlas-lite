# Atlas Web Phase 3: Multi-User Foundation

Web Phase 3 introduces private tenant-aware workspaces without enabling public
registration or changing the live owner-only cloud service prematurely.

## Safety Boundary

The current owner dashboard remains the live staging application. Phase 3 code
is local-only until its database, migration, authentication, authorization,
backup, and incident-response controls pass review.

Phase 3 must not:

- Enable public registration.
- Accept an identity based on email alone.
- Allow one tenant to read or write another tenant's records.
- Store passwords or OAuth credentials in the account registry.
- Deploy a paid database without a fresh cost estimate and explicit approval.
- Expand trading authority.

## Foundation Milestone

Status: Complete.

The first local foundation includes:

- Stable tenant and user identifiers.
- Google identity binding by verified provider subject plus verified email.
- Owner, administrator, analyst, and viewer roles.
- Explicit permissions with least-privilege defaults.
- Disabled-account handling.
- Tenant-scoped workspace paths.
- Fail-closed duplicate, malformed, and unknown identity handling.
- Automated cross-tenant and role-isolation tests.

The example JSON registry is a development contract, not the planned production
database. It contains no real identity subject or secret.

## Next Milestones

1. Define the relational schema and migration workflow. Complete locally.
2. Add tenant-aware repositories for reports, watchlists, portfolios, research,
   and paper accounts. Complete at the initial local foundation level.
3. Introduce an invite-only administration workflow. Complete locally.
4. Integrate tenant resolution into a separate local application boundary.
   Complete locally.
5. Test object-level authorization across every private route. Complete for
   the initial read-only route set.
6. Complete a threat model, backup design, and cost review.
7. Deploy only after the owner-only service remains available for rollback.

## Persistence Milestone

Status: Complete locally.

The initial SQLite persistence layer provides:

- Versioned, idempotent schema migration.
- Foreign-key enforcement on every connection.
- Tenants, users, memberships, reports, watchlists, portfolios, research
  tasks, and paper accounts.
- Composite tenant/resource keys that prevent a child record from referencing
  another tenant's parent record.
- Tenant-filtered repository queries.
- Role authorization before repository reads and writes.
- Relative report-path enforcement.
- Database checks for roles, statuses, priorities, positive shares, and
  positive paper starting cash.

SQLite is a local proving environment, not the final production database.
Production database selection requires a separate architecture and cost review.

## Invite Administration Milestone

Status: Complete locally.

The administration foundation provides:

- Expiring invitations for administrator, analyst, and viewer roles.
- One-time invitation tokens stored only as SHA-256 hashes.
- Acceptance bound to the invited email and a verified Google subject.
- Replay, revoked, expired, mismatched-email, and duplicate-pending rejection.
- Guarded role changes and immediate account disabling.
- Owner protection from ordinary downgrade or disable workflows.
- Append-only audit events protected by database triggers.
- A read-only Access & Security dashboard panel showing the current release
  boundary without enabling account creation.

No invitation email is sent and no live account is created in this milestone.
The live Google Cloud service remains owner-only.

## Tenant Web Boundary Milestone

Status: Complete locally.

The separate tenant preview application provides:

- A short-lived, HMAC-signed, HttpOnly, SameSite=Strict local session.
- Database membership resolution on every request.
- Session tenant and user claims checked against the resolved membership.
- Read-only APIs for workspace identity, reports, watchlists, portfolios,
  research tasks, paper accounts, members, invitations, and audit events.
- Object-level tenant filtering for watchlist items and portfolio positions.
- Role enforcement for administrative routes.
- Immediate invalidation of existing sessions after account disabling.
- Protected static files and rejection of all mutating HTTP methods.
- A visible workspace name, role, and account identity in the dashboard.

The preview login is localhost-only and exists solely to test the boundary.
It is not a production authentication mechanism and is not deployed to cloud.

Run the isolated preview with:

```powershell
py -3.12 tenant_dashboard.py
```

Then open `http://127.0.0.1:8766`. The ignored SQLite database is created under
`tenant_data/`.

## Exit Criteria

Web Phase 3 is complete only when:

- Every user-owned database record has a tenant identifier.
- Database constraints reinforce application authorization.
- Cross-tenant read and write tests pass for every resource type.
- Invite, disable, role-change, session-revocation, export, and deletion
  workflows are audited.
- Backups and isolated restoration tests pass.
- Security and privacy reviews are complete.
- Invite-only staging is explicitly approved.

Estimated Web Phase 3 completion after the tenant web boundary: 55%.
