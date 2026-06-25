"""
Modelo de Aseguradora — compañías de seguros.
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import Field, SQLModel, UniqueConstraint, Column
from sqlalchemy import JSON
from app.models.mixins import SoftDeleteMixin


class Insurer(SoftDeleteMixin, SQLModel, table=True):
    """Compañía aseguradora."""
    __tablename__ = "aseguradora"
    __table_args__ = (
        UniqueConstraint("organization_id", "nombre", name="uq_aseguradora_nombre"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)

    nombre: str = Field(index=True)
    telefono: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    direccion: Optional[str] = Field(default=None)
    contactos: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    activa: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InsurerCreate(SQLModel):
    organization_id: uuid.UUID
    nombre: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    contactos: List[Dict[str, Any]] = []
    activa: bool = True


class InsurerRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    nombre: str
    telefono: Optional[str]
    email: Optional[str]
    direccion: Optional[str]
    contactos: List[Dict[str, Any]]
    activa: bool
    created_at: datetime
    updated_at: datetime


class InsurerUpdate(SQLModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    contactos: Optional[List[Dict[str, Any]]] = None
    activa: Optional[bool] = None
