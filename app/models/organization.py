"""
Modelos de Organization y Membership para multi-tenancy.
Cada tenant es una Organization. Los usuarios pertenecen a orgs via Membership.
"""
import uuid
import re
import unicodedata
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel, UniqueConstraint


class MembershipRole(str, Enum):
    """Roles jerárquicos dentro de una organización: owner > admin > member > viewer"""
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


# Orden jerárquico para comparaciones
ROLE_HIERARCHY = {
    MembershipRole.viewer: 0,
    MembershipRole.member: 1,
    MembershipRole.admin: 2,
    MembershipRole.owner: 3,
}


def role_gte(role: MembershipRole, minimum: MembershipRole) -> bool:
    """Verifica si un rol es igual o superior al mínimo requerido."""
    return ROLE_HIERARCHY[role] >= ROLE_HIERARCHY[minimum]


def slugify(text: str) -> str:
    """Genera un slug válido: lowercase, ASCII alfanumérico y guiones."""
    # Normalizar unicode y quitar diacríticos (é→e, ñ→n, etc.)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


# --- Modelos de tabla ---

class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    plan: str = Field(default="free")
    is_active: bool = Field(default=True)
    is_system: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Membership(SQLModel, table=True):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    role: str = Field(default=MembershipRole.member)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Schemas ---

class OrganizationCreate(SQLModel):
    name: str
    slug: Optional[str] = None
    plan: str = "free"


class OrganizationRead(SQLModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    is_system: bool
    created_at: datetime


class OrganizationUpdate(SQLModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None


class MembershipCreate(SQLModel):
    user_id: int
    role: str = MembershipRole.member


class MembershipRead(SQLModel):
    id: uuid.UUID
    user_id: int
    organization_id: uuid.UUID
    role: str
    is_active: bool
    created_at: datetime


class MembershipUpdate(SQLModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
