"""Versioned tenant-aware SQLite persistence for Web Phase 3."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import uuid

from app.tenant_accounts import (
    TenantAccount,
    TenantRegistry,
    VALID_ROLES,
    VALID_STATUSES,
)


SCHEMA_VERSION = 2


MIGRATION_1 = """
CREATE TABLE tenants (
    tenant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
    created_at TEXT NOT NULL
);

CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL CHECK (provider = 'google'),
    subject TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE,
    created_at TEXT NOT NULL,
    UNIQUE (provider, subject)
);

CREATE TABLE memberships (
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'analyst', 'viewer')),
    status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, user_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE reports (
    tenant_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    title TEXT NOT NULL,
    markdown_path TEXT,
    html_path TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (tenant_id, report_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
);

CREATE TABLE watchlists (
    tenant_id TEXT NOT NULL,
    watchlist_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, watchlist_id),
    UNIQUE (tenant_id, name),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
);

CREATE TABLE watchlist_items (
    tenant_id TEXT NOT NULL,
    watchlist_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    category TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (tenant_id, watchlist_id, ticker),
    FOREIGN KEY (tenant_id, watchlist_id)
        REFERENCES watchlists (tenant_id, watchlist_id) ON DELETE CASCADE
);

CREATE TABLE portfolios (
    tenant_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    name TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, portfolio_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
);

CREATE TABLE positions (
    tenant_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    shares REAL NOT NULL CHECK (shares > 0),
    cost_basis REAL CHECK (cost_basis IS NULL OR cost_basis >= 0),
    PRIMARY KEY (tenant_id, portfolio_id, ticker),
    FOREIGN KEY (tenant_id, portfolio_id)
        REFERENCES portfolios (tenant_id, portfolio_id) ON DELETE CASCADE
);

CREATE TABLE research_tasks (
    tenant_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    role TEXT NOT NULL,
    subject TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('open', 'in_progress', 'awaiting_owner', 'closed')
    ),
    priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (tenant_id, task_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
);

CREATE TABLE paper_accounts (
    tenant_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    starting_cash REAL NOT NULL CHECK (starting_cash > 0),
    status TEXT NOT NULL CHECK (status IN ('active', 'closed')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, account_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
);

CREATE INDEX reports_by_tenant_date
    ON reports (tenant_id, generated_at DESC);
CREATE INDEX research_tasks_by_tenant_status
    ON research_tasks (tenant_id, status, priority);
"""


MIGRATION_2 = """
CREATE TABLE invitations (
    tenant_id TEXT NOT NULL,
    invitation_id TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'analyst', 'viewer')),
    token_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'accepted', 'revoked', 'expired')
    ),
    invited_by_user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    accepted_at TEXT,
    accepted_user_id TEXT,
    PRIMARY KEY (tenant_id, invitation_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by_user_id) REFERENCES users (user_id),
    FOREIGN KEY (accepted_user_id) REFERENCES users (user_id)
);

CREATE UNIQUE INDEX one_pending_invitation_per_email
    ON invitations (tenant_id, email)
    WHERE status = 'pending';

CREATE TABLE audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    actor_user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (actor_user_id) REFERENCES users (user_id)
);

CREATE INDEX audit_events_by_tenant_time
    ON audit_events (tenant_id, event_id DESC);

CREATE TRIGGER audit_events_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END;

