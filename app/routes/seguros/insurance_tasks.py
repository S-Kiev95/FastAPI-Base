"""
Rutas de Tareas — CRUD + completar + mis tareas + vencidas.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.core.dependencies import get_current_active_user
from app.models.user import UserRead
from app.models.seguros.insurance_task import InsuranceTaskCreate, InsuranceTaskRead, InsuranceTaskUpdate
from app.services.seguros.insurance_task_service import insurance_task_service

router = APIRouter(prefix="/tareas", tags=["tareas"])


@router.get("/", response_model=List[InsuranceTaskRead])
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    return insurance_task_service.get_all(session, skip=skip, limit=limit, organization_id=tenant.org_id)


@router.get("/mis-tareas", response_model=List[InsuranceTaskRead])
async def get_my_tasks(
    current_user: UserRead = Depends(get_current_active_user),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Tareas asignadas al usuario actual."""
    return insurance_task_service.get_assigned_to(session, current_user.id)


@router.get("/vencidas", response_model=List[InsuranceTaskRead])
async def get_overdue_tasks(
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Tareas vencidas de la organización."""
    return insurance_task_service.get_overdue(session, tenant.org_id)


@router.get("/{task_id}", response_model=InsuranceTaskRead)
async def get_task(
    task_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = insurance_task_service.get_by_id(session, task_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return obj


@router.post("/", response_model=InsuranceTaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: InsuranceTaskCreate,
    current_user: UserRead = Depends(get_current_active_user),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    data.organization_id = tenant.org_id
    data.creado_por = current_user.id
    return await insurance_task_service.create(session, data)


@router.patch("/{task_id}", response_model=InsuranceTaskRead)
async def update_task(
    task_id: int,
    data: InsuranceTaskUpdate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = insurance_task_service.get_by_id(session, task_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return await insurance_task_service.update(session, task_id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = insurance_task_service.get_by_id(session, task_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    await insurance_task_service.delete(session, task_id)


@router.post("/{task_id}/completar", response_model=InsuranceTaskRead)
async def complete_task(
    task_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Marcar tarea como completada."""
    result = await insurance_task_service.complete_task(session, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return result
