"""
Equipo de la organización — miembros e invitaciones, reachable por /api.

Envuelve los servicios existentes (membership/invitation) agregando:
- enriquecimiento de miembros con nombre/email del usuario,
- devolución del token/link de aceptación al crear (porque el email SMTP
  puede no estar configurado en dev).
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization, require_org_role
from app.core.dependencies import get_current_active_user
from app.models.user import User, UserRead
from app.models.organization import MembershipRole
from app.models.invitation import InvitationRead
from app.services.organization_service import membership_service
from app.services.invitation_service import invitation_service
from app.config import settings

router = APIRouter(prefix="/equipo", tags=["equipo"])


class InviteRequest(BaseModel):
    email: str
    role: str = "member"


class RoleUpdate(BaseModel):
    role: str


@router.get("/miembros")
async def list_members(
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Miembros activos de la organización con nombre/email del usuario."""
    members = membership_service.get_org_members(session, tenant.org_id)
    uids = {m.user_id for m in members}
    users = (
        {u.id: u for u in session.exec(select(User).where(User.id.in_(uids))).all()}
        if uids else {}
    )
    out = []
    for m in members:
        u = users.get(m.user_id)
        out.append({
            "user_id": m.user_id,
            "nombre": (u.name or u.email) if u else None,
            "email": u.email if u else None,
            "role": m.role,
            "is_active": m.is_active,
        })
    return out


@router.patch("/miembros/{user_id}")
async def update_member_role(
    user_id: int,
    data: RoleUpdate,
    tenant: TenantContext = Depends(require_org_role(MembershipRole.admin)),
    session: Session = Depends(get_session),
):
    """Cambia el rol de un miembro (requiere admin+)."""
    m = membership_service.update_role(session, tenant.org_id, user_id, data.role)
    if not m:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    return {"user_id": m.user_id, "role": m.role, "is_active": m.is_active}


@router.delete("/miembros/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: int,
    tenant: TenantContext = Depends(require_org_role(MembershipRole.admin)),
    session: Session = Depends(get_session),
):
    """Remueve un miembro de la organización (no se puede remover al owner)."""
    ok = membership_service.remove_member(session, tenant.org_id, user_id)
    if not ok:
        raise HTTPException(status_code=400, detail="No se pudo remover el miembro (¿es el owner?)")


@router.get("/invitaciones", response_model=List[InvitationRead])
async def list_invitations(
    tenant: TenantContext = Depends(require_org_role(MembershipRole.admin)),
    session: Session = Depends(get_session),
):
    """Invitaciones pendientes (requiere admin+)."""
    return invitation_service.get_pending_invitations(session, tenant.org_id)


@router.post("/invitaciones", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    data: InviteRequest,
    current_user: UserRead = Depends(get_current_active_user),
    tenant: TenantContext = Depends(require_org_role(MembershipRole.admin)),
    session: Session = Depends(get_session),
):
    """Crea una invitación (requiere admin+). Devuelve la invitación + el link
    de aceptación con el token en claro (para poder compartirlo si el email
    no está configurado)."""
    invitation, raw_token = invitation_service.create_invitation(
        session, tenant.org_id, data.email, data.role, current_user.id,
    )
    # Intento de envío por email (no-op si SMTP no está configurado)
    try:
        from app.services.email_service import email_service
        accept_url = f"{settings.FRONTEND_URL}/app/aceptar-invitacion?token={raw_token}"
        await email_service.send_invitation_email(
            to=data.email,
            org_name=tenant.organization.name,
            inviter_name=current_user.name or current_user.email,
            role=data.role,
            accept_url=accept_url,
        )
    except Exception:
        pass

    return {
        "invitation": InvitationRead.model_validate(invitation).model_dump(),
        "accept_token": raw_token,
        "accept_path": f"/app/aceptar-invitacion?token={raw_token}",
    }


@router.delete("/invitaciones/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    tenant: TenantContext = Depends(require_org_role(MembershipRole.admin)),
    session: Session = Depends(get_session),
):
    """Revoca una invitación pendiente (requiere admin+)."""
    ok = invitation_service.revoke_invitation(session, invitation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
