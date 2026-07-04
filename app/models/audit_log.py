"""
Modelo de Audit Log — registro inmutable de acciones sobre recursos.
Append-only: no se actualiza ni se elimina.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class AuditLog(SQLModel, table=True):
    """Registro de auditoría. Inmutable (append-only)."""
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True, foreign_key="users.id")
    organization_id: Optional[str] = Field(default=None, index=True)
    action: str = Field(index=True)           # create, update, delete, restore, login, export
    resource_type: str = Field(index=True)     # "users", "media", "organizations", etc.
    resource_id: Optional[str] = Field(default=None, index=True)
    changes: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class AuditLogRead(SQLModel):
    """Schema de lectura para audit logs."""
    id: uuid.UUID
    user_id: Optional[int]
    organization_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    changes: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
