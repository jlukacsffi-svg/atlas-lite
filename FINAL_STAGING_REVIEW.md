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
3. Artifact Registry dry-run observation review
   Confirm the current dry-run retention policy is acceptable before any future
   deletion is considered.
4. Schedule decision
   Keep schedules paused, or explicitly approve recurring execution with the
   guarded resume script.
5. Final sign-off
   Confirm staging is acceptable from the perspectives of cost, security, and
   day-to-day operation.

## Evidence To Record

Record the following when the manual gates are complete:

- Date and time of the cross-device owner login.
- Whether the non-owner denial test was blocked or denied as expected.
- The uptime report window used for sign-off.
- Whether schedules remain paused or were explicitly approved.
- Any follow-up issues discovered during the manual review.
