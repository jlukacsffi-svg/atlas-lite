"""Tenant-aware identity, role, and workspace boundaries for Web Phase 3."""

from dataclasses import dataclass
import json
from pathlib import Path
import re


REGISTRY_VERSION = 1
VALID_ROLES = {"owner", "admin", "analyst", "viewer"}
VALID_STATUSES = {"active", "disabled"}
TENANT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
USER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
ROLE_PERMISSIONS = {
    "owner": {
        "workspace:read",
        "research:write",
        "portfolio:write",
        "members:manage",
        "account:manage",
    },
    "admin": {
        "workspace:read",
        "research:write",
        "portfolio:write",
        "members:manage",
    },
    "analyst": {
        "workspace:read",
        "research:write",
    },
    "viewer": {
        "workspace:read",
    },
}


class TenantAccessError(PermissionError):
    """Raised when an identity cannot access a requested tenant resource."""


@dataclass(frozen=True)
class TenantAccount:
    tenant_id: str
    user_id: str
    provider: str
    subject: str
    email: str
    role: str
    status: str = "active"

    @classmethod
    def from_record(cls, record):
        required = {
            "tenant_id",
            "user_id",
            "provider",
            "subject",
            "email",
            "role",
        }
        if not isinstance(record, dict) or not required.issubset(record):
            raise ValueError("Tenant account record is incomplete")
        account = cls(
            tenant_id=str(record["tenant_id"]).strip().lower(),
            user_id=str(record["user_id"]).strip().lower(),
            provider=str(record["provider"]).strip().lower(),
            subject=str(record["subject"]).strip(),
            email=str(record["email"]).strip().lower(),
            role=str(record["role"]).strip().lower(),
            status=str(record.get("status", "active")).strip().lower(),
        )
        account.validate()
        return account

    def validate(self):
        if not TENANT_ID_PATTERN.fullmatch(self.tenant_id):
            raise ValueError("Invalid tenant_id")
        if not USER_ID_PATTERN.fullmatch(self.user_id):
            raise ValueError("Invalid user_id")
        if self.provider not in {"google"}:
            raise ValueError("Unsupported identity provider")
        if not self.subject:
            raise ValueError("Identity subject is required")
        if "@" not in self.email:
            raise ValueError("Valid account email is required")
        if self.role not in VALID_ROLES:
            raise ValueError("Invalid tenant role")
        if self.status not in VALID_STATUSES:
            raise ValueError("Invalid account status")

    def permits(self, permission):
        return permission in ROLE_PERMISSIONS[self.role]


class TenantRegistry:
    """Read and authorize a fail-closed tenant account registry."""

    def __init__(self, registry_file):
        self.registry_file = Path(registry_file)
        self._accounts = self._load()
        self._by_identity = {
            (account.provider, account.subject): account
            for account in self._accounts
        }

    def _load(self):
        try:
            payload = json.loads(self.registry_file.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError("Tenant registry is required") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Tenant registry is invalid JSON") from exc
        if payload.get("schema_version") != REGISTRY_VERSION:
            raise ValueError("Unsupported tenant registry schema")
        records = payload.get("accounts")
        if not isinstance(records, list):
            raise ValueError("Tenant registry accounts must be a list")

        accounts = [TenantAccount.from_record(record) for record in records]
        identities = set()
        memberships = set()
        for account in accounts:
            identity = (account.provider, account.subject)
            membership = (account.tenant_id, account.user_id)
            if identity in identities:
                raise ValueError("Duplicate external identity")
            if membership in memberships:
                raise ValueError("Duplicate tenant membership")
            identities.add(identity)
            memberships.add(membership)
        return tuple(accounts)

    def resolve(self, provider, subject, verified_email):
        identity = (str(provider).strip().lower(), str(subject).strip())
        account = self._by_identity.get(identity)
        if account is None:
            raise TenantAccessError("Identity is not invited")
        if account.status != "active":
            raise TenantAccessError("Account is disabled")
        if account.email != str(verified_email).strip().lower():
            raise TenantAccessError("Verified email does not match invitation")
        return account

    @staticmethod
    def authorize(account, tenant_id, permission):
        requested_tenant = str(tenant_id).strip().lower()
        if account.tenant_id != requested_tenant:
            raise TenantAccessError("Cross-tenant access denied")
        if not account.permits(permission):
            raise TenantAccessError("Role does not grant permission")
        return account


class TenantWorkspacePaths:
    """Construct private paths inside one tenant's dedicated workspace."""

    def __init__(self, data_root, tenant_id):
        tenant_id = str(tenant_id).strip().lower()
        if not TENANT_ID_PATTERN.fullmatch(tenant_id):
            raise ValueError("Invalid tenant_id")
        self.data_root = Path(data_root).resolve()
        self.tenant_id = tenant_id
        self.root = (self.data_root / "tenants" / tenant_id).resolve()
        expected_parent = (self.data_root / "tenants").resolve()
        if self.root.parent != expected_parent:
            raise ValueError("Unsafe tenant workspace path")

    @property
    def research_archive(self):
        return self.root / "research_archive"

    @property
    def research_tasks(self):
        return self.root / "research_tasks"

    @property
    def paper_trading(self):
        return self.root / "paper_trading"

    @property
    def portfolio_history(self):
        return self.root / "portfolio_history"

    @property
    def reports(self):
        return self.root / "reports"

