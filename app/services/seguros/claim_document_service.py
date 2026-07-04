"""
Service de Documento de Siniestro — CRUD + marcar recibido.
"""
from datetime import date, datetime, timezone
from typing import List
from sqlmodel import Session, select
from app.models.seguros.claim_document import (
    ClaimDocument, ClaimDocumentCreate, ClaimDocumentUpdate, ClaimDocumentRead,
)
from app.services.base_service import BaseService
from app.services.websocket import claim_documents_channel


class ClaimDocumentService(BaseService[ClaimDocument, ClaimDocumentCreate, ClaimDocumentUpdate, ClaimDocumentRead]):

    def __init__(self):
        super().__init__(
            model=ClaimDocument,
            channel=claim_documents_channel,
            read_schema=ClaimDocumentRead,
        )

    def get_by_claim(self, session: Session, siniestro_id: int) -> List[ClaimDocument]:
        """Documentos de un siniestro."""
        statement = select(ClaimDocument).where(ClaimDocument.siniestro_id == siniestro_id)
        return list(session.exec(statement).all())

    async def mark_received(self, session: Session, doc_id: int) -> ClaimDocument:
        """Marcar un documento como recibido."""
        obj = session.get(ClaimDocument, doc_id)
        if not obj:
            return None
        obj.recibido = True
        obj.fecha_recepcion = date.today()
        session.add(obj)
        session.commit()
        session.refresh(obj)
        await self.channel.broadcast_updated(
            ClaimDocumentRead.model_validate(obj).model_dump()
        )
        return obj


claim_document_service = ClaimDocumentService()
