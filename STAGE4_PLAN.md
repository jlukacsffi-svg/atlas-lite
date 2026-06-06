# Stage 4 Plan: Multi-Agent Research Organization

Stage 4 should turn Atlas from a strong reporting system into a coordinated research organization.

Do not build a large agent framework immediately. The first implementation should be a lightweight task queue and role-based research workflow that uses the existing reports, scoring, archive, weekly summaries, and portfolio intelligence.

## Objective

Atlas should be able to assign research work, track open questions, challenge assumptions, and organize recommendations without trading or contacting external parties.

## Safety Boundaries

Atlas must not:

- Execute trades.
- Connect to brokerage accounts.
- Make financial commitments.
- Contact external customers.
- Represent itself as a licensed financial advisor.
- Modify watchlist categories or portfolio assumptions without explicit owner review.

Stage 4 remains research-only.

## Initial Roles

### CEO Agent

Purpose:

Prioritize the research agenda.

Responsibilities:

- Review daily and weekly report outputs.
- Select the most important research tasks.
- Escalate urgent risks.
- Summarize the current agenda for Joe.

### CIO Agent

Purpose:

Review investment opportunities and thesis quality.

Responsibilities:

- Review high Atlas Priority Ranking names.
- Maintain thesis questions.
- Recommend watchlist review prompts.
- Compare opportunities across sectors.

### CRO Agent

Purpose:

Challenge risk assumptions.

Responsibilities:

- Review downside movers.
- Review portfolio concentration when configured.
- Review weak sector trends.
- Flag thesis risks and data-quality gaps.

### Reporting Agent

Purpose:

Convert research outputs into concise briefs.

Responsibilities:

- Produce daily and weekly executive summaries.
- Track unresolved research prompts.
- Keep reports concise and owner-focused.

## First Implementation

Build a local research task queue before building autonomous agents.

Suggested local file:

```text
research_tasks/tasks.json
```

The folder should be ignored by Git because tasks may eventually reference personal holdings or owner-specific priorities.

Each task should include:

- Task ID
- Created timestamp
- Source report
- Suggested owner role: CEO, CIO, CRO, or Reporting
- Ticker or sector
- Priority
- Status: open, in_progress, closed
- Prompt
- Notes

## First Software Milestone

Add a task generator that reads daily and weekly signals and creates research-task suggestions.

Initial task sources:

- Weekly Research Action Prompts
- Portfolio risk alerts
- Watchlist Change Recommendations
- Large downside moves
- Missing market or portfolio data
- Recurring score leaders

Atlas should not execute tasks automatically in the first version. It should create a reviewable task list.

## Success Test

Stage 4 foundation is successful when Atlas can answer:

- What should we research next?
- Why is this task important?
- Which role should review it?
- What report or signal created the task?
- Is the task still open?

## Recommended Next Build Step

Create a local `research_tasks/` system with:

- `app/research_tasks.py`
- `research_tasks.py` command-line entry point
- ignored local `research_tasks/tasks.json`
- tests for task creation, deduplication, and status updates

This should be done before implementing long-running autonomous agents.
