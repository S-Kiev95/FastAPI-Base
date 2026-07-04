"""
Modelo de Cuota — plan de pagos por póliza.
"""
import uuid
from datetime import date, datetime
from typing import Optional
from sqlmodel import Field, SQLModel, UniqueConstraint


class Installment(SQLModel, table=True):
    """Cuota de pago de una póliza."""
    __tablename__ = "cuota"
    __table_args__ = (
        UniqueConstraint("poliza_id", "numero_cuota", name="uq_cuota_poliza_numero"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    poliza_id: int = Field(foreign_key="poliza.id", index=True)

    numero_cuota: int
    monto: float
    fecha_vencimiento: date = Field(index=True)
    fecha_pago: Optional[date] = Field(default=None)
    pagada: bool = Field(default=False)
    metodo_pago: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InstallmentCreate(SQLModel):
    organization_id: Optional[uuid.UUID] = None
    poliza_id: int
    numero_cuota: int
    monto: float
    fecha_vencimiento: date
    fecha_pago: Optional[date] = None
    pagada: bool = False
    metodo_pago: Optional[str] = None


class InstallmentRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    poliza_id: int
    numero_cuota: int
    monto: float
    fecha_vencimiento: date
    fecha_pago: Optional[date]
    pagada: bool
    metodo_pago: Optional[str]
    created_at: datetime
    updated_at: datetime
    # Enriquecidos por la ruta (solo lectura)
    poliza_numero: Optional[str] = None
    cliente_nombre: Optional[str] = None


class InstallmentUpdate(SQLModel):
    monto: Optional[float] = None
    fecha_vencimiento: Optional[date] = None
    fecha_pago: Optional[date] = None
    pagada: Optional[bool] = None
    metodo_pago: Optional[str] = None
