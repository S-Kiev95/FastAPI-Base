"""
Rutas de Mensajes — bandeja de entrada, enviados, enviar, no leídos.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.core.dependencies import get_current_active_user
from app.models.user import UserRead
from app.models.seguros.message import MessageCreate, MessageRead
from app.services.seguros.message_service import message_service
from app.services.seguros.enrich import enrich_messages

router = APIRouter(prefix="/mensajes", tags=["mensajes"])


@router.get("/inbox", response_model=List[MessageRead])
async def get_inbox(
    skip: int = 0,
    limit: int = 50,
    current_user: UserRead = Depends(get_current_active_user),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Bandeja de entrada del usuario."""
    return enrich_messages(session, message_service.get_inbox(session, current_user.id, skip=skip, limit=limit))


@router.get("/enviados", response_model=List[MessageRead])
async def get_sent(
    skip: int = 0,
    limit: int = 50,
    current_user: UserRead = Depends(get_current_active_user),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Mensajes enviados por el usuario."""
    return enrich_messages(session, message_service.get_sent(session, current_user.id, skip=skip, limit=limit))


@router.get("/no-leidos/count")
async def get_unread_count(
    current_user: UserRead = Depends(get_current_active_user),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Cantidad de mensajes no leídos."""
    count = message_service.get_unread_count(session, current_user.id)
    return {"count": count}


@router.post("/", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    current_user: UserRead = Depends(get_current_active_user),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Enviar un mensaje."""
    data.organization_id = tenant.org_id
    data.remitente_id = current_user.id
    return await message_service.create(session, data)


@router.post("/{message_id}/leer", response_model=MessageRead)
async def mark_read(
    message_id: int,
    current_user: UserRead = Depends(get_current_active_user),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Marcar mensaje como leído."""
    result = await message_service.mark_read(session, message_id)
    if not result:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    return result
