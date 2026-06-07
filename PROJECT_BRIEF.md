# Atlas Capital Research / Atlas Lite Project Brief

## Current Project

Atlas Lite is the first working prototype of Atlas Capital Research.

The current goal is to build a reliable investment research and reporting system before expanding into more advanced autonomy.

Atlas Lite currently generates Morning Executive Brief markdown reports for a growth-focused stock watchlist. It retrieves market data, preserves a `yfinance` first / Yahoo Finance Chart API fallback flow, identifies movers, opportunities, risks, and writes reports locally.

Current local project folder:

```text
C:\Users\jluka\OneDrive\Documentos\Atlas-lite
```

Current GitHub repository:

```text
https://github.com/jlukacsffi-svg/atlas-lite
```

Current run command:

```powershell
py -3.12 main.py
```

Python 3.12 should be used. Python 3.14 is installed on the machine but caused compatibility issues with pandas and yfinance.

## Owner

Owner: Joe Lukacsffi

Joe is the final decision-maker. Atlas can research, score, summarize, and eventually recommend actions, but financial decisions require human approval until Joe explicitly authorizes a later autonomy level.

## Long-Term Vision

Atlas Capital Research is intended to become an autonomous AI investment research organization.

The long-term system should behave like a company that continuously gathers information, analyzes opportunities and risks, maintains context, and produces concise executive intelligence.

The eventual vision may include autonomous trading, but the project should reach that only through staged, tested, owner-approved phases.

Atlas should also become a modern web product. The long-term primary experience
should be a secure, responsive website with dashboards and graphics for market
research, scores, portfolios, risks, research workflows, and paper or approved
trading activity.

Users should eventually be able to create private Atlas accounts. Each account
must be isolated so a user can access only that user's own watchlists, reports,
portfolio information, alerts, research, and paper-trading records.

The web-platform plan is documented in `WEB_PLATFORM_PLAN.md`. Account creation
should progress from owner-only, to invite-only, to controlled beta, and only
then to public registration after security and operational reviews.

For the detailed staged development plan, read `ROADMAP.md`.

Atlas should evolve in stages:

1. Research and reporting.
2. Scoring and ranking.
3. Watchlist management.
4. Portfolio and risk monitoring.
5. Paper trading.
6. Limited autonomous trading under explicit owner-approved rules.
7. Broader autonomous capital management only after major legal, compliance, risk, and owner-approval work.

Web delivery evolves on a parallel track:

1. Read-only local owner dashboard.
2. Secure owner-only cloud deployment.
3. Invite-only multi-user workspaces.
4. Controlled customer beta.
5. Public self-service product after security and compliance readiness.

Do not add brokerage integrations, trading execution, or real capital movement unless Joe explicitly asks for that phase.

## Current Watchlist

Atlas Lite currently monitors:

- NVDA
- AMD
- AVGO
- TSM
- ARM
- MSFT
- AMZN
- GOOGL
- META
- PLTR
- LMT
- NOC
- RTX
- CRWD
- PANW
- SPY
- QQQ

## Atlas Security Universe v1

The goal is not to track every possible security. The goal is to build a high-quality universe where Atlas can learn, develop scoring models, and prove value.

Initial target size: roughly 100-150 securities.

Priority sectors:

- AI and infrastructure.
- Semiconductors.
- Cloud platforms.
- Defense and aerospace.
- Cybersecurity.
- Robotics and automation.
- Growth ETFs and sector benchmarks.

Early examples:

- AI / infrastructure: NVIDIA, AMD, Broadcom, Taiwan Semiconductor, Arm.
- Cloud / platforms: Microsoft, Amazon, Alphabet, Meta.
- Defense / aerospace: Lockheed Martin, RTX, Northrop Grumman, General Dynamics, Kratos, AeroVironment, Palantir.
- Cybersecurity: CrowdStrike, Palo Alto Networks, Fortinet, Zscaler.
- Robotics / automation: Rockwell Automation, ABB, Symbotic.
- ETFs and benchmarks: SPY, QQQ, VGT, AI, BOTZ, ROBO, CIBR.

## Watchlist Categories

Each security should eventually receive a status:

- Core Holdings: highest conviction, long-term positions.
- Watchlist: interesting, waiting for entry point.
- Emerging: new companies under investigation.
- Avoid: Atlas identified significant concerns.

## Atlas Scoring Engine v1

