# Atlas Lite Handoff

Last updated: 2026-06-01

## Current Roadmap Position

Atlas Lite is at the end of Stage 1: Reliable Daily Briefing.

Stage 1 completed:

- Reliable market data retrieval.
- yfinance-first flow with Yahoo Finance fallback.
- yfinance circuit breaker after repeated failures.
- Markdown Morning Executive Brief.
- Rule-based Executive Summary.
- News Highlights for major movers.
- HTML report output.
- Windows scheduled execution scripts.
- Optional SMTP email delivery support.
- Local `.env` loading for ignored, machine-local email settings.

## Current Blocker

Email delivery is implemented but Gmail SMTP authentication is not yet passing.

The latest live email test:

- Loaded `.env` successfully.
- Confirmed email delivery was enabled.
- Confirmed SMTP host/user/recipient were present.
- Confirmed password was present and normalized to 16 characters.
- Generated Markdown and HTML reports successfully.
- Reached Gmail SMTP.
- Failed at login with Gmail error `535 5.7.8 Username and Password not accepted`.

Most likely causes:

- The Google app password was created for the wrong Google account.
- The regular account password was used instead of a Google app password.
- The app password needs to be regenerated.
- The `.env` file has a mismatch between sender/user and the account that generated the app password.

Dedicated sender account:

```text
atlas.capital.reports@gmail.com
```

Recipient:

```text
jlukacsffi@gmail.com
```

## Important Security Note

Do not paste email passwords or app passwords into chat.

The local `.env` file is ignored by Git and should stay local only.

Never commit `.env`.

## Next Session First Step

1. Sign into Google as `atlas.capital.reports@gmail.com`.
2. Go to Google App Passwords.
3. Generate a new app password for `Atlas Lite SMTP`.
4. Update the local `.env` file:

```text
ATLAS_SMTP_PASSWORD=the16characterapppassword
```

5. Verify these `.env` values:

```text
ATLAS_EMAIL_ENABLED=true
ATLAS_SMTP_HOST=smtp.gmail.com
ATLAS_SMTP_PORT=587
ATLAS_SMTP_USER=atlas.capital.reports@gmail.com
ATLAS_EMAIL_FROM=atlas.capital.reports@gmail.com
ATLAS_EMAIL_TO=jlukacsffi@gmail.com
ATLAS_SMTP_USE_STARTTLS=true
ATLAS_SMTP_USE_SSL=false
```

6. Rerun:

```powershell
& "C:\Users\jluka\AppData\Local\Programs\Python\Python312\python.exe" main.py
```

Expected success output:

```text
[ok] Report email sent.
```

## Useful Files

- `ROADMAP.md`: long-term Atlas development roadmap.
- `PROJECT_BRIEF.md`: project vision and constraints.
- `AGENTS.md`: Codex working instructions.
- `app/email_delivery.py`: optional email delivery and `.env` loading.
- `main.py`: daily report execution flow.
- `scripts/run_atlas_daily.ps1`: scheduled runner.
- `scripts/setup_windows_scheduled_task.ps1`: Windows Scheduled Task setup.

