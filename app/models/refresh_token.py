"""
Modelo RefreshToken para tokens de refresco persistidos en BD.
Permite revocación, listado de sesiones activas y logout.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    token_hash: str = Field(unique=True, index=True)  # SHA-256 del token raw
    user_id: int = Field(foreign_key="users.id", index=True)
    expires_at: datetime
    revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None  # Para identificar sesiones
