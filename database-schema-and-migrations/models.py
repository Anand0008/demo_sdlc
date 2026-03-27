"""
Database models and schema definitions.
See Confluence > Database Schema and Migrations for the full ERD.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class User:
    id: str
    email: str
    hashed_password: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    failed_login_count: int = 0
    locked_until: datetime | None = None


@dataclass
class AuditLog:
    id: str
    user_id: str
    action: str            # e.g. "login", "logout", "failed_login"
    ip_address: str
    user_agent: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)
