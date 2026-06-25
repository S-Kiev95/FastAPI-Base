"""
Modelo de Tarea — tareas y calendario interno de la correduría.
"""
import uuid
from datetime import date, datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel
from app.models.mixins import SoftDeleteMixin


class TaskPriority(str, Enum):
    alta = "alta"
    media = "media"
    baja = "baja"


class TaskStatus(str, Enum):
    pendiente = "pendiente"
    en_progreso = "en_progreso"
    completada = "completada"
    cancelada = "cancelada"


class InsuranceTask(SoftDeleteMixin, SQLModel, table=True):
    """Tarea interna de la correduría, vinculable a cliente/póliza/siniestro."""
    __tablename__ = "tarea"

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    creado_por: int = Field(foreign_key="users.id")
    asignado_a: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    titulo: str
    descripcion: Optional[str] = Field(default=None)
    prioridad: str = Field(default=TaskPriority.media)
    estado: str = Field(default=TaskStatus.pendiente, index=True)
    fecha_vencimiento: Optional[date] = Field(default=None, index=True)
    fecha_completada: Optional[datetime] = Field(default=None)

    # Vinculación opcional a entidades del sistema
    cliente_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    poliza_id: Optional[int] = Field(default=None, foreign_key="poliza.id")
    siniestro_id: Optional[int] = Field(default=None, foreign_key="siniestro.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InsuranceTaskCreate(SQLModel):
    organization_id: uuid.UUID
    creado_por: int
    asignado_a: Optional[int] = None
    titulo: str
    descripcion: Optional[str] = None
    prioridad: str = TaskPriority.media
    estado: str = TaskStatus.pendiente
    fecha_vencimiento: Optional[date] = None
    cliente_id: Optional[int] = None
    poliza_id: Optional[int] = None
    siniestro_id: Optional[int] = None


class InsuranceTaskRead(SQLModel):
    id: int
    organization_id: uuid.UUID
    creado_por: int
    asignado_a: Optional[int]
    titulo: str
    descripcion: Optional[str]
    prioridad: str
    estado: str
    fecha_vencimiento: Optional[date]
    fecha_completada: Optional[datetime]
    cliente_id: Optional[int]
    poliza_id: Optional[int]
    siniestro_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class InsuranceTaskUpdate(SQLModel):
    asignado_a: Optional[int] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    prioridad: Optional[str] = None
    estado: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    fecha_completada: Optional[datetime] = None
    cliente_id: Optional[int] = None
    poliza_id: Optional[int] = None
    siniestro_id: Optional[int] = None
