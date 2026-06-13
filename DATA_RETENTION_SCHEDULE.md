# Atlas Data Retention Schedule

Status: Internal engineering baseline. Legal review required before external
users.

Effective internally: June 13, 2026

## Principles

- Collect and retain only what supports a documented product, security, legal,
  licensing, accounting, or operational purpose.
- Tenant-owned records are distinct from a user's external identity.
- Deletion must propagate through active systems and expire from backups on a
  documented cycle.
- Security evidence must not be silently altered or deleted by ordinary product
  workflows.
- Legal hold overrides ordinary deletion until the hold is released.

## Schedule

| Record | Active retention | After account/tenant closure | Disposal |
|---|---|---|---|
| User identity and membership | Life of account | Pseudonymize within 30 days after approved deletion, unless required for security or law | Remove direct identifiers |
| Pending invitations | Until accepted, revoked, or expired | Delete token hash and direct email within 90 days | Secure database deletion |
| Sessions and OAuth state | Minutes to 1 hour | Expire automatically | Cryptographic expiry |
| Application access logs | 90 days | Same period | Provider lifecycle deletion |
| Security and administration audit events | 7 years | Retain with pseudonymized actor where appropriate | Controlled expiry after legal review |
| Reports and research | Tenant-controlled while active | Export or delete within 90 days of tenant closure, subject to legal hold | Tenant-approved deletion |
| Portfolio and watchlist data | Tenant-controlled while active | Delete within 30 days after approved tenant closure | Database deletion |
| Paper-trading records | Tenant-controlled while active | Retain up to 7 years for model evaluation and disputes, then delete or anonymize | Controlled deletion |
| Support communications | 2 years after resolution | Same period | Mailbox/ticket deletion |
| Privacy requests and completion evidence | 3 years after completion | Same period | Controlled deletion |
| Incident records and forensic evidence | 7 years after closure | Same period | Security-owner approval |
| Database backups | Rolling 35 days in staging; production period requires review | Expire through lifecycle policy | Managed encrypted deletion |
| Local caches | 7 to 30 days by source | Delete when no longer required | Automated cache expiry |
| Billing and contractual records | As required by tax, contract, and accounting rules | Usually 7 years, subject to counsel | Controlled deletion |

## Deletion Workflow

1. Verify requester identity and authority.
2. Identify tenant-owned, user-owned, security, backup, and legal-hold records.
3. Disable access immediately when appropriate.
4. Delete or pseudonymize active-system records.
5. Record completion without retaining unnecessary personal information.
6. Allow encrypted backups to expire on schedule rather than editing backup
   archives in place.
7. Confirm completion and explain retained categories and reasons.

## Review

Review this schedule at least annually and whenever Atlas adds a data category,
provider, jurisdiction, regulated activity, payment feature, brokerage
integration, or materially different customer type.

