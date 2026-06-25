"""
Modelo de Mensaje — mensajería interna entre usuarios de la organización.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    """Mensaje interno entre usuarios de la misma organización."""
    __tablename__ = "mensaje"

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    remitente_id: int = Field(foreign_key="users.id")
    destinatario_id: int = Field(foreign_key="users.id", index=True)

    asunto: Optional[str] = Field(default=None)
    contenido: str
    leido: bool = Field(default=False)
    fecha_leido: Optional[datetime] = Field(default=None)

    # Vinculación opcional a entidades del sistema
    cliente_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    poliza_id: Optional[int] = Field(default=None, foreign_key="poliza.id")
    siniestro_id: Optional[int] = Field(default=None, foreign_key="siniestro.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class MessageCreate(SQLModel):
    organization_id: uuid.UUID
    remitente_id: int
    destinatario_id: int
    asunto: Optional[str] = None
    contenido: str
    cliente_id: Optional[int] = None
    poliza_id: Optional[int] = None
    siniestro_id: Optional[int] = None


class MessageRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    remitente_id: int
    destinatario_id: int
    asunto: Optional[str]
    contenido: str
    leido: bool
    fecha_leido: Optional[datetime]
    cliente_id: Optional[int]
    poliza_id: Optional[int]
    siniestro_id: Optional[int]
    created_at: datetime


class MessageUpdate(SQLModel):
    leido: Optional[bool] = None
    fecha_leido: Optional[datetime] = None
