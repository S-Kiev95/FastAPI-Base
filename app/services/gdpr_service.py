"""
Servicio GDPR — exportación de datos y eliminación de cuenta.
Cumple con derecho de acceso (Art. 15) y derecho al olvido (Art. 17).
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlmodel import Session, select

from app.config import settings

logger = logging.getLogger(__name__)


class GDPRService:
    """Exportación de datos personales y eliminación con período de gracia."""

    def export_user_data(self, session: Session, user_id: int) -> Dict[str, Any]:
        """
        Exporta todos los datos personales del usuario (Art. 15 GDPR).
        Retorna un dict JSON-serializable con toda la información.
        """
        from app.models.user import User
        from app.models.organization import Membership
        from app.models.api_key import ApiKey
        from app.models.audit_log import AuditLog

        user = session.get(User, user_id)
        if not user:
            return {}

        # Datos del perfil
        profile = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "provider": user.provider,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

        # Membresías
        memberships = session.exec(
            select(Membership).where(Membership.user_id == user_id)
        ).all()
        membership_data = [
            {
                "organization_id": str(m.organization_id),
                "role": m.role,
                "is_active": m.is_active,
                "joined_at": m.joined_at.isoformat() if hasattr(m, 'joined_at') and m.joined_at else None,
            }
            for m in memberships
        ]

        # API Keys (sin hashes)
        api_keys = session.exec(
            select(ApiKey).where(ApiKey.user_id == user_id)
        ).all()
        api_key_data = [
            {
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in api_keys
        ]

        # Audit trail del usuario
        audit_logs = session.exec(
            select(AuditLog).where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(500)
        ).all()
        audit_data = [
            {
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "ip_address": a.ip_address,
            }
            for a in audit_logs
        ]

        return {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "profile": profile,
            "memberships": membership_data,
            "api_keys": api_key_data,
            "audit_log": audit_data,
        }

    def request_account_deletion(
        self, session: Session, user_id: int
    ) -> Optional[datetime]:
        """
        Solicita eliminación de cuenta con período de gracia (Art. 17 GDPR).
        Marca la cuenta como pendiente de eliminación (soft delete con fecha futura).
        Retorna la fecha efectiva de eliminación.
        """
        from app.models.user import User

        user = session.get(User, user_id)
        if not user:
            return None

        grace_days = settings.ACCOUNT_DELETION_GRACE_DAYS
        deletion_date = datetime.now(timezone.utc) + timedelta(days=grace_days)

        # Marcar con soft delete (la fecha indica cuándo se completará)
        user.deleted_at = deletion_date
        user.is_active = False
        session.add(user)
        session.commit()

        logger.info(
            f"Cuenta {user_id} marcada para eliminación el {deletion_date.isoformat()}"
        )
        return deletion_date

    def cancel_account_deletion(self, session: Session, user_id: int) -> bool:
        """
        Cancela una solicitud de eliminación pendiente (dentro del período de gracia).
        Restaura la cuenta.
        """
        from app.models.user import User

        user = session.get(User, user_id)
        if not user or user.deleted_at is None:
            return False

        # Solo cancelar si aún está en período de gracia
        deleted_at = user.deleted_at if user.deleted_at.tzinfo else user.deleted_at.replace(tzinfo=timezone.utc)
        if deleted_at <= datetime.now(timezone.utc):
            return False  # Ya pasó la fecha

        user.deleted_at = None
        user.is_active = True
        session.add(user)
        session.commit()

        logger.info(f"Eliminación de cuenta {user_id} cancelada")
        return True

    def purge_expired_accounts(self, session: Session) -> int:
        """
        Hard delete de cuentas cuyo período de gracia expiró.
        Diseñado para correr como tarea programada (ARQ worker / cron).
        Retorna cantidad de cuentas purgadas.
        """
        from app.models.user import User
        from app.models.api_key import ApiKey
        from app.models.organization import Membership

        now = datetime.now(timezone.utc)
        expired = session.exec(
            select(User).where(
                User.deleted_at.is_not(None),
                User.deleted_at <= now,
            )
        ).all()

        count = 0
        for user in expired:
            # Revocar API keys
            keys = session.exec(
                select(ApiKey).where(ApiKey.user_id == user.id)
            ).all()
            for key in keys:
                session.delete(key)

            # Eliminar membresías
            memberships = session.exec(
                select(Membership).where(Membership.user_id == user.id)
            ).all()
            for m in memberships:
                session.delete(m)

            # Hard delete del usuario
            session.delete(user)
            count += 1

        if count > 0:
            session.commit()
            logger.info(f"Purgadas {count} cuentas expiradas")

        return count


gdpr_service = GDPRService()
