"""
Modelo de relación Aseguradora-Taller (M2M).
"""
import uuid
from datetime import date, datetime
from typing import Optional
from sqlmodel import Field, SQLModel, UniqueConstraint


class InsurerWorkshop(SQLModel, table=True):
    """Relación muchos-a-muchos entre aseguradoras y talleres acreditados."""
    __tablename__ = "aseguradora_taller"
    __table_args__ = (
        UniqueConstraint("aseguradora_id", "taller_id", name="uq_aseg_taller"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    aseguradora_id: int = Field(foreign_key="aseguradora.id", index=True)
    taller_id: int = Field(foreign_key="taller.id", index=True)

    zona: Optional[str] = Field(default=None)
    prioridad: int = Field(default=0)
    vigente_desde: Optional[date] = Field(default=None)
    vigente_hasta: Optional[date] = Field(default=None)
    activo: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class InsurerWorkshopCreate(SQLModel):
    organization_id: Optional[uuid.UUID] = None
    aseguradora_id: Optional[int] = None
    taller_id: int
    zona: Optional[str] = None
    prioridad: int = 0
    vigente_desde: Optional[date] = None
    vigente_hasta: Optional[date] = None
    activo: bool = True


class InsurerWorkshopRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    aseguradora_id: int
    taller_id: int
    zona: Optional[str]
    prioridad: int
    vigente_desde: Optional[date]
    vigente_hasta: Optional[date]
    activo: bool
    created_at: datetime


class InsurerWorkshopUpdate(SQLModel):
    zona: Optional[str] = None
    prioridad: Optional[int] = None
    vigente_desde: Optional[date] = None
    vigente_hasta: Optional[date] = None
    activo: Optional[bool] = None
