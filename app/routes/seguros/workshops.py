"""
Rutas de Talleres — CRUD con filtros por departamento/especialidad.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List, Optional

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.seguros.workshop import WorkshopCreate, WorkshopRead, WorkshopUpdate
from app.services.seguros.workshop_service import workshop_service

router = APIRouter(prefix="/talleres", tags=["talleres"])


@router.get("/", response_model=List[WorkshopRead])
async def list_workshops(
    skip: int = 0,
    limit: int = 100,
    departamento: Optional[str] = Query(None),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    if departamento:
        return workshop_service.get_by_departamento(session, tenant.org_id, departamento)
    return workshop_service.get_all(session, skip=skip, limit=limit, organization_id=tenant.org_id)


@router.get("/{workshop_id}", response_model=WorkshopRead)
async def get_workshop(
    workshop_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = workshop_service.get_by_id(session, workshop_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    return obj


@router.post("/", response_model=WorkshopRead, status_code=status.HTTP_201_CREATED)
async def create_workshop(
    data: WorkshopCreate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    data.organization_id = tenant.org_id
    return await workshop_service.create(session, data)


@router.patch("/{workshop_id}", response_model=WorkshopRead)
async def update_workshop(
    workshop_id: int,
    data: WorkshopUpdate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = workshop_service.get_by_id(session, workshop_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    return await workshop_service.update(session, workshop_id, data)


@router.delete("/{workshop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workshop(
    workshop_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = workshop_service.get_by_id(session, workshop_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    await workshop_service.delete(session, workshop_id)
