"""
Modelo de Cliente — personas aseguradas.
"""
import uuid
from datetime import date, datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from app.models.mixins import SoftDeleteMixin


class Client(SoftDeleteMixin, SQLModel, table=True):
    """Cliente de la correduría de seguros."""
    __tablename__ = "cliente"

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)

    numero_cliente: Optional[str] = Field(default=None)
    nombre: str = Field(index=True)
    apellido: str = Field(index=True)
    documento_identidad: Optional[str] = Field(default=None, index=True)
    telefono: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    direccion: Optional[str] = Field(default=None)
    fecha_nacimiento: Optional[date] = Field(default=None)
    notas: Optional[str] = Field(default=None)
    activo: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ClientCreate(SQLModel):
    organization_id: uuid.UUID
    numero_cliente: Optional[str] = None
    nombre: str
    apellido: str
    documento_identidad: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    notas: Optional[str] = None
    activo: bool = True


class ClientRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    numero_cliente: Optional[str]
    nombre: str
    apellido: str
    documento_identidad: Optional[str]
    telefono: Optional[str]
    email: Optional[str]
    direccion: Optional[str]
    fecha_nacimiento: Optional[date]
    notas: Optional[str]
    activo: bool
    created_at: datetime
    updated_at: datetime


class ClientUpdate(SQLModel):
    numero_cliente: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    documento_identidad: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None
