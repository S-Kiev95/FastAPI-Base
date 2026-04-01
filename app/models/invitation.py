"""
Modelo Invitation para invitaciones a organizaciones.
Token hasheado en BD, expira en 48h por defecto.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

from app.models.organization import MembershipRole


class Invitation(SQLModel, table=True):
    __tablename__ = "invitations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    email: str = Field(index=True)
    role: str = Field(default=MembershipRole.member)
    token_hash: str = Field(unique=True, index=True)
    invited_by: int = Field(foreign_key="users.id")
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Schemas ---

class InvitationCreate(SQLModel):
    email: str
    role: str = MembershipRole.member


class InvitationRead(SQLModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime
