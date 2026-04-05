"""
Servicio de auditoría — registra acciones sobre recursos.
No hereda de BaseService (los audit logs son inmutables, sin cache ni broadcast).
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select, func
from app.models.audit_log import AuditLog
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class AuditService:
    """Servicio standalone de audit log."""

    def record(
        self,
        session: Session,
        *,
        user_id: Optional[int] = None,
        organization_id: Optional[str] = None,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """Registra una entrada de auditoría. No-op si AUDIT_LOG_ENABLED=False."""
        if not settings.AUDIT_LOG_ENABLED:
            return None

        try:
            entry = AuditLog(
                user_id=user_id,
                organization_id=str(organization_id) if organization_id else None,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry
        except Exception as e:
            logger.error(f"Error registrando audit log: {e}")
            session.rollback()
            return None

    def get_logs(
        self,
        session: Session,
        *,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        organization_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Consulta audit logs con filtros. Retorna paginado."""
        query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)

        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            count_query = count_query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == str(resource_id))
            count_query = count_query.where(AuditLog.resource_id == str(resource_id))
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
            count_query = count_query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if organization_id:
            query = query.where(AuditLog.organization_id == str(organization_id))
            count_query = count_query.where(AuditLog.organization_id == str(organization_id))

        total = session.exec(count_query).one()
        results = list(
            session.exec(
                query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
            ).all()
        )

        return {
            "items": results,
            "total": total,
            "limit": limit,
            "offset": skip,
        }

    @staticmethod
    def compute_changes(old_obj, update_data: dict) -> Dict[str, Any]:
        """Calcula diff entre objeto actual y datos de actualización."""
        changes = {}
        for field, new_value in update_data.items():
            old_value = getattr(old_obj, field, None)
            if old_value != new_value:
                # Serializar valores para JSON
                changes[field] = {
                    "old": str(old_value) if old_value is not None else None,
                    "new": str(new_value) if new_value is not None else None,
                }
        return changes


audit_service = AuditService()
