"""
Rutas de Dashboard — KPIs y próximos vencimientos.
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.seguros.policy import PolicyRead
from app.services.seguros.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
async def get_dashboard_stats(
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """KPIs principales del dominio de seguros."""
    return dashboard_service.get_stats(session, tenant.org_id)


@router.get("/proximos-vencimientos", response_model=List[PolicyRead])
async def get_upcoming_expirations(
    days: int = Query(30, description="Días de anticipación"),
    limit: int = Query(20, description="Cantidad máxima"),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Pólizas que vencen próximamente."""
    return dashboard_service.get_upcoming_expirations(
        session, tenant.org_id, days=days, limit=limit
    )
