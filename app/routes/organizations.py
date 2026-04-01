"""
Rutas CRUD de organizaciones y gestión de miembros.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.dependencies import get_current_active_user
from app.core.tenant import TenantContext, get_current_organization, require_org_role
from app.models.user import UserRead
from app.models.organization import (
    OrganizationRead, OrganizationUpdate,
    MembershipCreate, MembershipRead, MembershipUpdate, MembershipRole,
    slugify,
)
from app.services.organization_service import organization_service, membership_service

router = APIRouter(prefix="/orgs", tags=["organizations"])


# ---- Organization CRUD ----

@router.get("/", response_model=List[OrganizationRead])
async def list_my_organizations(
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Lista las organizaciones donde el usuario tiene membership activa."""
    orgs = organization_service.get_user_organizations(session, current_user.id)
    return [OrganizationRead.model_validate(o) for o in orgs]


@router.get("/{org_slug}", response_model=OrganizationRead)
async def get_organization(
    tenant: TenantContext = Depends(get_current_organization),
):
    """Detalle de una organización (requiere membership)."""
    return OrganizationRead.model_validate(tenant.organization)


@router.patch("/{org_slug}", response_model=OrganizationRead)
async def update_organization(
    data: OrganizationUpdate,
    tenant: TenantContext = Depends(require_org_role(MembershipRole.admin)),
    session: Session = Depends(get_session),
):
    """Actualizar organización (requiere admin+)."""
    org = tenant.organization
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(org, key, value)
    session.add(org)
    session.commit()
    session.refresh(org)
    return OrganizationRead.model_validate(org)


# ---- Members ----

@router.get("/{org_slug}/members", response_model=List[MembershipRead])
async def list_members(
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Listar miembros de la organización (requiere membership)."""
    members = membership_service.get_org_members(session, tenant.org_id)
    return [MembershipRead.model_validate(m) for m in members]


@router.post("/{org_slug}/members", response_model=MembershipRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    data: MembershipCreate,
    tenant: TenantContext = Depends(require_org_role(MembershipRole.admin)),
    session: Session = Depends(get_session),
):
    """Agregar miembro a la organización (requiere admin+)."""
    # Verificar que no exista ya
    existing = membership_service.get_membership(session, tenant.org_id, data.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya es miembro de esta organización",
        )
    membership = membership_service.add_member(
        session, tenant.org_id, data.user_id, data.role
    )
    return MembershipRead.model_validate(membership)


@router.patch("/{org_slug}/members/{user_id}", response_model=MembershipRead)
async def update_member_role(
    user_id: int,
    data: MembershipUpdate,
    tenant: TenantContext = Depends(require_org_role(MembershipRole.owner)),
    session: Session = Depends(get_session),
):
    """Cambiar rol de un miembro (solo owner)."""
    if data.role is None:
        raise HTTPException(status_code=400, detail="Se requiere el campo 'role'")
    membership = membership_service.update_role(session, tenant.org_id, user_id, data.role)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership no encontrada")
    return MembershipRead.model_validate(membership)


@router.delete("/{org_slug}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: int,
    tenant: TenantContext = Depends(require_org_role(MembershipRole.admin)),
    session: Session = Depends(get_session),
):
    """Remover miembro de la organización (requiere admin+). El owner no puede ser removido."""
    removed = membership_service.remove_member(session, tenant.org_id, user_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo remover al miembro (no existe o es owner)",
        )
