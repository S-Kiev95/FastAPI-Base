"""
Usuarios de la organización — para dropdowns de mensajería y asignación de tareas.
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.user import User
from app.models.organization import Membership

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/")
async def list_org_users(
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Lista los usuarios (miembros activos) de la organización."""
    stmt = (
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == tenant.org_id)
        .where(Membership.is_active == True)  # noqa: E712
    )
    users = session.exec(stmt).all()
    return [{"id": u.id, "nombre": u.name or u.email, "email": u.email} for u in users]
