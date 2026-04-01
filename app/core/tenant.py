"""
Dependencias de multi-tenancy para inyectar en rutas.
Verifica que el usuario tenga membership activa en la organización.
"""
from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.core.dependencies import get_current_active_user
from app.models.user import UserRead
from app.models.organization import Organization, Membership, MembershipRole, role_gte
from app.services.organization_service import organization_service, membership_service


class TenantContext:
    """Contexto de tenant: organización + membership del usuario actual."""
    def __init__(self, organization: Organization, membership: Membership):
        self.organization = organization
        self.membership = membership

    @property
    def org_id(self):
        return self.organization.id

    @property
    def role(self) -> str:
        return self.membership.role


async def get_current_organization(
    org_slug: str,
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
) -> TenantContext:
    """
    Verifica que el usuario tenga membership activa en la org.
    Inyectar en rutas que operen sobre datos de un tenant.

    Uso:
        @router.get("/orgs/{org_slug}/items")
        async def list_items(tenant: TenantContext = Depends(get_current_organization)):
            org_id = tenant.org_id
    """
    org = organization_service.get_by_slug(session, org_slug)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organización '{org_slug}' no encontrada",
        )

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organización desactivada",
        )

    membership = membership_service.get_membership(session, org.id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés acceso a esta organización",
        )

    return TenantContext(organization=org, membership=membership)


def require_org_role(minimum_role: MembershipRole):
    """
    Dependency factory que verifica rol mínimo dentro de la org.
    Jerarquía: owner > admin > member > viewer.

    Uso:
        @router.delete("/orgs/{org_slug}/items/{id}")
        async def delete_item(
            tenant: TenantContext = Depends(require_org_role(MembershipRole.admin))
        ):
    """
    async def check_role(
        tenant: TenantContext = Depends(get_current_organization),
    ) -> TenantContext:
        if not role_gte(MembershipRole(tenant.role), minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol '{minimum_role.value}' o superior",
            )
        return tenant

    return check_role
