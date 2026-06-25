"""
Rutas de Cuotas — listado, vencidas y marcar pagada.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from datetime import date
from pydantic import BaseModel

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.seguros.installment import InstallmentRead
from app.services.seguros.installment_service import installment_service

router = APIRouter(prefix="/cuotas", tags=["cuotas"])


class PagarRequest(BaseModel):
    fecha_pago: date
    metodo_pago: str = None


@router.get("/", response_model=List[InstallmentRead])
async def list_installments(
    skip: int = 0,
    limit: int = 100,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    return installment_service.get_all(session, skip=skip, limit=limit, organization_id=tenant.org_id)


@router.get("/vencidas", response_model=List[InstallmentRead])
async def get_overdue_installments(
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Cuotas vencidas (no pagadas con fecha pasada)."""
    return installment_service.get_overdue(session, tenant.org_id)


@router.post("/{installment_id}/pagar", response_model=InstallmentRead)
async def pay_installment(
    installment_id: int,
    data: PagarRequest,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Marcar una cuota como pagada."""
    obj = installment_service.get_by_id(session, installment_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    result = await installment_service.mark_paid(session, installment_id, data.fecha_pago, data.metodo_pago)
    return result
