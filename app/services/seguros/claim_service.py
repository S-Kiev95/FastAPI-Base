"""
Service de Siniestro — CRUD + filtros por póliza y estado.
"""
import uuid
from typing import List
from sqlmodel import Session, select
from app.models.seguros.claim import Claim, ClaimCreate, ClaimUpdate, ClaimRead
from app.services.base_service import BaseService
from app.services.websocket import claims_channel


class ClaimService(BaseService[Claim, ClaimCreate, ClaimUpdate, ClaimRead]):

    def __init__(self):
        super().__init__(
            model=Claim,
            channel=claims_channel,
            read_schema=ClaimRead,
        )

    def get_by_policy(self, session: Session, poliza_id: int) -> List[Claim]:
        """Siniestros de una póliza."""
        statement = select(Claim).where(Claim.poliza_id == poliza_id)
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())

    def get_by_status(
        self, session: Session, organization_id: uuid.UUID, estado: str
    ) -> List[Claim]:
        """Siniestros filtrados por estado."""
        statement = (
            select(Claim)
            .where(Claim.organization_id == organization_id)
            .where(Claim.estado == estado)
        )
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())


claim_service = ClaimService()
