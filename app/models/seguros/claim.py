"""
Modelo de Siniestro — reclamos / siniestros.
"""
import uuid
from datetime import date, datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel, UniqueConstraint
from app.models.mixins import SoftDeleteMixin


class DamageType(str, Enum):
    dano_propio = "dano_propio"
    dano_tercero = "dano_tercero"
    robo_total = "robo_total"
    robo_parcial = "robo_parcial"
    incendio = "incendio"
    otro = "otro"


class ClaimStatus(str, Enum):
    abierto = "abierto"
    en_tramite = "en_tramite"
    liquidado = "liquidado"
    rechazado = "rechazado"
    cerrado = "cerrado"


class Claim(SoftDeleteMixin, SQLModel, table=True):
    """Siniestro / reclamo asociado a una póliza."""
    __tablename__ = "siniestro"
    __table_args__ = (
        UniqueConstraint("organization_id", "numero_siniestro", name="uq_siniestro_numero"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    poliza_id: int = Field(foreign_key="poliza.id", index=True)
    aseguradora_id: int = Field(foreign_key="aseguradora.id", index=True)

    numero_siniestro: str = Field(index=True)
    fecha_ocurrencia: Optional[date] = Field(default=None)
    fecha_denuncia: Optional[date] = Field(default=None)
    tipo_dano: str = Field(default=DamageType.dano_propio)
    estado: str = Field(default=ClaimStatus.abierto, index=True)
    monto_reclamado: Optional[float] = Field(default=None)
    monto_liquidado: Optional[float] = Field(default=None)
    descripcion: Optional[str] = Field(default=None)
    observaciones: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ClaimCreate(SQLModel):
    organization_id: Optional[uuid.UUID] = None
    poliza_id: int
    aseguradora_id: int
    numero_siniestro: str
    fecha_ocurrencia: Optional[date] = None
    fecha_denuncia: Optional[date] = None
    tipo_dano: str = DamageType.dano_propio
    estado: str = ClaimStatus.abierto
    monto_reclamado: Optional[float] = None
    monto_liquidado: Optional[float] = None
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None


class ClaimRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    poliza_id: int
    aseguradora_id: int
    numero_siniestro: str
    fecha_ocurrencia: Optional[date]
    fecha_denuncia: Optional[date]
    tipo_dano: str
    estado: str
    monto_reclamado: Optional[float]
    monto_liquidado: Optional[float]
    descripcion: Optional[str]
    observaciones: Optional[str]
    created_at: datetime
    updated_at: datetime
    # Enriquecidos por la ruta (solo lectura)
    poliza_numero: Optional[str] = None
    cliente_nombre: Optional[str] = None
    aseguradora_nombre: Optional[str] = None


class ClaimUpdate(SQLModel):
    fecha_ocurrencia: Optional[date] = None
    fecha_denuncia: Optional[date] = None
    tipo_dano: Optional[str] = None
    estado: Optional[str] = None
    monto_reclamado: Optional[float] = None
    monto_liquidado: Optional[float] = None
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None