Each company should eventually receive a score from 0-100.

Proposed weighting:

- Growth Score: 40%.
- Quality Score: 20%.
- Moat Score: 15%.
- Momentum Score: 15%.
- Risk Score: 10%.

Scoring should start simple and become more sophisticated only when the data supports it.

## Future Daily Cycle

Possible future operating rhythm:

- 4:00 AM: Market Intelligence Agent scans news, earnings, and analyst changes.
- 5:00 AM: Research Agent updates company scores and watchlists.
- 6:00 AM: Risk Agent evaluates portfolio risk and concentration.
- 7:00 AM: CEO Agent generates an Executive Brief with opportunities, risks, watchlist changes, and recommended actions.

## Future Agent Organization

Atlas should eventually operate like a hierarchy, not a collection of disconnected scripts.

Possible future structure:

- Owner / Board Chairman: Joe.
- CEO Agent: coordinates the organization and manages priorities.
- CIO Agent: leads investment research and opportunity evaluation.
- CFO Agent: monitors portfolio performance and capital allocation.
- Chief Risk Officer Agent: challenges assumptions and evaluates risk.
- Chief Research Officer Agent: coordinates research standards and archives.
- Market Intelligence Team: monitors news, earnings, regulatory actions, contracts, M&A, insider transactions, and analyst changes.
- Sector Analyst Agents: specialize in AI, semiconductors, software, cybersecurity, aerospace and defense, healthcare, energy, financials, and consumer.
- Portfolio Analyst Agent: monitors holdings, allocation, gain/loss, attribution, and benchmarks.
- Reporting Agent: produces Morning Briefs, Weekly Briefs, Monthly Reviews, Opportunity Reports, and Risk Alerts.

Atlas Lite currently performs early Reporting Agent and Market Intelligence functions.

## Safety Rules

Near-term Atlas must not:

- Execute trades.
- Connect to brokerage accounts.
- Commit capital.
- Make financial decisions autonomously.
- Create legal obligations.
- Contact external customers.
- Represent itself as a licensed financial advisor.
- Store passwords, tokens, or API keys in the repository.
- Expose one user's private information to another user.
- Enable public registration before tenant isolation and account security are tested.

Future hosted Atlas must use managed authentication, server-side authorization,
tenant-aware data storage, encryption, managed secrets, audit logging, backups,
monitoring, and secure account recovery. Security is a release requirement.

Secrets should not be placed in prompts, source code, README files, AGENTS.md, screenshots, commits, or issue comments.

Future secrets should use environment variables or a local `.env` file that remains ignored by Git.

## Development Environment

Primary development machine:

- Windows HP laptop.
- Editor: Visual Studio Code.
- Python: Python 3.12 for Atlas Lite.

Git is installed at:

```text
C:\Program Files\Git\cmd\git.exe
```

In the current Codex terminal, plain `git` was not on PATH, but the full Git path works.

Verified Git state during setup:

```text
git version 2.54.0.windows.1
main tracks origin/main
origin https://github.com/jlukacsffi-svg/atlas-lite.git
```

Do not ask for or store GitHub passwords. GitHub authentication should remain handled by browser login, VS Code, Git Credential Manager, or GitHub OAuth.

## Development Philosophy

- Keep solutions simple.
- Preserve working functionality.
- Build incrementally.
- Prefer reliability over complexity.
- Preserve the `yfinance` plus Yahoo fallback market-data behavior.
- Avoid premature multi-agent frameworks.
- Every new component should provide measurable value.
- Test after meaningful changes with `py -3.12 main.py`.

## Near-Term Priorities

1. Add news headlines explaining major price moves.
2. Add an AI-generated executive summary.
3. Add HTML report output.
4. Add scheduled daily execution.
5. Add email delivery.

The highest-value next feature is a News Highlights section that answers: "Why did this stock move?"

## Recommended Next Task

Review the current Atlas Lite repository, then add a News Highlights section to the Morning Executive Brief.

Suggested requirements:

- Identify tickers with absolute percent change greater than 2%.
- Retrieve recent public news headlines for each major mover.
- Summarize 1-3 likely reasons for each move.
- Add News Highlights after Top Movers.
- Preserve the existing report format.
- Preserve the `yfinance` plus Yahoo fallback behavior.
- Do not add trading capability.
- Keep the project simple.
- Run `py -3.12 main.py` after changes.
