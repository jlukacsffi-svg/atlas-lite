# Atlas Redesign Local Preview

Run the integrated read-only redesign from the repository root:

```powershell
py -3.12 run_redesign.py
```

Open `http://127.0.0.1:8771/`.

Today, Ideas, Research, and Portfolio use real Atlas records from the latest
completed research snapshot and paper ledger. Their status banner identifies
the source timestamp and whether the snapshot is stale. Activity, Reports,
Alerts, and Settings remain prototype or partially connected pages and say so
in their status banner.

If either page API is unavailable, the browser retains the design fixtures only
as a clearly labeled development fallback. The server accepts no POST request
and has no brokerage connection.
