"""
Modelo de Vehículo — vehículos asegurados.
"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel, UniqueConstraint
from app.models.mixins import SoftDeleteMixin


class VehicleType(str, Enum):
    auto = "auto"
    moto = "moto"
    camion = "camion"
    utilitario = "utilitario"
    otro = "otro"


class Vehicle(SoftDeleteMixin, SQLModel, table=True):
    """Vehículo asegurado, pertenece a un cliente."""
    __tablename__ = "vehiculo"
    __table_args__ = (
        UniqueConstraint("organization_id", "matricula", name="uq_vehiculo_matricula"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)

    marca: str
    modelo: Optional[str] = Field(default=None)
    anio: Optional[int] = Field(default=None)
    matricula: str = Field(index=True)
    tipo: str = Field(default=VehicleType.auto)
    color: Optional[str] = Field(default=None)
    numero_motor: Optional[str] = Field(default=None)
    numero_chasis: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VehicleCreate(SQLModel):
    organization_id: uuid.UUID
    cliente_id: int
    marca: str
    modelo: Optional[str] = None
    anio: Optional[int] = None
    matricula: str
    tipo: str = VehicleType.auto
    color: Optional[str] = None
    numero_motor: Optional[str] = None
    numero_chasis: Optional[str] = None


class VehicleRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    cliente_id: int
    marca: str
    modelo: Optional[str]
    anio: Optional[int]
    matricula: str
    tipo: str
    color: Optional[str]
    numero_motor: Optional[str]
    numero_chasis: Optional[str]
    created_at: datetime
    updated_at: datetime


class VehicleUpdate(SQLModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    matricula: Optional[str] = None
    tipo: Optional[str] = None
    color: Optional[str] = None
    numero_motor: Optional[str] = None
    numero_chasis: Optional[str] = None
