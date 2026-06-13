# Atlas External Review Packet

Status: Prepared for counsel, data providers, and an independent security
reviewer. No external review has been completed.

Prepared: June 13, 2026

## Product Summary

Atlas Capital Research is an invite-only research and portfolio-intelligence
platform. It produces market monitoring, scores, reports, personalized
portfolio context, research tasks, and strictly simulated paper proposals.
Real trading, brokerage access, public registration, and autonomous financial
commitments are disabled.

## Investment-Adviser Counsel Questions

Counsel should review:

1. Whether compensated access to personalized portfolios, rankings, alerts,
   recommendations, or paper proposals constitutes investment advice.
2. Whether any publisher exclusion could apply and which product features
   would defeat general, impersonal, bona fide, and regular-publication
   requirements.
3. Federal versus state registration, notice, recordkeeping, custody,
   marketing, testimonial, performance-presentation, and fiduciary issues.
4. Required disclosures for model limitations, conflicts, compensation,
   affiliates, data sources, hypothetical performance, and paper trading.
5. Whether future brokerage connectivity or automated execution changes the
   analysis.
6. Terms, privacy language, age/eligibility, dispute terms, liability limits,
   and user-consent workflow.

Required written outcome:

- Applicable registrations or exemptions.
- Features permitted before registration.
- Required disclosures and records.
- Prohibited marketing or performance claims.
- Conditions for human-approved and autonomous trading stages.

## Market And News Data Review

Current sources:

| Source | Current use | External-product decision |
|---|---|---|
| Yahoo Finance chart/search endpoints and `yfinance` | Prices, metadata, headlines, analyst-action signals | Block redistribution and customer reliance pending written licensing analysis |
| Nasdaq earnings endpoint | Earnings calendar | Block customer use pending Nasdaq terms/licensing review |
| SEC EDGAR APIs and filings | Company facts, submissions, Form 4 data | Public source; continue fair-access identification, caching, and rate limits; confirm attribution and derived-display rules |
| Publisher headline links | Headline context and outbound links | Review excerpt, display, caching, attribution, and commercial-use rights |

The current Yahoo and Nasdaq endpoints must not be assumed to authorize a
commercial multi-user product. Before external beta, obtain written permission,
a commercial provider agreement, or replace them with a provider whose license
expressly covers Atlas's storage, derived analytics, display, and user count.

Required provider-review outcome:

- Permitted data fields and use cases.
- Display, attribution, caching, history, derived-data, redistribution, and
  audit requirements.
- User, request, geography, and retention limits.
- Fees, reporting, termination, and fallback rights.

## Independent Security Review Scope

The reviewer should test:

- Identity lifecycle, invite acceptance, MFA, recovery, and session revocation.
- Cross-tenant read/write isolation for every private object and export.
- Role escalation, forged claims, object identifiers, and disabled accounts.
- OAuth state, nonce, PKCE, cookie, CSRF, redirect, and logout controls.
- Injection, request smuggling, file/path handling, secrets, logs, and error
  disclosure.
- Backup, restore, deletion, pseudonymization, audit integrity, and incident
  response.
- Cloud IAM, service accounts, database roles, network exposure, storage,
  monitoring, build/deploy provenance, and rollback.
- Rate limiting, abuse, dependency, and denial-of-service risks.

Required deliverable:

- Scope and methodology.
- Findings ranked by severity and exploitability.
- Reproduction evidence.
- Remediation verification.
- Explicit statement of untested areas.

## Release Rule

No external invitation may be sent until:

- Counsel supplies a written disposition.
- Data rights are documented for every customer-facing source.
- Critical and high independent-security findings are resolved.
- Joe explicitly approves the revised cost and invite-only staging release.

## Reference Basis

- SEC investment-adviser overview:
  https://www.sec.gov/about/offices/oia/oia_investman/rplaze-042012.pdf
- SEC information-provider request for comment:
  https://www.sec.gov/files/rules/other/2022/ia-6050.pdf
- Yahoo API terms:
  https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apitnc/index.html
- Nasdaq legal terms:
  https://www.nasdaq.com/legal
- SEC developer resources and fair access:
  https://www.sec.gov/about/developer-resources
  https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

