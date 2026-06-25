"""
Service de relación Aseguradora-Taller (M2M).
"""
from typing import List
from sqlmodel import Session, select
from app.models.seguros.insurer_workshop import (
    InsurerWorkshop, InsurerWorkshopCreate, InsurerWorkshopUpdate, InsurerWorkshopRead,
)
from app.services.base_service import BaseService
from app.services.websocket import insurer_workshops_channel


class InsurerWorkshopService(BaseService[InsurerWorkshop, InsurerWorkshopCreate, InsurerWorkshopUpdate, InsurerWorkshopRead]):

    def __init__(self):
        super().__init__(
            model=InsurerWorkshop,
            channel=insurer_workshops_channel,
            read_schema=InsurerWorkshopRead,
        )

    def get_by_insurer(self, session: Session, aseguradora_id: int) -> List[InsurerWorkshop]:
        """Relaciones de una aseguradora con talleres."""
        statement = (
            select(InsurerWorkshop)
            .where(InsurerWorkshop.aseguradora_id == aseguradora_id)
            .order_by(InsurerWorkshop.prioridad)
        )
        return list(session.exec(statement).all())

    def get_by_workshop(self, session: Session, taller_id: int) -> List[InsurerWorkshop]:
        """Aseguradoras que acreditan a un taller."""
        statement = select(InsurerWorkshop).where(InsurerWorkshop.taller_id == taller_id)
        return list(session.exec(statement).all())


insurer_workshop_service = InsurerWorkshopService()
