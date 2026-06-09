# Atlas Web Phase 2: Secure Owner Cloud

Web Phase 2 moves the owner dashboard from Joe's laptop to private cloud
infrastructure. It does not add public accounts, customer access, or trading
authority.

## Current Status

Authentication, durable storage, backup restoration, and controlled-cost cloud
foundations are implemented. The dashboard service is deployed behind
owner-only Google OAuth. Interactive owner login is working in the live
staging service; cloud jobs, monitoring, cross-device testing, and final
staging validation remain. Daily and weekly jobs are deployed and manually
validated, while their recurring triggers remain paused.
Estimated Web Phase 2 completion: 98%.

Completed foundation:

- Production-oriented WSGI application boundary.
- Waitress production server dependency.
- Cloud Run-compatible `PORT` handling and `0.0.0.0` binding in cloud mode.
- Container definition running as a non-root user.
- Public, data-free `/healthz` and `/readyz` service checks.
- Fail-closed cloud startup configuration.
- Google Identity-Aware Proxy signed-token verification.
- Owner-email allowlist after signed-token verification.
- Google OpenID Connect authorization-code flow for personal-project hosting.
- CSRF state, nonce, verified ID-token, issuer, audience, and owner checks.
- HMAC-signed one-hour owner sessions with Secure, HttpOnly, SameSite cookies.
- Five-minute signed OAuth state cookies and fail-closed callback handling.
- Secret Manager deployment references for client and session credentials.
- Read-only HTTP surface with mutating methods rejected.
- Security headers for private dashboard responses.
- Explicit `ATLAS_DATA_ROOT` boundary for private artifacts.
- Centralized writable paths for reports, archives, research tasks, paper
  state, portfolio history, logs, and caches.
- Private Cloud Storage artifact bundle with a versioned manifest.
- Bucket policy removes default legacy project-wide storage bindings and grants
  Joe explicit bucket administration while granting only the dedicated
  dashboard and job identities direct object access.
- The unused default Compute Engine service account does not retain the broad
  project `Editor` role.
- The build identity has the purpose-built Cloud Build Builder role while the
  broad project `Editor` role remains removed.
- SHA-256 verification and atomic local replacement on downloads.
- Generation-match preconditions on uploads to prevent silent concurrent
  overwrites.
- Strict file allowlist that excludes `.env`, source files, and credentials.
- Daily and weekly cloud-job wrappers that pull before execution and push only
  after a successful run.
- Automated authentication, authorization, readiness, and read-only tests.
- Full live daily-run validation against a disposable cloud-style data root.
- Google Cloud CLI and Application Default Credentials configured locally.
- Dedicated `atlas-capital-research-stg` project with controlled billing and a
  `$10` gross-usage monthly budget.
- Guarded, plan-first bootstrap and deployment scripts for budgets, storage,
  identities, Artifact Registry, Cloud Run, Google OAuth, jobs, and schedules.
- Controlled-cost cloud policy, explicit paid-deployment confirmations, paused
  schedules, a `$10` alert budget, and a plan-first emergency billing stop.
- Checksum-verified local private backup archives.
- Clear handling rule that local ZIP backups require private encrypted storage;
  application-level archive encryption is not claimed.
- Guarded restores that validate the complete archive before writing.
- Automated tamper, path-traversal, unexpected-entry, and overwrite tests.
- Successful isolated restoration drill against the current Atlas private
  state.
- Successful live owner Google sign-in to the Cloud Run dashboard.
- PKCE authorization-code protection with the verifier retained only in the
  signed, five-minute OAuth state cookie.
- Strict handling of Google's equivalent basic email-scope aliases without
  globally relaxing OAuth scope validation.
- Successful authenticated dashboard access after a fresh Cloud Run
  redeployment.
- Throttled cloud-artifact refresh with last-known-data fallback.
- Successful manual daily and weekly Cloud Run job executions.
- Paused daily and weekly Cloud Scheduler triggers.
- A low-frequency public readiness check and owner email alerting for
  dashboard outages and Cloud Run job failures.
- Guarded schedule controls require explicit recurring-execution approval and
  verify job history plus monitoring before resume.
- Artifact Registry retention is installed in dry-run mode, keeps the three
  newest images, and does not currently delete anything.
- A read-only staging readiness audit checks 25 security, identity, scaling,
  storage, job, schedule, monitoring, and retention controls.
- Preliminary monitoring found no Cloud Run error logs but exposed regional
  probe noise under a 10-second scale-to-zero cold-start timeout. The timeout
  is now 30 seconds at the same ten-minute frequency.
- The live sidebar identifies the hosted environment as `Secure owner cloud`
  and exposes a session sign-out link.

Remaining before completing authenticated cloud staging:

- Complete a cross-device owner login test.
- Perform a manual non-owner denial check; automated denial coverage passes.
- Review one complete day of uptime and alert telemetry.
- Review the Artifact Registry cleanup dry run before enabling deletion.
- Activate schedules only after separate owner approval.
- Complete the remaining manual staging security review before production.

Current external gate:

