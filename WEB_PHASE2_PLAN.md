# Atlas Web Phase 2: Secure Owner Cloud

Web Phase 2 moves the owner dashboard from Joe's laptop to private cloud
infrastructure. It does not add public accounts, customer access, or trading
authority.

## Current Status

Foundation implemented. Cloud deployment is intentionally not yet enabled.
Estimated Web Phase 2 completion: 35%.

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
- Automated authentication, authorization, readiness, and read-only tests.

Remaining before the first cloud deployment:

- Create a dedicated Google Cloud project with billing and budget alerts.
- Choose a U.S. region and create separate staging and production services.
- Replace local JSON files with durable managed storage or a tested persistent
  synchronization process.
- Configure Secret Manager and a least-privilege service account.
- Configure Cloud Run with no unauthenticated invoker access.
- Enable Identity-Aware Proxy and grant access only to Joe's Google account.
- Configure and verify the exact IAP audience.
- Configure scheduled Cloud Run jobs for daily and weekly Atlas execution.
- Add centralized logs, uptime checks, alerts, and backup restoration tests.
- Complete staging deployment and security review before production.

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
PORT=<provided by Cloud Run>
```

The service refuses cloud startup when authentication, owner identity, or IAP
audience configuration is absent.

Do not put production values in source files, `.env` examples, container
images, prompts, or GitHub. Production configuration belongs in managed cloud
configuration and Secret Manager.

## Persistent Data Migration

Cloud Run's container filesystem is temporary. The existing local files cannot
be treated as the hosted system of record.

The migration should proceed in two steps:

1. Define repository interfaces for research snapshots, research tasks, paper
   account state, recommendations, reviews, and audit events.
2. Implement managed adapters, likely using a relational database for
   structured account and workflow data plus object storage for generated
   reports and immutable exports.

The local file adapters remain available for development and recovery testing.

## Deployment Safety Checklist

Before any staging URL is shared:

- Cloud Run rejects unauthenticated invocation.
- IAP is enabled and only Joe has the access role.
- The application rejects missing, invalid, wrong-audience, expired, and
  non-owner IAP tokens.
- The service account has no broad project-owner or editor role.
- Secrets are stored outside the image.
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
