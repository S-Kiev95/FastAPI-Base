"""
Service de Cliente — CRUD + búsqueda por nombre/documento.
"""
import uuid
from typing import List, Optional
from sqlmodel import Session, select, or_
from app.models.seguros.client import Client, ClientCreate, ClientUpdate, ClientRead
from app.services.base_service import BaseService
from app.services.websocket import clients_channel


class ClientService(BaseService[Client, ClientCreate, ClientUpdate, ClientRead]):

    def __init__(self):
        super().__init__(
            model=Client,
            channel=clients_channel,
            read_schema=ClientRead,
        )

    def search(
        self, session: Session, organization_id: uuid.UUID, query: str, limit: int = 50
    ) -> List[Client]:
        """Búsqueda por nombre, apellido o documento de identidad."""
        pattern = f"%{query}%"
        statement = (
            select(Client)
            .where(Client.organization_id == organization_id)
            .where(
                or_(
                    Client.nombre.ilike(pattern),
                    Client.apellido.ilike(pattern),
                    Client.documento_identidad.ilike(pattern),
                    Client.numero_cliente.ilike(pattern),
                )
            )
        )
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement.limit(limit)).all())


client_service = ClientService()
