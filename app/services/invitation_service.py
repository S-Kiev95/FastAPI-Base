"""
Servicio de invitaciones a organizaciones.
"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlmodel import Session, select

from app.models.invitation import Invitation
from app.models.organization import Membership, MembershipRole
from app.core.security import hash_token
from app.config import settings


class InvitationService:

    def create_invitation(
        self,
        session: Session,
        org_id: uuid.UUID,
        email: str,
        role: str,
        invited_by: int,
    ) -> Tuple[Invitation, str]:
        """
        Crea una invitación y retorna (invitation, raw_token).
        El raw_token se envía por email; solo el hash se guarda en BD.
        """
        raw_token = secrets.token_urlsafe(48)
        token_h = hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(hours=settings.INVITATION_EXPIRE_HOURS)

        invitation = Invitation(
            organization_id=org_id,
            email=email,
            role=role,
            token_hash=token_h,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        session.add(invitation)
        session.commit()
        session.refresh(invitation)
        return invitation, raw_token

    def accept_invitation(
        self, session: Session, raw_token: str, user_id: int
    ) -> Optional[Membership]:
        """
        Acepta una invitación: marca accepted_at y crea Membership.
        Retorna None si token inválido, expirado o ya aceptado.
        """
        token_h = hash_token(raw_token)
        stmt = select(Invitation).where(Invitation.token_hash == token_h)
        invitation = session.exec(stmt).first()

        if not invitation:
            return None
        if invitation.accepted_at is not None:
            return None
        if invitation.expires_at < datetime.utcnow():
            return None

        # Marcar como aceptada
        invitation.accepted_at = datetime.utcnow()
        session.add(invitation)

        # Verificar que no exista membership previa
        stmt = select(Membership).where(
            Membership.organization_id == invitation.organization_id,
            Membership.user_id == user_id,
        )
        existing = session.exec(stmt).first()
        if existing:
            # Reactivar si estaba inactiva
            if not existing.is_active:
                existing.is_active = True
                existing.role = invitation.role
                session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        # Crear nueva membership
        membership = Membership(
            user_id=user_id,
            organization_id=invitation.organization_id,
            role=invitation.role,
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)
        return membership

    def get_pending_invitations(
        self, session: Session, org_id: uuid.UUID
    ) -> List[Invitation]:
        """Retorna invitaciones no aceptadas y no expiradas de una org."""
        now = datetime.utcnow()
        stmt = select(Invitation).where(
            Invitation.organization_id == org_id,
            Invitation.accepted_at == None,  # noqa: E711
            Invitation.expires_at > now,
        )
        return list(session.exec(stmt).all())

    def revoke_invitation(
        self, session: Session, invitation_id: uuid.UUID
    ) -> bool:
        """Revoca (elimina) una invitación pendiente. Retorna False si no existe."""
        stmt = select(Invitation).where(Invitation.id == invitation_id)
        invitation = session.exec(stmt).first()
        if not invitation or invitation.accepted_at is not None:
            return False
        session.delete(invitation)
        session.commit()
        return True


invitation_service = InvitationService()
