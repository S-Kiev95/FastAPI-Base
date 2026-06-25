"""
Modelo de Taller — talleres mecánicos acreditados.
"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel
from app.models.mixins import SoftDeleteMixin


class WorkshopSpecialty(str, Enum):
    general = "general"
    chapa_pintura = "chapa_pintura"
    mecanica = "mecanica"
    electricidad = "electricidad"
    cristales = "cristales"
    multimarca = "multimarca"
    oficial = "oficial"


class Workshop(SoftDeleteMixin, SQLModel, table=True):
    """Taller mecánico acreditado por aseguradoras."""
    __tablename__ = "taller"

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)

    nombre: str = Field(index=True)
    direccion: Optional[str] = Field(default=None)
    departamento: str = Field(index=True)
    ciudad: Optional[str] = Field(default=None)
    telefono: Optional[str] = Field(default=None)
    telefono2: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    especialidad: str = Field(default=WorkshopSpecialty.general)
    marcas_atendidas: Optional[str] = Field(default=None)  # Comma-separated para SQLite compat
    horario: Optional[str] = Field(default=None)
    activo: bool = Field(default=True)
    notas: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkshopCreate(SQLModel):
    organization_id: uuid.UUID
    nombre: str
    direccion: Optional[str] = None
    departamento: str
    ciudad: Optional[str] = None
    telefono: Optional[str] = None
    telefono2: Optional[str] = None
    email: Optional[str] = None
    especialidad: str = WorkshopSpecialty.general
    marcas_atendidas: Optional[str] = None
    horario: Optional[str] = None
    activo: bool = True
    notas: Optional[str] = None


class WorkshopRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    nombre: str
    direccion: Optional[str]
    departamento: str
    ciudad: Optional[str]
    telefono: Optional[str]
    telefono2: Optional[str]
    email: Optional[str]
    especialidad: str
    marcas_atendidas: Optional[str]
    horario: Optional[str]
    activo: bool
    notas: Optional[str]
    created_at: datetime
    updated_at: datetime


class WorkshopUpdate(SQLModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    departamento: Optional[str] = None
    ciudad: Optional[str] = None
    telefono: Optional[str] = None
    telefono2: Optional[str] = None
    email: Optional[str] = None
    especialidad: Optional[str] = None
    marcas_atendidas: Optional[str] = None
    horario: Optional[str] = None
    activo: Optional[bool] = None
    notas: Optional[str] = None
