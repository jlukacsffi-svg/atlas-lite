# Atlas Security Incident Response Plan

Status: Internal engineering playbook. Legal and external security review
required before external users.

Effective internally: June 13, 2026

## Objectives

Protect people and tenant data, contain harm, preserve evidence, restore secure
operations, communicate accurately, meet notification duties, and improve
controls after every incident.

## Roles

- Incident commander: Joe Lukacsffi until a delegated security owner exists.
- Technical lead: isolates services, revokes credentials, preserves evidence,
  investigates scope, remediates, and restores.
- Privacy/legal lead: counsel or designated advisor determines notification,
  law-enforcement, contractual, and regulatory obligations.
- Communications lead: prepares factual user and provider communications
  approved by the incident commander and legal lead.

One person may temporarily hold several roles, but major decisions and evidence
must be logged.

## Severity

| Level | Example | Initial response target |
|---|---|---|
| SEV-1 Critical | Confirmed cross-tenant exposure, stolen privileged credentials, destructive compromise, real-trading impact | 15 minutes |
| SEV-2 High | Suspected private-data exposure, active account takeover, material service compromise | 1 hour |
| SEV-3 Medium | Contained vulnerability or limited security event with no confirmed exposure | 4 hours |
| SEV-4 Low | Policy violation, unsuccessful attack, low-risk defect | 1 business day |

## Detect And Triage

1. Record time, reporter, affected systems, indicators, and known users.
2. Assign severity without minimizing uncertainty.
3. Preserve relevant logs, database generations, deployment revisions,
   configuration, and screenshots.
4. Open a private incident record. Do not place personal data or secrets in
   source control or ordinary chat.
5. Determine whether the event is ongoing and whether external help is needed.

## Contain

- Disable affected accounts, sessions, keys, jobs, endpoints, or services.
- Preserve the owner-only service as a rollback path.
- Pause invitations, exports, deletion completion, and scheduled processing
  when integrity is uncertain.
- Rotate exposed secrets through managed secret storage.
- Do not destroy evidence while containing the event.

## Eradicate And Recover

- Identify root cause and all affected assets.
- Patch or remove the cause and validate tenant isolation.
- Restore only from checksum-verified, integrity-tested backups.
- Reissue credentials and invalidate sessions.
- Run regression, authorization, recovery, and readiness tests.
- Increase monitoring and observe the restored environment before normal use.

## Notification

The privacy/legal lead determines who must be notified, by when, and with what
content under applicable law, contracts, and provider rules. Communications
must state what happened, what information was involved, what Atlas did, what
the recipient should do, and how to obtain help. Do not speculate or conceal a
material fact.

## Evidence And Documentation

Maintain a timeline, decisions, commands, affected record categories, evidence
hashes, notifications, restoration results, costs, and follow-up owners.
Restrict evidence access and apply the retention schedule.

## Post-Incident Review

Within five business days after stabilization:

1. Document root cause and control failures.
2. Record what detected the event and what delayed response.
3. Assign corrective actions with owners and deadlines.
4. Update tests, threat model, policies, monitoring, and training.
5. Decide whether external users or autonomy levels must remain suspended.

## Emergency Contacts

- Owner: Joe Lukacsffi
- Atlas email: `atlas.capital.reports@gmail.com`
- Google Cloud support and billing contacts: verify in the console before beta.
- Legal counsel, cyber insurer, forensic provider, and law enforcement:
  intentionally unassigned until external readiness review.

## Reference Basis

- NIST SP 800-61 Revision 3:
  https://csrc.nist.gov/pubs/sp/800/61/r3/final
- FTC Data Breach Response guide:
  https://www.ftc.gov/business-guidance/resources/data-breach-response-guide-business

