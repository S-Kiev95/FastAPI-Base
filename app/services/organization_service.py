"""
Servicios para Organization y Membership.
"""
import uuid
from typing import Optional, List
from sqlmodel import Session, select

from app.models.organization import (
    Organization, OrganizationCreate, OrganizationUpdate, OrganizationRead,
    Membership, MembershipRole, slugify,
)
from app.services.base_service import BaseService
from app.services.websocket.channels import organizations_channel
from app.config import settings


class OrganizationService(BaseService[Organization, OrganizationCreate, OrganizationUpdate, OrganizationRead]):

    def __init__(self):
        super().__init__(
            model=Organization,
            channel=organizations_channel,
            read_schema=OrganizationRead,
        )

    def get_by_slug(self, session: Session, slug: str) -> Optional[Organization]:
        stmt = select(Organization).where(Organization.slug == slug)
        return session.exec(stmt).first()

    def get_user_organizations(self, session: Session, user_id: int) -> List[Organization]:
        """Retorna las organizaciones donde el usuario tiene membership activa."""
        stmt = (
            select(Organization)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == user_id, Membership.is_active == True)
        )
        return list(session.exec(stmt).all())

    def get_system_organization(self, session: Session) -> Optional[Organization]:
        stmt = select(Organization).where(Organization.is_system == True)
        return session.exec(stmt).first()

    def create_with_owner(
        self,
        session: Session,
        name: str,
        slug: str,
        owner_user_id: int,
        plan: Optional[str] = None,
    ) -> tuple[Organization, Membership]:
        """Crea una organización y asigna al usuario como owner."""
        org = Organization(
            name=name,
            slug=slug,
            plan=plan or settings.DEFAULT_PLAN,
        )
        session.add(org)
        session.flush()

        membership = Membership(
            user_id=owner_user_id,
            organization_id=org.id,
            role=MembershipRole.owner,
        )
        session.add(membership)
        session.commit()
        session.refresh(org)
        session.refresh(membership)
        return org, membership


class MembershipService:

    def get_membership(
        self, session: Session, org_id: uuid.UUID, user_id: int
    ) -> Optional[Membership]:
        stmt = select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == user_id,
            Membership.is_active == True,
        )
        return session.exec(stmt).first()

    def get_org_members(self, session: Session, org_id: uuid.UUID) -> List[Membership]:
        stmt = select(Membership).where(
            Membership.organization_id == org_id,
            Membership.is_active == True,
        )
        return list(session.exec(stmt).all())

    def add_member(
        self,
        session: Session,
        org_id: uuid.UUID,
        user_id: int,
        role: str = MembershipRole.member,
    ) -> Membership:
        membership = Membership(
            user_id=user_id,
            organization_id=org_id,
            role=role,
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)
        return membership

    def remove_member(self, session: Session, org_id: uuid.UUID, user_id: int) -> bool:
        membership = self.get_membership(session, org_id, user_id)
        if not membership:
            return False
        if membership.role == MembershipRole.owner:
            return False  # El owner no puede ser removido
        membership.is_active = False
        session.add(membership)
        session.commit()
        return True

    def update_role(
        self,
        session: Session,
        org_id: uuid.UUID,
        user_id: int,
        new_role: str,
    ) -> Optional[Membership]:
        membership = self.get_membership(session, org_id, user_id)
        if not membership:
            return None
        membership.role = new_role
        session.add(membership)
        session.commit()
        session.refresh(membership)
        return membership


organization_service = OrganizationService()
membership_service = MembershipService()
