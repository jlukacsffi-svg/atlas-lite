# Atlas Web Platform Plan

The Atlas Web Platform will turn the proven Atlas research engine into a
modern, secure, multi-user web product.

This is a parallel product track. It must not interrupt the current research,
paper-trading, risk, and evaluation work. The local Atlas system remains the
development and proving environment until the web architecture is ready.

## Product Vision

Users should be able to sign in securely and see a private Atlas workspace
containing only their own information.

The experience should use modern, responsive web design and clear graphics to
make complex research easy to scan.

Planned views include:

- Executive dashboard.
- Morning and weekly briefs.
- Interactive market and sector charts.
- Security scores and score histories.
- Watchlists and opportunity rankings.
- Research tasks, findings, and owner decisions.
- Portfolio allocation, performance, and risk graphics.
- Paper-trading proposals, positions, attribution, and benchmark comparisons.
- Alerts and notification preferences.
- Account, security, privacy, and subscription settings.

Email remains useful as a notification and delivery channel, but the website
becomes the primary product experience.

## Design Direction

The interface should feel like a serious modern financial research workspace:

- Quiet, information-dense, and professional.
- Responsive across desktop, tablet, and mobile.
- Fast to scan and efficient for repeated daily use.
- Accessible by keyboard and assistive technology.
- Clear charts with meaningful labels, comparison periods, and data sources.
- Restrained visual styling with strong hierarchy rather than decorative
  dashboards.
- Consistent design system, navigation, loading, empty, error, and offline
  states.

Visualizations may include:

- Portfolio value and benchmark performance.
- Allocation and concentration.
- Score history and component breakdowns.
- Sector heat maps.
- Price and event timelines.
- Opportunity/risk matrices.
- Research workflow and proposal status.
- Paper-trade attribution and drawdown.

## Account And Tenant Model

Atlas must be multi-user by design before public account creation is enabled.

Each user receives a private workspace. Data belonging to one user must never
be returned to another user.

Initial account rollout:

1. Owner-only internal account.
2. Invite-only trusted-user accounts.
3. Controlled beta with account administration and support tools.
4. Public self-service registration only after security, privacy, reliability,
   and operational reviews.

Potential account roles:

- Account owner.
- Administrator.
- Analyst or collaborator.
- Read-only viewer.

Future organization accounts may support teams, but personal accounts should
remain the first multi-user model.

## Security Requirements

Security is a release requirement, not a later enhancement.

The hosted product must include:

- Proven managed authentication instead of custom password storage.
- Email verification and secure account recovery.
- Multi-factor authentication and passkey support when available.
- Short-lived sessions, secure cookies, CSRF protection, and session revocation.
- Server-side authorization on every private resource.
- Tenant identifiers and ownership checks on every user-owned record.
- Database constraints and automated tests for tenant isolation.
- Encryption in transit and at rest.
- Managed secret storage; no production secrets in source files or prompts.
- Rate limiting, abuse protection, and bot controls.
- Immutable security, financial-decision, and administrative audit logs.
- Dependency, container, and source-code security scanning.
- Secure backups with restoration testing.
- Monitoring, alerting, incident response, and account lockout procedures.
- Data export and deletion workflows.
- Privacy policy, terms of service, and appropriate financial disclaimers before
  public availability.

Brokerage credentials must never be stored directly by Atlas. Any future
brokerage connection requires explicit owner approval, a dedicated security
design, least-privilege authorization, and read-only access first.

## Proposed Architecture Direction

Technology choices should be confirmed when implementation begins, but the
platform should separate:

- Web frontend and design system.
- Authenticated application API.
- Atlas research and scoring services.
- Scheduled background workers.
- Relational database with tenant-aware records.
- Object storage for generated reports and exports.
- Notification delivery.
- Audit and observability services.

Likely production capabilities:

- Cloud hosting independent of Joe's laptop.
- Managed relational database.
- Background job queue for market scans and report generation.
- CDN and secure static asset delivery.
- Separate development, staging, and production environments.
- Automated deployment with rollback.

The local Python research modules should be reused behind stable service
boundaries rather than rewritten merely to create a website.

## Delivery Phases

### Web Phase 1: Local Owner Dashboard

Build a read-only local dashboard using existing Atlas outputs.

Status: Complete.

Includes:

- Executive summary.
- Market overview.
- Score rankings.
- Research agenda.
- Paper-account performance.
- Core charts and responsive navigation.
- Localhost-only standard-library web server.
- Explicit read-only routes and browser security headers.

No public accounts and no cloud deployment.

### Web Phase 2: Secure Single-User Cloud

Move the owner dashboard to secure hosted infrastructure.

Status: Authentication and durable-storage foundation in progress.

Includes:

- Owner authentication.
- Managed database.
- Scheduled cloud execution.
- Private report history.
- Monitoring, backups, and secure deployment.

This phase removes the requirement that Joe's laptop remain on.

The detailed architecture, configuration contract, and deployment checklist
are in `WEB_PHASE2_PLAN.md`.

### Web Phase 3: Multi-User Foundation

Introduce private user workspaces.

Status: Local identity, role, permission, tenant-path, and relational
persistence foundations complete. Invite-only administration and its
read-only dashboard status are complete locally. The separate tenant-aware
local application boundary and initial object-level route tests are complete.
The threat model, tenant database recovery drill, tenant-scoped privacy export,
and guarded account deletion workflow are complete locally. Production
database, legal/privacy, and deployment review are next. The live cloud service
remains owner-only.

Includes:

- Invite-only account creation.
- Tenant-aware data model.
- Per-user watchlists, reports, portfolios, and paper accounts.
- Role and permission model.
- Tenant-isolation tests and security review.
- Administrative support tools.

The detailed safety boundary and delivery checklist are in
`WEB_PHASE3_PLAN.md`.

### Web Phase 4: Customer Product Beta

Introduce a controlled external beta.

Includes:

- Account onboarding and recovery.
- Notification preferences.
- Usage limits and subscription foundations.
- Privacy controls and data export/deletion.
- Product analytics that do not expose financial data.
- Support and incident-response workflows.

### Web Phase 5: Public Product

Enable self-service registration only after the platform demonstrates:

- Reliable tenant isolation.
- Stable operations and backups.
- Security testing and incident readiness.
- Clear legal, privacy, and financial-risk disclosures.
- Sustainable data licensing and operating costs.

## Relationship To Trading Stages

The web platform and trading autonomy are separate dimensions.

A modern website does not grant Atlas more financial authority.

- Paper proposals may be reviewed on the website.
- Human-approved real-trade workflows require Stage 6 authorization.
- Limited autonomous trading remains Stage 7 and requires separate approval.
- User accounts must never inherit Joe's trading permissions or private data.

## Near-Term Rule

Do not pause the Stage 5 evaluation period to build the full hosted product.

Begin Web Phase 1 only as a read-only presentation layer over stable Atlas
outputs. Advance to cloud and multi-user phases incrementally, with security and
tenant isolation tested before real users are invited.

## Success Test

The web platform succeeds when each user can securely access a polished,
responsive Atlas workspace containing only their own research, portfolio, and
paper-trading information, with clear graphics, reliable cloud operation, and a
complete audit trail.