- The Atlas project is linked to `My Billing Account`.
- The `$10` budget tracks gross usage before promotional credits.
- Private storage, Artifact Registry, a container image, and a scale-to-zero
  Cloud Run service exist.
- No scheduled jobs are active.
- Daily and weekly jobs exist and have each completed one successful manual
  execution.
- Monitoring and owner email notification policies are active.
- The current service redirects unauthenticated users to Google and admits only
  the configured owner after signed identity verification.

## Chosen Initial Architecture

The first hosted version is deliberately single-user:

```text
Joe's browser
    |
    | HTTPS + Google sign-in
    v
Cloud Run public login/callback boundary
    |
    | Google OpenID Connect + signed owner session
    v
Owner-only Atlas dashboard application
    |
    +-- Atlas read-only application API
    +-- Managed persistent research storage
    +-- Managed logs and monitoring

Cloud Scheduler
    |
    v
Private Cloud Run jobs
    |
    +-- Daily research/report run
    +-- Weekly summary run
    +-- Persistent archive updates
```

Cloud Run permits unauthenticated network invocation only because `/login` and
`/oauth/callback` must be reachable. The application allows public access only
to those routes and data-free health checks. Dashboard pages and APIs require a
valid signed owner session. Unsigned identity headers are never trusted.

## Runtime Configuration

Local preview defaults:

```text
ATLAS_WEB_MODE=local
ATLAS_AUTH_MODE=local
PORT=8765
```

Cloud mode requires all of:

```text
ATLAS_WEB_MODE=cloud
ATLAS_AUTH_MODE=google_oauth
ATLAS_OWNER_EMAIL=<owner Google account>
ATLAS_GOOGLE_CLIENT_ID=<Secret Manager reference>
ATLAS_GOOGLE_CLIENT_SECRET=<Secret Manager reference>
ATLAS_OAUTH_REDIRECT_URI=<exact HTTPS callback>
ATLAS_SESSION_SECRET=<Secret Manager reference, at least 32 characters>
ATLAS_DATA_ROOT=<persistent artifact mount or synchronized directory>
ATLAS_GCS_BUCKET=<private bucket name>
ATLAS_GCS_PREFIX=owner-v1
PORT=<provided by Cloud Run>
```

The service refuses cloud startup when authentication, owner identity, callback
URI, credentials, session key, or persistent storage configuration is absent.

Do not put production values in source files, `.env` examples, container
images, prompts, or GitHub. Production configuration belongs in managed cloud
configuration and Secret Manager.

## Persistent Data Migration

Cloud Run's container filesystem is temporary. Atlas now uses a private Cloud
Storage bundle as the first single-user hosted system of record.

The bundle includes only allowlisted private runtime artifacts:

- Research snapshots and archive indexes.
- Research tasks and role briefs.
- Paper account, append-only ledger, and performance report.
- Morning and weekly reports.
- Portfolio history and optional private portfolio configuration.

Every bundle has a versioned manifest containing object paths, sizes, and
SHA-256 checksums. Downloads verify the manifest and write files atomically.
Uploads use object-generation preconditions and publish the manifest last.

This object-storage design is intentionally a Phase 2 single-owner bridge. Web
Phase 3 still requires a tenant-aware relational database for multi-user data.

Least-privilege service roles:

- Dashboard service: bucket-level `roles/storage.objectViewer`.
- Scheduled daily/weekly job: bucket-level `roles/storage.objectUser`.
- Neither service receives Storage Admin, Editor, or Owner.

Cloud commands:

```text
python cloud_sync.py pull
python cloud_sync.py push
python cloud_daily.py
python cloud_weekly.py
```

The Python client uses Application Default Credentials. Do not create or place
service-account key files in the repository or container image.

## Deployment Safety Checklist

Before any staging URL is shared:

- Unauthenticated dashboard/API access is rejected or redirected to login.
- Google OAuth is in testing mode with Joe as the only test user.
- The application rejects missing, invalid, wrong-audience, expired,
  wrong-nonce, unverified-email, and non-owner identities.
- Session and OAuth state cookies are signed, short-lived, Secure, HttpOnly,
  and SameSite.
- The service account has no broad project-owner or editor role.
- Secrets are stored outside the image.
- Bucket uses uniform bucket-level access and public access prevention.
- Dashboard and scheduled-job service accounts have separate least-privilege
  bucket roles.
- Private data is not included in the image or build context.
- Health endpoints reveal no portfolio, research, account, or identity data.
- Logs do not include tokens, credentials, report bodies, or portfolio details.
- Backups are encrypted and a restoration has been tested.
- Private local backup archives remain ignored by Git and outside public
  storage.
- Staging and production use separate services and data.
- No brokerage credentials or real-order capability exist.

## First Deployment Success Test

Web Phase 2 is complete when:

- Joe can open Atlas from another device using Google sign-in.
- No unauthenticated user can reach the application.
- Atlas runs daily and weekly without Joe's laptop.
- Dashboard and report history survive service restarts and redeployments.
- Monitoring reports failures.
- Backup restoration has been demonstrated.
- The local restoration drill passes before cloud deployment, and the cloud
  restoration drill passes before production.
- The full security checklist has passed in staging and production.
