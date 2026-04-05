"""
Rutas de Audit Log — solo accesibles por superadmin.
Prefijo: /audit
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import Optional

from app.database import get_session
from app.core.admin_deps import get_current_superadmin
from app.services.audit_service import audit_service

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(get_current_superadmin)],
)


@router.get("/logs")
def list_audit_logs(
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """Listar audit logs con filtros opcionales."""
    return audit_service.get_logs(
        session,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        action=action,
        organization_id=organization_id,
        skip=skip,
        limit=limit,
    )


@router.get("/logs/{resource_type}/{resource_id}")
def get_resource_audit_trail(
    resource_type: str,
    resource_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """Obtener el audit trail completo de un recurso específico."""
    return audit_service.get_logs(
        session,
        resource_type=resource_type,
        resource_id=resource_id,
        skip=skip,
        limit=limit,
    )
