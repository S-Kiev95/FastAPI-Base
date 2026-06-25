"""
Modelo de Póliza — contratos de seguro.
"""
import uuid
from datetime import date, datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel, UniqueConstraint
from app.models.mixins import SoftDeleteMixin


class InsuranceType(str, Enum):
    auto = "auto"
    moto = "moto"
    hogar = "hogar"
    vida = "vida"
    comercio = "comercio"
    responsabilidad_civil = "responsabilidad_civil"
    otro = "otro"


class PolicyStatus(str, Enum):
    activa = "activa"
    vencida = "vencida"
    cancelada = "cancelada"
    suspendida = "suspendida"
    renovada = "renovada"


class Currency(str, Enum):
    UYU = "UYU"
    USD = "USD"


class Policy(SoftDeleteMixin, SQLModel, table=True):
    """Póliza de seguro, vincula cliente + vehículo + aseguradora."""
    __tablename__ = "poliza"
    __table_args__ = (
        UniqueConstraint("organization_id", "numero_poliza", name="uq_poliza_numero"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    vehiculo_id: Optional[int] = Field(default=None, foreign_key="vehiculo.id")
    aseguradora_id: int = Field(foreign_key="aseguradora.id", index=True)
    corredor_id: Optional[int] = Field(default=None, foreign_key="users.id")

    numero_poliza: str = Field(index=True)
    tipo_seguro: str = Field(default=InsuranceType.auto)
    vigente_desde: date
    vigente_hasta: date
    prima_total: Optional[float] = Field(default=None)
    moneda: str = Field(default=Currency.UYU)
    total_cuotas: int = Field(default=1)
    estado: str = Field(default=PolicyStatus.activa, index=True)
    notas: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyCreate(SQLModel):
    organization_id: uuid.UUID
    cliente_id: int
    vehiculo_id: Optional[int] = None
    aseguradora_id: int
    corredor_id: Optional[int] = None
    numero_poliza: str
    tipo_seguro: str = InsuranceType.auto
    vigente_desde: date
    vigente_hasta: date
    prima_total: Optional[float] = None
    moneda: str = Currency.UYU
    total_cuotas: int = 1
    estado: str = PolicyStatus.activa
    notas: Optional[str] = None


class PolicyRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    cliente_id: int
    vehiculo_id: Optional[int]
    aseguradora_id: int
    corredor_id: Optional[int]
    numero_poliza: str
    tipo_seguro: str
    vigente_desde: date
    vigente_hasta: date
    prima_total: Optional[float]
    moneda: str
    total_cuotas: int
    estado: str
    notas: Optional[str]
    created_at: datetime
    updated_at: datetime


class PolicyUpdate(SQLModel):
    vehiculo_id: Optional[int] = None
    aseguradora_id: Optional[int] = None
    corredor_id: Optional[int] = None
    numero_poliza: Optional[str] = None
    tipo_seguro: Optional[str] = None
    vigente_desde: Optional[date] = None
    vigente_hasta: Optional[date] = None
    prima_total: Optional[float] = None
    moneda: Optional[str] = None
    total_cuotas: Optional[int] = None
    estado: Optional[str] = None
    notas: Optional[str] = None
