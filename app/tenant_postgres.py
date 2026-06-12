"""PostgreSQL persistence adapter for the Atlas tenant repository."""

from contextlib import contextmanager
from datetime import datetime, timezone
import inspect

from app.tenant_store import SCHEMA_VERSION, TenantStore


MIGRATION_LOCK_ID = 73124561
EXPECTED_TABLES = {
    "tenants",
    "users",
    "memberships",
    "reports",
    "watchlists",
    "watchlist_items",
    "portfolios",
    "positions",
    "research_tasks",
    "paper_accounts",
    "invitations",
    "audit_events",
    "privacy_requests",
}

POSTGRES_MIGRATIONS = {
    1: (
        """
        CREATE TABLE tenants (
            tenant_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL CHECK (provider = 'google'),
            subject TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (provider, subject)
        )
        """,
        """
        CREATE TABLE memberships (
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                role IN ('owner', 'admin', 'analyst', 'viewer')
            ),
            status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, user_id),
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)
                REFERENCES users (user_id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE reports (
            tenant_id TEXT NOT NULL,
            report_id TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            title TEXT NOT NULL,
            markdown_path TEXT,
            html_path TEXT,
            summary_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (tenant_id, report_id),
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE watchlists (
            tenant_id TEXT NOT NULL,
            watchlist_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, watchlist_id),
            UNIQUE (tenant_id, name),
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE watchlist_items (
            tenant_id TEXT NOT NULL,
            watchlist_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            category TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (tenant_id, watchlist_id, ticker),
            FOREIGN KEY (tenant_id, watchlist_id)
                REFERENCES watchlists (tenant_id, watchlist_id)
                ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE portfolios (
            tenant_id TEXT NOT NULL,
            portfolio_id TEXT NOT NULL,
            name TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, portfolio_id),
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE positions (
            tenant_id TEXT NOT NULL,
            portfolio_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            shares DOUBLE PRECISION NOT NULL CHECK (shares > 0),
            cost_basis DOUBLE PRECISION CHECK (
                cost_basis IS NULL OR cost_basis >= 0
            ),
            PRIMARY KEY (tenant_id, portfolio_id, ticker),
            FOREIGN KEY (tenant_id, portfolio_id)
                REFERENCES portfolios (tenant_id, portfolio_id)
                ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE research_tasks (
            tenant_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            role TEXT NOT NULL,
            subject TEXT NOT NULL,
            prompt TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('open', 'in_progress', 'awaiting_owner', 'closed')
            ),
            priority TEXT NOT NULL CHECK (
                priority IN ('low', 'medium', 'high')
            ),
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (tenant_id, task_id),
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE paper_accounts (
            tenant_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            name TEXT NOT NULL,
            starting_cash DOUBLE PRECISION NOT NULL CHECK (starting_cash > 0),
            status TEXT NOT NULL CHECK (status IN ('active', 'closed')),
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, account_id),
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX reports_by_tenant_date
            ON reports (tenant_id, generated_at DESC)
        """,
        """
        CREATE INDEX research_tasks_by_tenant_status
            ON research_tasks (tenant_id, status, priority)
        """,
    ),
    2: (
        """
        CREATE TABLE invitations (
            tenant_id TEXT NOT NULL,
            invitation_id TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                role IN ('admin', 'analyst', 'viewer')
            ),
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
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE,
            FOREIGN KEY (invited_by_user_id) REFERENCES users (user_id),
            FOREIGN KEY (accepted_user_id) REFERENCES users (user_id)
        )
        """,
        """
        CREATE UNIQUE INDEX one_pending_invitation_per_email
            ON invitations (tenant_id, email)
            WHERE status = 'pending'
        """,
        """
        CREATE TABLE audit_events (
            event_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            actor_user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE,
            FOREIGN KEY (actor_user_id) REFERENCES users (user_id)
        )
        """,
        """
        CREATE INDEX audit_events_by_tenant_time
            ON audit_events (tenant_id, event_id DESC)
        """,
        """
        CREATE FUNCTION reject_audit_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $atlas$
        BEGIN
            RAISE EXCEPTION 'audit events are append-only';
        END;
        $atlas$
        """,
        """
        CREATE TRIGGER audit_events_no_update
        BEFORE UPDATE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation()
        """,
        """
        CREATE TRIGGER audit_events_no_delete
        BEFORE DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation()
        """,
    ),
    3: (
        """
        CREATE TABLE privacy_requests (
            tenant_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            request_type TEXT NOT NULL CHECK (
                request_type IN ('tenant_export', 'account_deletion')
            ),
            requested_by_user_id TEXT NOT NULL,
            target_user_id TEXT,
            status TEXT NOT NULL CHECK (
                status IN ('pending', 'completed', 'cancelled')
            ),
            created_at TEXT NOT NULL,
            completed_at TEXT,
            completed_by_user_id TEXT,
            result_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (tenant_id, request_id),
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (tenant_id) ON DELETE CASCADE,
            FOREIGN KEY (requested_by_user_id) REFERENCES users (user_id),
            FOREIGN KEY (target_user_id) REFERENCES users (user_id),
            FOREIGN KEY (completed_by_user_id) REFERENCES users (user_id)
        )
        """,
        """
        CREATE UNIQUE INDEX one_pending_deletion_per_user
            ON privacy_requests (tenant_id, target_user_id)
            WHERE request_type = 'account_deletion' AND status = 'pending'
        """,
        """
        CREATE INDEX privacy_requests_by_tenant_time
            ON privacy_requests (tenant_id, created_at DESC)
        """,
    ),
}


