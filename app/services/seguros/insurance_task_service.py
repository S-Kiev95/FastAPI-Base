"""
Service de Tarea — CRUD + asignación + vencidas + completar.
"""
import uuid
from datetime import date, datetime, timezone
from typing import List
from sqlmodel import Session, select
from app.models.seguros.insurance_task import (
    InsuranceTask, InsuranceTaskCreate, InsuranceTaskUpdate, InsuranceTaskRead, TaskStatus,
)
from app.services.base_service import BaseService
from app.services.websocket import insurance_tasks_channel


class InsuranceTaskService(BaseService[InsuranceTask, InsuranceTaskCreate, InsuranceTaskUpdate, InsuranceTaskRead]):

    def __init__(self):
        super().__init__(
            model=InsuranceTask,
            channel=insurance_tasks_channel,
            read_schema=InsuranceTaskRead,
        )

    def get_assigned_to(self, session: Session, user_id: int) -> List[InsuranceTask]:
        """Tareas asignadas a un usuario."""
        statement = (
            select(InsuranceTask)
            .where(InsuranceTask.asignado_a == user_id)
            .where(InsuranceTask.estado.notin_([TaskStatus.completada, TaskStatus.cancelada]))
        )
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())

    def get_overdue(self, session: Session, organization_id: uuid.UUID) -> List[InsuranceTask]:
        """Tareas vencidas (no completadas/canceladas)."""
        today = date.today()
        statement = (
            select(InsuranceTask)
            .where(InsuranceTask.organization_id == organization_id)
            .where(InsuranceTask.fecha_vencimiento < today)
            .where(InsuranceTask.estado.notin_([TaskStatus.completada, TaskStatus.cancelada]))
        )
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())

    async def complete_task(self, session: Session, task_id: int) -> InsuranceTask:
        """Marcar tarea como completada."""
        obj = session.get(InsuranceTask, task_id)
        if not obj:
            return None
        obj.estado = TaskStatus.completada
        obj.fecha_completada = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        await self.channel.broadcast_updated(
            InsuranceTaskRead.model_validate(obj).model_dump()
        )
        return obj


insurance_task_service = InsuranceTaskService()
