"""
Modelo de Documento de Siniestro — checklist de documentos requeridos.
"""
import uuid
from datetime import date, datetime
from typing import Optional
from sqlmodel import Field, SQLModel, UniqueConstraint


class ClaimDocument(SQLModel, table=True):
    """Documento asociado a un siniestro (checklist dinámico)."""
    __tablename__ = "siniestro_documento"
    __table_args__ = (
        UniqueConstraint("siniestro_id", "tipo_documento", name="uq_sinDoc_tipo"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    siniestro_id: int = Field(foreign_key="siniestro.id", index=True)

    tipo_documento: str
    recibido: bool = Field(default=False)
    fecha_recepcion: Optional[date] = Field(default=None)
    archivo_url: Optional[str] = Field(default=None)
    notas: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClaimDocumentCreate(SQLModel):
    organization_id: uuid.UUID
    siniestro_id: int
    tipo_documento: str
    recibido: bool = False
    fecha_recepcion: Optional[date] = None
    archivo_url: Optional[str] = None
    notas: Optional[str] = None


class ClaimDocumentRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    siniestro_id: int
    tipo_documento: str
    recibido: bool
    fecha_recepcion: Optional[date]
    archivo_url: Optional[str]
    notas: Optional[str]
    created_at: datetime


class ClaimDocumentUpdate(SQLModel):
    recibido: Optional[bool] = None
    fecha_recepcion: Optional[date] = None
    archivo_url: Optional[str] = None
    notas: Optional[str] = None