def validate_postgres_contract():
    """Return a fail-closed audit of the offline PostgreSQL schema contract."""
    statements = [
        statement.strip()
        for version in range(1, SCHEMA_VERSION + 1)
        for statement in POSTGRES_MIGRATIONS.get(version, ())
    ]
    sql = "\n".join(statements)
    repository_sources = "\n".join(
        inspect.getsource(member)
        for name, member in TenantStore.__dict__.items()
        if callable(member)
        and name not in {"connect", "migrate", "schema_version"}
    )
    checks = {
        "all_schema_versions_present": set(POSTGRES_MIGRATIONS)
        == set(range(1, SCHEMA_VERSION + 1)),
        "all_tables_present": all(
            f"CREATE TABLE {table}" in sql for table in EXPECTED_TABLES
        ),
        "sqlite_only_syntax_absent": not any(
            marker in sql
            for marker in ("AUTOINCREMENT", "COLLATE NOCASE", "PRAGMA")
        ),
        "composite_tenant_keys_present": all(
            fragment in sql
            for fragment in (
                "PRIMARY KEY (tenant_id, watchlist_id, ticker)",
                "FOREIGN KEY (tenant_id, watchlist_id)",
                "PRIMARY KEY (tenant_id, portfolio_id, ticker)",
                "FOREIGN KEY (tenant_id, portfolio_id)",
            )
        ),
        "append_only_audit_present": all(
            fragment in sql
            for fragment in (
                "reject_audit_event_mutation",
                "audit_events_no_update",
                "audit_events_no_delete",
            )
        ),
        "partial_uniqueness_present": all(
            fragment in sql
            for fragment in (
                "one_pending_invitation_per_email",
                "one_pending_deletion_per_user",
            )
        ),
        "identity_column_present": (
            "BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY" in sql
        ),
        "repository_queries_portable": not any(
            marker in repository_sources
            for marker in ("PRAGMA", "AUTOINCREMENT", "COLLATE NOCASE", "executescript")
        ),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "migration_versions": len(POSTGRES_MIGRATIONS),
        "statement_count": len(statements),
        "table_count": len(EXPECTED_TABLES),
        "checks": checks,
        "passed": all(checks.values()),
    }


