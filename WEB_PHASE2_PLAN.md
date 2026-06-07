# Atlas Web Phase 2: Secure Owner Cloud

Web Phase 2 moves the owner dashboard from Joe's laptop to private cloud
infrastructure. It does not add public accounts, customer access, or trading
authority.

## Current Status

Authentication and durable-storage foundations are implemented. Cloud
deployment is intentionally not yet enabled.
Estimated Web Phase 2 completion: 65%.

Completed foundation:

- Production-oriented WSGI application boundary.
- Waitress production server dependency.
- Cloud Run-compatible `PORT` handling and `0.0.0.0` binding in cloud mode.
- Container definition running as a non-root user.
- Public, data-free `/healthz` and `/readyz` service checks.
- Fail-closed cloud startup configuration.
- Google Identity-Aware Proxy signed-token verification.
- Owner-email allowlist after signed-token verification.
- Read-only HTTP surface with mutating methods rejected.
- Security headers for private dashboard responses.
- Explicit `ATLAS_DATA_ROOT` boundary for private artifacts.
- Centralized writable paths for reports, archives, research tasks, paper
  state, portfolio history, logs, and caches.
- Private Cloud Storage artifact bundle with a versioned manifest.
- SHA-256 verification and atomic local replacement on downloads.
- Generation-match preconditions on uploads to prevent silent concurrent
  overwrites.
- Strict file allowlist that excludes `.env`, source files, and credentials.
- Daily and weekly cloud-job wrappers that pull before execution and push only
  after a successful run.
- Automated authentication, authorization, readiness, and read-only tests.
- Full live daily-run validation against a disposable cloud-style data root.
- Google Cloud CLI and Application Default Credentials configured locally.
- Dedicated `atlas-capital-research-stg` project created with billing disabled.
- Guarded, plan-first bootstrap and deployment scripts for budgets, storage,
  identities, Artifact Registry, Cloud Run, IAP, jobs, and schedules.
- Zero-cost cloud policy, explicit paid-deployment confirmations, paused
  schedules, and a plan-first emergency billing stop.

Remaining before the first cloud deployment:

- Create or select a billing account, link only the dedicated staging project,
  and apply the prepared budget alerts.
- Choose a U.S. region and create separate staging and production services.
- Create and bootstrap the private Cloud Storage bucket.
- Configure Secret Manager and a least-privilege service account.
- Configure Cloud Run with no unauthenticated invoker access.
- Enable Identity-Aware Proxy and grant access only to Joe's Google account.
- Configure and verify the exact IAP audience.
- Configure scheduled Cloud Run jobs for daily and weekly Atlas execution.
- Add centralized logs, uptime checks, alerts, and backup restoration tests.
- Complete staging deployment and security review before production.

Current external gate:

- The Google account has no open Cloud Billing account.
- No paid services have been enabled.
- Billing must remain disabled until Joe reviews a written cost estimate and
  explicitly approves the monthly staging budget.
- Follow `GCP_STAGING_SETUP.md` to cross the billing gate deliberately.

## Chosen Initial Architecture

The first hosted version is deliberately single-user:

```text
Joe's browser
    |
    | HTTPS + Google sign-in
    v
Google Identity-Aware Proxy
    |
    | Signed IAP identity JWT
    v
Private Cloud Run dashboard service
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

The dashboard service must verify IAP's signed JWT in addition to relying on
the cloud access policy. Unsigned identity headers are not trusted.

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
ATLAS_AUTH_MODE=iap
ATLAS_OWNER_EMAIL=<owner Google account>
ATLAS_IAP_AUDIENCE=<exact Cloud Run IAP audience>
ATLAS_DATA_ROOT=<persistent artifact mount or synchronized directory>
ATLAS_GCS_BUCKET=<private bucket name>
ATLAS_GCS_PREFIX=owner-v1
PORT=<provided by Cloud Run>
```

The service refuses cloud startup when authentication, owner identity, or IAP
audience configuration is absent.

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

- Cloud Run rejects unauthenticated invocation.
- IAP is enabled and only Joe has the access role.
- The application rejects missing, invalid, wrong-audience, expired, and
  non-owner IAP tokens.
- The service account has no broad project-owner or editor role.
- Secrets are stored outside the image.
- Bucket uses uniform bucket-level access and public access prevention.
- Dashboard and scheduled-job service accounts have separate least-privilege
  bucket roles.
- Private data is not included in the image or build context.
- Health endpoints reveal no portfolio, research, account, or identity data.
- Logs do not include tokens, credentials, report bodies, or portfolio details.
- Backups are encrypted and a restoration has been tested.
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
- The full security checklist has passed in staging and production.