CREATE TRIGGER audit_events_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END;
"""


class TenantStore:
    """Persist tenant data while requiring authorization for every resource."""

    def __init__(self, database_path, clock=None):
        self.database_path = Path(database_path)
        self.clock = clock or (
            lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
        )

    @contextmanager
    def connect(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            rows = connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
            applied = {int(row["version"]) for row in rows}
            unknown = [version for version in applied if version > SCHEMA_VERSION]
            if unknown:
                raise ValueError("Database schema is newer than this application")
            if 1 not in applied:
                connection.executescript(MIGRATION_1)
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (1, self.clock()),
                )
            if 2 not in applied:
                connection.executescript(MIGRATION_2)
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (2, self.clock()),
                )
        return SCHEMA_VERSION

    def schema_version(self):
        with self.connect() as connection:
            try:
                row = connection.execute(
                    "SELECT MAX(version) AS version FROM schema_migrations"
                ).fetchone()
            except sqlite3.OperationalError:
                return 0
        return int(row["version"] or 0)

    def provision_account(self, tenant_name, account):
        if not isinstance(account, TenantAccount):
            raise TypeError("account must be a TenantAccount")
        account.validate()
        if account.role != "owner":
            raise ValueError("Initial tenant account must be an owner")
        now = self.clock()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO tenants (tenant_id, name, status, created_at)
                VALUES (?, ?, 'active', ?)
                """,
                (account.tenant_id, str(tenant_name).strip(), now),
            )
            connection.execute(
                """
                INSERT INTO users (
                    user_id, provider, subject, email, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account.user_id,
                    account.provider,
                    account.subject,
                    account.email,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO memberships (
                    tenant_id, user_id, role, status, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account.tenant_id,
                    account.user_id,
                    account.role,
                    account.status,
                    now,
                ),
            )
        return account

    def resolve(self, provider, subject, verified_email):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT m.tenant_id, u.user_id, u.provider, u.subject, u.email,
                       m.role, m.status, t.status AS tenant_status
                FROM users u
                JOIN memberships m ON m.user_id = u.user_id
                JOIN tenants t ON t.tenant_id = m.tenant_id
                WHERE u.provider = ? AND u.subject = ?
                """,
                (str(provider).strip().lower(), str(subject).strip()),
            ).fetchone()
        if row is None:
            raise PermissionError("Identity is not invited")
        account = TenantAccount.from_record(dict(row))
        if row["tenant_status"] != "active":
            raise PermissionError("Tenant is disabled")
        if account.status != "active":
            raise PermissionError("Account is disabled")
        if account.email != str(verified_email).strip().lower():
            raise PermissionError("Verified email does not match invitation")
        return account

    def add_membership(self, actor, account):
        self._authorize(actor, "members:manage")
        if not isinstance(account, TenantAccount):
            raise TypeError("account must be a TenantAccount")
        account.validate()
        if account.tenant_id != actor.tenant_id:
            raise PermissionError("Cross-tenant membership denied")
        if account.role not in VALID_ROLES or account.status not in VALID_STATUSES:
            raise ValueError("Invalid membership")
        now = self.clock()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    user_id, provider, subject, email, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account.user_id,
                    account.provider,
                    account.subject,
                    account.email,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO memberships (
                    tenant_id, user_id, role, status, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account.tenant_id,
                    account.user_id,
                    account.role,
                    account.status,
                    now,
                ),
            )
        return account

    def invite_member(
        self,
        actor,
        email,
        role,
        expires_at,
        invitation_id=None,
        token=None,
    ):
        self._authorize(actor, "members:manage")
        role = str(role).strip().lower()
        if role not in {"admin", "analyst", "viewer"}:
            raise ValueError("Invitation role must be admin, analyst, or viewer")
        email = self._email(email)
        expires_at = str(expires_at).strip()
        if self._timestamp(expires_at) <= self._timestamp(self.clock()):
            raise ValueError("Invitation expiration must be in the future")
        invitation_id = invitation_id or self._id("invite")
        raw_token = token or secrets.token_urlsafe(32)
        token_hash = self._token_hash(raw_token)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO invitations (
                    tenant_id, invitation_id, email, role, token_hash, status,
                    invited_by_user_id, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                (
                    actor.tenant_id,
                    invitation_id,
                    email,
                    role,
                    token_hash,
                    actor.user_id,
                    self.clock(),
                    expires_at,
                ),
            )
            self._audit(
                connection,
                actor,
                "invitation.created",
                "invitation",
                invitation_id,
                {"email": email, "role": role, "expires_at": expires_at},
            )
        return {
            "invitation_id": invitation_id,
            "email": email,
            "role": role,
            "expires_at": expires_at,
            "token": raw_token,
        }

    def accept_invitation(
        self,
        token,
        provider,
        subject,
        verified_email,
        user_id=None,
    ):
        token_hash = self._token_hash(token)
        now = self.clock()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM invitations
                WHERE token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
            if row is None:
                raise PermissionError("Invitation is invalid")
            if row["status"] != "pending":
                raise PermissionError("Invitation is no longer active")
        if self._timestamp(row["expires_at"]) <= self._timestamp(now):
            with self.connect() as connection:
                connection.execute(
                    """
                    UPDATE invitations
                    SET status = 'expired'
                    WHERE tenant_id = ? AND invitation_id = ?
                    """,
                    (row["tenant_id"], row["invitation_id"]),
                )
            raise PermissionError("Invitation has expired")
        with self.connect() as connection:
            email = self._email(verified_email)
            if email != str(row["email"]).lower():
                raise PermissionError("Verified email does not match invitation")
            account = TenantAccount(
                tenant_id=row["tenant_id"],
                user_id=user_id or self._id("user"),
                provider=str(provider).strip().lower(),
                subject=str(subject).strip(),
                email=email,
                role=row["role"],
                status="active",
            )
            account.validate()
            connection.execute(
                """
                INSERT INTO users (
                    user_id, provider, subject, email, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account.user_id,
                    account.provider,
                    account.subject,
                    account.email,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO memberships (
                    tenant_id, user_id, role, status, created_at
                ) VALUES (?, ?, ?, 'active', ?)
                """,
                (
                    account.tenant_id,
                    account.user_id,
                    account.role,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE invitations
                SET status = 'accepted', accepted_at = ?, accepted_user_id = ?
                WHERE tenant_id = ? AND invitation_id = ?
                """,
                (
                    now,
                    account.user_id,
                    account.tenant_id,
                    row["invitation_id"],
                ),
            )
            self._audit(
                connection,
                account,
                "invitation.accepted",
                "membership",
                account.user_id,
                {"email": account.email, "role": account.role},
            )
        return account

    def revoke_invitation(self, actor, invitation_id):
        self._authorize(actor, "members:manage")
        with self.connect() as connection:
            changed = connection.execute(
                """
                UPDATE invitations
                SET status = 'revoked'
                WHERE tenant_id = ? AND invitation_id = ? AND status = 'pending'
                """,
                (actor.tenant_id, str(invitation_id)),
            ).rowcount
            if changed != 1:
                raise ValueError("Pending invitation not found")
            self._audit(
                connection,
                actor,
                "invitation.revoked",
                "invitation",
                str(invitation_id),
                {},
            )

    def list_invitations(self, actor):
        self._authorize(actor, "members:manage")
        rows = self._rows(
            """
            SELECT invitation_id, email, role, status, created_at, expires_at,
                   accepted_at
            FROM invitations
            WHERE tenant_id = ?
            ORDER BY created_at DESC, invitation_id
            """,
            (actor.tenant_id,),
        )
        return rows

    def list_members(self, actor):
        self._authorize(actor, "members:manage")
        return self._rows(
            """
            SELECT u.user_id, u.email, m.role, m.status, m.created_at
            FROM memberships m
            JOIN users u ON u.user_id = m.user_id
            WHERE m.tenant_id = ?
            ORDER BY u.email
            """,
            (actor.tenant_id,),
        )

    def change_member_role(self, actor, user_id, role):
        self._authorize(actor, "members:manage")
        role = str(role).strip().lower()
        if role not in VALID_ROLES:
            raise ValueError("Invalid tenant role")
        target = self._membership(actor.tenant_id, user_id)
        if target.role == "owner" or role == "owner":
            raise ValueError("Owner role changes require a separate transfer workflow")
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE memberships SET role = ?
                WHERE tenant_id = ? AND user_id = ?
                """,
                (role, actor.tenant_id, str(user_id)),
            )
            self._audit(
                connection,
                actor,
                "membership.role_changed",
                "membership",
                str(user_id),
                {"from": target.role, "to": role},
            )

    def set_member_status(self, actor, user_id, status):
        self._authorize(actor, "members:manage")
        status = str(status).strip().lower()
        if status not in VALID_STATUSES:
            raise ValueError("Invalid account status")
        target = self._membership(actor.tenant_id, user_id)
        if target.role == "owner":
            raise ValueError("Owner account cannot be disabled here")
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE memberships SET status = ?
                WHERE tenant_id = ? AND user_id = ?
                """,
                (status, actor.tenant_id, str(user_id)),
            )
            self._audit(
                connection,
                actor,
                "membership.status_changed",
                "membership",
                str(user_id),
                {"from": target.status, "to": status},
            )

    def list_audit_events(self, actor, limit=100):
        self._authorize(actor, "account:manage")
        limit = max(1, min(int(limit), 500))
        return self._rows(
            """
            SELECT event_id, actor_user_id, action, target_type, target_id,
                   occurred_at, details_json
            FROM audit_events
            WHERE tenant_id = ?
            ORDER BY event_id DESC
            LIMIT ?
            """,
            (actor.tenant_id, limit),
            json_fields=("details_json",),
        )

    def create_report(
        self,
        actor,
        title,
        generated_at,
        markdown_path=None,
        html_path=None,
        summary=None,
        report_id=None,
    ):
        self._authorize(actor, "research:write")
        report_id = report_id or self._id("report")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO reports (
                    tenant_id, report_id, generated_at, title,
                    markdown_path, html_path, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    actor.tenant_id,
                    report_id,
                    str(generated_at),
                    self._required(title, "report title"),
                    self._optional_path(markdown_path),
                    self._optional_path(html_path),
                    self._json(summary or {}),
                ),
            )
        return report_id

    def list_reports(self, actor):
        self._authorize(actor, "workspace:read")
        return self._rows(
            """
            SELECT report_id, generated_at, title, markdown_path, html_path,
                   summary_json
            FROM reports
            WHERE tenant_id = ?
            ORDER BY generated_at DESC
            """,
            (actor.tenant_id,),
            json_fields=("summary_json",),
        )

    def list_watchlists(self, actor):
        self._authorize(actor, "workspace:read")
        return self._rows(
            """
            SELECT watchlist_id, name, created_at
            FROM watchlists
            WHERE tenant_id = ?
            ORDER BY name, watchlist_id
            """,
            (actor.tenant_id,),
        )

    def create_watchlist(self, actor, name, watchlist_id=None):
        self._authorize(actor, "research:write")
        watchlist_id = watchlist_id or self._id("watchlist")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO watchlists (
                    tenant_id, watchlist_id, name, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    actor.tenant_id,
                    watchlist_id,
                    self._required(name, "watchlist name"),
                    self.clock(),
                ),
            )
        return watchlist_id

    def add_watchlist_item(
        self,
        actor,
        watchlist_id,
        ticker,
        category="Watchlist",
        notes="",
    ):
        self._authorize(actor, "research:write")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO watchlist_items (
                    tenant_id, watchlist_id, ticker, category, notes
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (tenant_id, watchlist_id, ticker)
                DO UPDATE SET category = excluded.category, notes = excluded.notes
                """,
                (
                    actor.tenant_id,
                    str(watchlist_id),
                    self._ticker(ticker),
                    self._required(category, "watchlist category"),
                    str(notes).strip(),
                ),
            )

    def list_watchlist_items(self, actor, watchlist_id):
        self._authorize(actor, "workspace:read")
        return self._rows(
            """
            SELECT ticker, category, notes
            FROM watchlist_items
            WHERE tenant_id = ? AND watchlist_id = ?
            ORDER BY ticker
            """,
            (actor.tenant_id, str(watchlist_id)),
        )

    def create_portfolio(
        self,
        actor,
        name,
        currency="USD",
        portfolio_id=None,
    ):
        self._authorize(actor, "portfolio:write")
        portfolio_id = portfolio_id or self._id("portfolio")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO portfolios (
                    tenant_id, portfolio_id, name, currency, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    actor.tenant_id,
                    portfolio_id,
                    self._required(name, "portfolio name"),
                    str(currency).strip().upper(),
                    self.clock(),
                ),
            )
        return portfolio_id

    def set_position(
        self,
        actor,
        portfolio_id,
        ticker,
        shares,
        cost_basis=None,
    ):
        self._authorize(actor, "portfolio:write")
        shares = float(shares)
        cost_basis = None if cost_basis is None else float(cost_basis)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO positions (
                    tenant_id, portfolio_id, ticker, shares, cost_basis
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (tenant_id, portfolio_id, ticker)
                DO UPDATE SET shares = excluded.shares,
                              cost_basis = excluded.cost_basis
                """,
                (
                    actor.tenant_id,
                    str(portfolio_id),
                    self._ticker(ticker),
                    shares,
                    cost_basis,
                ),
            )

    def list_positions(self, actor, portfolio_id):
        self._authorize(actor, "workspace:read")
        return self._rows(
            """
            SELECT ticker, shares, cost_basis
            FROM positions
            WHERE tenant_id = ? AND portfolio_id = ?
            ORDER BY ticker
            """,
            (actor.tenant_id, str(portfolio_id)),
        )

    def list_portfolios(self, actor):
        self._authorize(actor, "workspace:read")
        return self._rows(
            """
            SELECT portfolio_id, name, currency, created_at
            FROM portfolios
            WHERE tenant_id = ?
            ORDER BY name, portfolio_id
            """,
            (actor.tenant_id,),
        )

    def create_research_task(
        self,
        actor,
        role,
        subject,
        prompt,
        priority="medium",
        payload=None,
        task_id=None,
    ):
        self._authorize(actor, "research:write")
        task_id = task_id or self._id("task")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO research_tasks (
                    tenant_id, task_id, role, subject, prompt, status,
                    priority, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)
                """,
                (
                    actor.tenant_id,
                    task_id,
                    self._required(role, "research role"),
                    self._required(subject, "research subject"),
                    self._required(prompt, "research prompt"),
                    str(priority).strip().lower(),
                    self.clock(),
                    self._json(payload or {}),
                ),
            )
        return task_id

    def list_research_tasks(self, actor, status=None):
        self._authorize(actor, "workspace:read")
        query = """
            SELECT task_id, role, subject, prompt, status, priority,
                   created_at, payload_json
            FROM research_tasks
            WHERE tenant_id = ?
        """
        parameters = [actor.tenant_id]
        if status:
            query += " AND status = ?"
            parameters.append(str(status).strip().lower())
        query += " ORDER BY created_at DESC, task_id"
        return self._rows(
            query,
            tuple(parameters),
            json_fields=("payload_json",),
        )

    def create_paper_account(
        self,
        actor,
        name,
        starting_cash,
        account_id=None,
    ):
        self._authorize(actor, "portfolio:write")
        account_id = account_id or self._id("paper")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_accounts (
                    tenant_id, account_id, name, starting_cash,
                    status, created_at
                ) VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (
                    actor.tenant_id,
                    account_id,
                    self._required(name, "paper account name"),
                    float(starting_cash),
                    self.clock(),
                ),
            )
        return account_id

    def list_paper_accounts(self, actor):
        self._authorize(actor, "workspace:read")
        return self._rows(
            """
            SELECT account_id, name, starting_cash, status, created_at
            FROM paper_accounts
            WHERE tenant_id = ?
            ORDER BY created_at, account_id
            """,
            (actor.tenant_id,),
        )

    def workspace_summary(self, actor):
        self._authorize(actor, "workspace:read")
        with self.connect() as connection:
            tenant = connection.execute(
                """
                SELECT tenant_id, name, status, created_at
                FROM tenants
                WHERE tenant_id = ?
                """,
                (actor.tenant_id,),
            ).fetchone()
            counts = {}
            for table in (
                "reports",
                "watchlists",
                "portfolios",
                "research_tasks",
                "paper_accounts",
            ):
                row = connection.execute(
                    f"SELECT COUNT(*) AS total FROM {table} WHERE tenant_id = ?",
                    (actor.tenant_id,),
                ).fetchone()
                counts[table] = int(row["total"])
        return {
            "tenant": dict(tenant),
            "account": {
                "user_id": actor.user_id,
                "email": actor.email,
                "role": actor.role,
                "status": actor.status,
            },
            "counts": counts,
        }

    def _authorize(self, actor, permission):
        if not isinstance(actor, TenantAccount):
            raise TypeError("actor must be a TenantAccount")
        resolved = self.resolve(
            actor.provider,
            actor.subject,
            actor.email,
        )
        if resolved != actor:
            raise PermissionError("Account claims do not match active membership")
        return TenantRegistry.authorize(
            resolved,
            resolved.tenant_id,
            permission,
        )

    def _membership(self, tenant_id, user_id):
        with self.connect() as connection:
            return self._account_by_user(connection, tenant_id, user_id)

    @staticmethod
    def _account_by_user(connection, tenant_id, user_id):
        row = connection.execute(
            """
            SELECT m.tenant_id, u.user_id, u.provider, u.subject, u.email,
                   m.role, m.status
            FROM memberships m
            JOIN users u ON u.user_id = m.user_id
            WHERE m.tenant_id = ? AND u.user_id = ?
            """,
            (str(tenant_id), str(user_id)),
        ).fetchone()
        if row is None:
            raise ValueError("Tenant membership not found")
        return TenantAccount.from_record(dict(row))

    def _audit(
        self,
        connection,
        actor,
        action,
        target_type,
        target_id,
        details,
    ):
        connection.execute(
            """
            INSERT INTO audit_events (
                tenant_id, actor_user_id, action, target_type, target_id,
                occurred_at, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                actor.tenant_id,
                actor.user_id,
                str(action),
                str(target_type),
                str(target_id),
                self.clock(),
                self._json(details),
            ),
        )

    def _rows(self, query, parameters, json_fields=()):
        with self.connect() as connection:
            rows = [dict(row) for row in connection.execute(query, parameters)]
        for row in rows:
            for field in json_fields:
                row[field.removesuffix("_json")] = json.loads(row.pop(field))
        return rows

    @staticmethod
    def _required(value, label):
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{label} is required")
        return normalized

    @staticmethod
    def _ticker(value):
        ticker = str(value).strip().upper()
        if not ticker or len(ticker) > 12:
            raise ValueError("Valid ticker is required")
        return ticker

    @staticmethod
    def _email(value):
        email = str(value).strip().lower()
        if "@" not in email or len(email) > 254:
            raise ValueError("Valid email is required")
        return email

    @staticmethod
    def _timestamp(value):
        normalized = str(value).strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise ValueError("Timestamp must include a timezone")
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _token_hash(value):
        token = str(value).strip()
        if len(token) < 16:
            raise ValueError("Invitation token is invalid")
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _optional_path(value):
        if value is None:
            return None
        path = str(value).strip()
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("Stored report paths must be relative")
        return path

    @staticmethod
    def _json(value):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _id(prefix):
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