def translate_qmark_parameters(query):
    """Translate SQLite-style placeholders while preserving quoted question marks."""
    result = []
    index = 0
    quote = None
    while index < len(query):
        character = query[index]
        if quote:
            result.append(character)
            if character == quote:
                if index + 1 < len(query) and query[index + 1] == quote:
                    result.append(query[index + 1])
                    index += 1
                else:
                    quote = None
        elif character in {"'", '"'}:
            quote = character
            result.append(character)
        elif character == "?":
            result.append("%s")
        else:
            result.append(character)
        index += 1
    return "".join(result)


class PostgresCursorAdapter:
    """Present DB-API cursor results as mapping rows."""

    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchone(self):
        return self._mapping(self.cursor.fetchone())

    def fetchall(self):
        return [self._mapping(row) for row in self.cursor.fetchall()]

    def __iter__(self):
        for row in self.cursor:
            yield self._mapping(row)

    def _mapping(self, row):
        if row is None or hasattr(row, "keys"):
            return row
        columns = [column[0] for column in self.cursor.description]
        return dict(zip(columns, row))


class PostgresConnectionAdapter:
    """Adapt a pg8000-style DB-API connection to the repository contract."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(translate_qmark_parameters(query), tuple(parameters))
        return PostgresCursorAdapter(cursor)


class PostgresTenantStore(TenantStore):
    """Reuse tenant repository behavior with native PostgreSQL migrations."""

    def __init__(self, connection_factory, clock=None):
        self.connection_factory = connection_factory
        self.clock = clock or (
            lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
        )

    @contextmanager
    def connect(self):
        raw_connection = self.connection_factory()
        connection = PostgresConnectionAdapter(raw_connection)
        try:
            yield connection
            raw_connection.commit()
        except Exception:
            raw_connection.rollback()
            raise
        finally:
            raw_connection.close()

    def migrate(self):
        with self.connect() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(?)",
                (MIGRATION_LOCK_ID,),
            )
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
            if any(version > SCHEMA_VERSION for version in applied):
                raise ValueError("Database schema is newer than this application")
            for version in range(1, SCHEMA_VERSION + 1):
                if version in applied:
                    continue
                for statement in POSTGRES_MIGRATIONS[version]:
                    connection.execute(statement)
                connection.execute(
                    """
                    INSERT INTO schema_migrations (version, applied_at)
                    VALUES (?, ?)
                    """,
                    (version, self.clock()),
                )
        return SCHEMA_VERSION

    def schema_version(self):
        with self.connect() as connection:
            table = connection.execute(
                "SELECT to_regclass('public.schema_migrations') AS table_name"
            ).fetchone()
            if table["table_name"] is None:
                return 0
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
        return int(row["version"])


class CloudSqlPostgresConnectionFactory:
    """Create IAM-authenticated pg8000 connections through Cloud SQL."""

    def __init__(
        self,
        instance_connection_name,
        database,
        user,
        private_ip=False,
    ):
        self.instance_connection_name = str(instance_connection_name).strip()
        self.database = str(database).strip()
        self.user = str(user).strip()
        self.private_ip = bool(private_ip)
        if not all(
            (self.instance_connection_name, self.database, self.user)
        ):
            raise ValueError("Cloud SQL instance, database, and user are required")
        self._connector = None

    def __call__(self):
        try:
            from google.cloud.sql.connector import Connector, IPTypes
        except ImportError as exc:
            raise RuntimeError(
                "Install requirements-postgres.txt before using Cloud SQL"
            ) from exc
        if self._connector is None:
            self._connector = Connector()
        ip_type = IPTypes.PRIVATE if self.private_ip else IPTypes.PUBLIC
        return self._connector.connect(
            self.instance_connection_name,
            "pg8000",
            user=self.user,
            db=self.database,
            enable_iam_auth=True,
            ip_type=ip_type,
        )

    def close(self):
        if self._connector is not None:
            self._connector.close()
            self._connector = None
