"""
Service de Taller — CRUD + filtros por departamento y aseguradora.
"""
import uuid
from typing import List
from sqlmodel import Session, select
from app.models.seguros.workshop import Workshop, WorkshopCreate, WorkshopUpdate, WorkshopRead
from app.models.seguros.insurer_workshop import InsurerWorkshop
from app.services.base_service import BaseService
from app.services.websocket import workshops_channel


class WorkshopService(BaseService[Workshop, WorkshopCreate, WorkshopUpdate, WorkshopRead]):

    def __init__(self):
        super().__init__(
            model=Workshop,
            channel=workshops_channel,
            read_schema=WorkshopRead,
        )

    def get_by_departamento(
        self, session: Session, organization_id: uuid.UUID, departamento: str
    ) -> List[Workshop]:
        """Talleres filtrados por departamento."""
        statement = (
            select(Workshop)
            .where(Workshop.organization_id == organization_id)
            .where(Workshop.departamento == departamento)
        )
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())

    def get_by_insurer(self, session: Session, aseguradora_id: int) -> List[Workshop]:
        """Talleres acreditados por una aseguradora."""
        statement = (
            select(Workshop)
            .join(InsurerWorkshop, InsurerWorkshop.taller_id == Workshop.id)
            .where(InsurerWorkshop.aseguradora_id == aseguradora_id)
            .where(InsurerWorkshop.activo == True)
        )
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())


workshop_service = WorkshopService()
