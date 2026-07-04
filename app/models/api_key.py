"""
Modelo de API Key para autenticación M2M (machine-to-machine).
Las keys se almacenan hasheadas (SHA-256) — el valor raw solo se muestra una vez.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class ApiKey(SQLModel, table=True):
    """API Key persistida. Solo se almacena el hash, no el valor raw."""
    __tablename__ = "api_keys"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    key_prefix: str = Field(index=True)           # Primeros 8 chars (para identificación)
    key_hash: str = Field(unique=True, index=True) # SHA-256 del key completo
    user_id: int = Field(foreign_key="users.id", index=True)
    organization_id: Optional[str] = Field(default=None, index=True)
    scopes: Optional[str] = Field(default=None)    # Comma-separated: "read:users,write:media"
    expires_at: Optional[datetime] = Field(default=None)
    last_used_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Schemas ---

class ApiKeyCreate(SQLModel):
    """Schema para crear una API key."""
    name: str
    scopes: Optional[str] = None       # "read:users,write:media" o None (full access)
    expires_in_days: Optional[int] = None  # None = no expira


class ApiKeyRead(SQLModel):
    """Schema de lectura (nunca expone key_hash)."""
    id: uuid.UUID
    name: str
    key_prefix: str
    user_id: int
    organization_id: Optional[str]
    scopes: Optional[str]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool
    created_at: datetime


class ApiKeyCreateResponse(SQLModel):
    """Respuesta al crear — incluye el raw key (se muestra una sola vez)."""
    id: uuid.UUID
    name: str
    key_prefix: str
    raw_key: str           # Solo se muestra aquí, nunca más
    scopes: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime
    message: str = "Guarda esta API key — no se puede recuperar después."
