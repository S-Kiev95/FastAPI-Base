"""
Rutas de Pólizas — CRUD + renovar + por vencer + cuotas/siniestros.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.seguros.policy import PolicyCreate, PolicyRead, PolicyUpdate
from app.models.seguros.installment import InstallmentRead
from app.models.seguros.claim import ClaimRead
from app.services.seguros.policy_service import policy_service
from app.services.seguros.installment_service import installment_service
from app.services.seguros.claim_service import claim_service

router = APIRouter(prefix="/polizas", tags=["polizas"])


@router.get("/", response_model=List[PolicyRead])
async def list_policies(
    skip: int = 0,
    limit: int = 100,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    return policy_service.get_all(session, skip=skip, limit=limit, organization_id=tenant.org_id)


@router.get("/por-vencer", response_model=List[PolicyRead])
async def get_expiring_policies(
    days: int = Query(30, description="Días de anticipación"),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Pólizas que vencen en los próximos N días."""
    return policy_service.get_expiring_soon(session, tenant.org_id, days=days)


@router.get("/{policy_id}", response_model=PolicyRead)
async def get_policy(
    policy_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = policy_service.get_by_id(session, policy_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    return obj


@router.post("/", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
async def create_policy(
    data: PolicyCreate,
    generar_cuotas: bool = Query(True, description="Generar cuotas automáticamente"),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Crear póliza y opcionalmente generar cuotas."""
    data.organization_id = tenant.org_id
    policy = await policy_service.create(session, data)
    if generar_cuotas and policy.prima_total and policy.total_cuotas > 0:
        await installment_service.generate_installments(session, policy)
    return policy


@router.patch("/{policy_id}", response_model=PolicyRead)
async def update_policy(
    policy_id: int,
    data: PolicyUpdate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = policy_service.get_by_id(session, policy_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    return await policy_service.update(session, policy_id, data)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = policy_service.get_by_id(session, policy_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    await policy_service.delete(session, policy_id)


@router.post("/{policy_id}/renovar", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
async def renew_policy(
    policy_id: int,
    data: PolicyCreate,
    generar_cuotas: bool = Query(True),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Renovar una póliza: marca la actual como 'renovada' y crea una nueva."""
    data.organization_id = tenant.org_id
    new_policy = await policy_service.renew_policy(session, policy_id, data)
    if generar_cuotas and new_policy.prima_total and new_policy.total_cuotas > 0:
        await installment_service.generate_installments(session, new_policy)
    return new_policy


@router.get("/{policy_id}/cuotas", response_model=List[InstallmentRead])
async def get_policy_installments(
    policy_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Cuotas de una póliza."""
    return installment_service.get_by_policy(session, policy_id)


@router.get("/{policy_id}/siniestros", response_model=List[ClaimRead])
async def get_policy_claims(
    policy_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Siniestros de una póliza."""
    return claim_service.get_by_policy(session, policy_id)
