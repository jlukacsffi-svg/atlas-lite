# Atlas Final Staging Review

This runbook closes Web Phase 2 from the infrastructure side and leaves the
last owner-assisted gates explicit.

## Automated Review

Run the complete read-only review:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_final_staging_review.ps1 `
  -TelemetryHours 24
```

Expected result:

- `gcp_staging_status.ps1` confirms schedules remain paused and cleanup is
  still dry-run only.
- `gcp_staging_readiness.ps1` passes all automated security, storage,
  monitoring, and identity checks.
- `gcp_uptime_report.ps1` reports a clean regional telemetry window.
- The command ends with:

```text
[result] AUTOMATED FINAL REVIEW PASS - manual owner gates remain.
```

## Manual Owner Gates

These are the only remaining items before Web Phase 2 can be called complete:

1. Cross-device owner login
   Confirm that `jlukacsffi@gmail.com` can sign in from a second device and
   reach the live dashboard successfully.
2. Non-owner denial
   Confirm that a Google account outside the allowlist is denied dashboard
   access.
3. Final sign-off
   Confirm staging is acceptable from the perspectives of cost, security, and
   day-to-day operation.

The schedule decision is complete: daily and weekly recurring execution remain
paused. Resuming either schedule still requires a separate explicit approval.

## Record Identity Evidence

After observing a successful owner login from a second device:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_manual_validation.ps1 `
  -Action RecordCrossDevice `
  -ObservedAt "2026-06-11T12:00:00-07:00" `
  -ConfirmedExpectedResult
```

After observing a different Google account being denied:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\gcp_manual_validation.ps1 `
  -Action RecordNonOwnerDenial `
  -ObservedAt "2026-06-11T12:05:00-07:00" `
  -ConfirmedExpectedResult
```

Use the actual observation times. Optional `-Notes` may record a concise,
non-secret detail. The script only updates the local evidence file; it does not
change Google Cloud, OAuth, IAM, or schedule state.

## Artifact Registry Review

Validated on June 10, 2026:

- Repository size: 524.483 MB.
- Google Cloud includes the first 0.5 GB of Artifact Registry storage each
  month at no charge.
- The measured repository is approximately 24.5 MB above that allowance.
- At the published `$0.10/GB-month` storage rate, the estimated overage is
  approximately `$0.0025/month`.
- Eight Atlas images exist, all created June 7-8, 2026.
- The retention policy remains in dry-run mode, keeps the three newest images,
  and only observes images older than 14 days.
- No image is old enough to be a deletion candidate yet.
- Active deletion remains prohibited without a separate future review and
  explicit owner approval.

## Evidence To Record

Record the following when the manual gates are complete:

- Date and time of the cross-device owner login.
- Whether the non-owner denial test was blocked or denied as expected.
- The uptime report window used for sign-off.
- Whether schedules remain paused or were explicitly approved.
- Any follow-up issues discovered during the manual review.
