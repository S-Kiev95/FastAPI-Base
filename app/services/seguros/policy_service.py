"""
Service de Póliza — CRUD + vencimientos + renovación.
"""
import uuid
from datetime import date, timedelta
from typing import List, Optional
from sqlmodel import Session, select
from app.models.seguros.policy import Policy, PolicyCreate, PolicyUpdate, PolicyRead, PolicyStatus
from app.services.base_service import BaseService
from app.services.websocket import policies_channel


class PolicyService(BaseService[Policy, PolicyCreate, PolicyUpdate, PolicyRead]):

    def __init__(self):
        super().__init__(
            model=Policy,
            channel=policies_channel,
            read_schema=PolicyRead,
        )

    def get_by_client(self, session: Session, cliente_id: int) -> List[Policy]:
        """Pólizas de un cliente."""
        statement = select(Policy).where(Policy.cliente_id == cliente_id)
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())

    def get_expiring_soon(
        self, session: Session, organization_id: uuid.UUID, days: int = 30
    ) -> List[Policy]:
        """Pólizas que vencen en los próximos N días."""
        today = date.today()
        limit_date = today + timedelta(days=days)
        statement = (
            select(Policy)
            .where(Policy.organization_id == organization_id)
            .where(Policy.estado == PolicyStatus.activa)
            .where(Policy.vigente_hasta >= today)
            .where(Policy.vigente_hasta <= limit_date)
            .order_by(Policy.vigente_hasta)
        )
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())

    async def renew_policy(
        self, session: Session, policy_id: int, new_data: PolicyCreate
    ) -> Policy:
        """Renueva una póliza: marca la actual como 'renovada' y crea una nueva."""
        old = session.get(Policy, policy_id)
        if old:
            old.estado = PolicyStatus.renovada
            session.add(old)
            session.commit()
        return await self.create(session, new_data)


policy_service = PolicyService()
