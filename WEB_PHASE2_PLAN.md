# Atlas Web Phase 2: Secure Owner Cloud

Web Phase 2 moves the owner dashboard from Joe's laptop to private cloud
infrastructure. It does not add public accounts, customer access, or trading
authority.

## Current Status

Authentication, durable storage, backup restoration, and controlled-cost cloud
foundations are implemented. The dashboard service is deployed behind
owner-only Google OAuth. The first interactive owner login and final staging
validation are in progress.
Estimated Web Phase 2 completion: 90%.

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

Remaining before completing authenticated cloud staging:

- Complete the first interactive owner login.
- Verify non-owner denial, logout, expiry, and redeployment.
- Configure scheduled Cloud Run jobs for daily and weekly Atlas execution.
- Add centralized logs, uptime checks, and alerts.
- Repeat the restoration drill against the first real Cloud Storage bundle.
- Complete staging deployment and security review before production.

Current external gate:

- The Atlas project is linked to `My Billing Account`.
- The `$10` budget tracks gross usage before promotional credits.
- Private storage, Artifact Registry, a container image, and a scale-to-zero
  Cloud Run service exist.
- No scheduled jobs are active and the current service returns `403`.
- Follow `GCP_STAGING_SETUP.md` to complete owner sign-in deliberately.

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
