# Atlas Tenant Threat Model

## Scope

This model covers the Web Phase 3 local tenant boundary: identities,
memberships, invitations, tenant-owned records, administration events, signed
sessions, and SQLite backup/recovery. The live cloud service remains
owner-only.

## Protected Assets

- Tenant identity and membership records.
- Private reports, watchlists, portfolios, paper accounts, and research tasks.
- Invitation tokens and administration audit history.
- Tenant database backups and restore procedures.
- Session-signing secrets and authenticated sessions.

## Trust Boundaries

1. Browser to web application.
2. Signed session to active database membership.
3. Web application to tenant repository.
4. Tenant repository to SQLite constraints and storage.
5. Live database to private backup storage.
6. Future managed identity and database services to the Atlas application.

## Threats And Controls

| Threat | Current control | Verification |
|---|---|---|
| Session tampering or theft | HMAC signature, 30-minute expiry, HttpOnly and SameSite=Strict cookie, no-store responses | Web boundary tests |
| Forged or stale identity claims | Provider subject, verified email, tenant ID, and user ID are checked; membership is reloaded every request | Identity and disabled-account tests |
| Cross-tenant object access | Tenant is supplied by the active membership, never by the request; composite database keys and tenant filters isolate records | Repository and route isolation tests |
| Privilege escalation | Server-side role permissions; signed claims must exactly match active membership | Role and forged-claim tests |
| Invitation theft or replay | Random token is stored only as SHA-256, bound to email, expires, and becomes unusable after acceptance or revocation | Invitation lifecycle tests |
| Audit-history alteration | Administration events are append-only through SQLite triggers | Trigger test |
| Database corruption | SQLite integrity and foreign-key checks run before restore | Backup validation tests |
| Backup tampering | Strict two-file archive, size limit, SHA-256 checksum, schema version, and logical table inventory | Tamper and unexpected-entry tests |
| Unsafe or accidental restore | Validation occurs in an isolated temporary database; existing targets require explicit approval; live path replacement is refused | Restore tests and drill |
| Backup disclosure | Backups remain Git-ignored and must be stored only in private encrypted-at-rest storage | Operational policy |

## Recovery Procedure

1. Create a consistent backup using SQLite's online backup API.
2. Inspect the archive and verify its checksum, schema, integrity, foreign keys,
   and table inventory.
3. Restore to a new isolated path.
4. Run the automated drill and application tests.
5. Replace a live database only during a controlled maintenance window using
   an operator-managed atomic file replacement.

The ZIP archive provides integrity validation, not encryption. Never place a
tenant backup in source control, public object storage, email, or an
unencrypted device.

## Residual Risks Before Production

- The local SQLite file and ZIP archive do not provide application-level
  encryption.
- The local preview login is intentionally not production authentication.
- Production requires managed identity, MFA/account recovery, centralized
  session revocation, managed encrypted storage, monitoring, and tested cloud
  restoration.
- The current audit log protects against application-level update and deletion,
  not an administrator with direct filesystem/database access.
- Security review, privacy controls, incident response, and external testing
  remain required before inviting real customers.

## Reference Baseline

- OWASP Application Security Verification Standard 5.0.
- OWASP Session Management and Secrets Management guidance.
- NIST cloud multi-tenancy guidance.
- Python SQLite online backup API.
