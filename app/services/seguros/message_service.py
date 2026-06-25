"""
Service de Mensaje — bandeja de entrada, enviados, marcar leído.
"""
import uuid
from datetime import datetime, timezone
from typing import List
from sqlmodel import Session, select, func
from app.models.seguros.message import Message, MessageCreate, MessageUpdate, MessageRead
from app.services.base_service import BaseService
from app.services.websocket import messages_channel


class MessageService(BaseService[Message, MessageCreate, MessageUpdate, MessageRead]):

    def __init__(self):
        super().__init__(
            model=Message,
            channel=messages_channel,
            read_schema=MessageRead,
        )

    def get_inbox(
        self, session: Session, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[Message]:
        """Bandeja de entrada de un usuario."""
        statement = (
            select(Message)
            .where(Message.destinatario_id == user_id)
            .order_by(Message.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(session.exec(statement).all())

    def get_sent(
        self, session: Session, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[Message]:
        """Mensajes enviados por un usuario."""
        statement = (
            select(Message)
            .where(Message.remitente_id == user_id)
            .order_by(Message.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(session.exec(statement).all())

    async def mark_read(self, session: Session, message_id: int) -> Message:
        """Marcar mensaje como leído."""
        obj = session.get(Message, message_id)
        if not obj:
            return None
        obj.leido = True
        obj.fecha_leido = datetime.now(timezone.utc)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    def get_unread_count(self, session: Session, user_id: int) -> int:
        """Cantidad de mensajes no leídos."""
        statement = (
            select(func.count())
            .select_from(Message)
            .where(Message.destinatario_id == user_id)
            .where(Message.leido == False)
        )
        return session.exec(statement).one()


message_service = MessageService()
