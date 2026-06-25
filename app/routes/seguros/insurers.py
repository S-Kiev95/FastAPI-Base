"""
Rutas de Aseguradoras — CRUD + talleres vinculados.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.seguros.insurer import InsurerCreate, InsurerRead, InsurerUpdate
from app.models.seguros.insurer_workshop import InsurerWorkshopCreate, InsurerWorkshopRead
from app.models.seguros.workshop import WorkshopRead
from app.services.seguros.insurer_service import insurer_service
from app.services.seguros.insurer_workshop_service import insurer_workshop_service
from app.services.seguros.workshop_service import workshop_service

router = APIRouter(prefix="/aseguradoras", tags=["aseguradoras"])


@router.get("/", response_model=List[InsurerRead])
async def list_insurers(
    skip: int = 0,
    limit: int = 100,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    return insurer_service.get_all(session, skip=skip, limit=limit, organization_id=tenant.org_id)


@router.get("/{insurer_id}", response_model=InsurerRead)
async def get_insurer(
    insurer_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = insurer_service.get_by_id(session, insurer_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Aseguradora no encontrada")
    return obj


@router.post("/", response_model=InsurerRead, status_code=status.HTTP_201_CREATED)
async def create_insurer(
    data: InsurerCreate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    data.organization_id = tenant.org_id
    return await insurer_service.create(session, data)


@router.patch("/{insurer_id}", response_model=InsurerRead)
async def update_insurer(
    insurer_id: int,
    data: InsurerUpdate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = insurer_service.get_by_id(session, insurer_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Aseguradora no encontrada")
    return await insurer_service.update(session, insurer_id, data)


@router.delete("/{insurer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insurer(
    insurer_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = insurer_service.get_by_id(session, insurer_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Aseguradora no encontrada")
    await insurer_service.delete(session, insurer_id)


@router.get("/{insurer_id}/talleres", response_model=List[WorkshopRead])
async def get_insurer_workshops(
    insurer_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Talleres acreditados por esta aseguradora."""
    return workshop_service.get_by_insurer(session, insurer_id)


@router.post("/{insurer_id}/talleres", response_model=InsurerWorkshopRead, status_code=status.HTTP_201_CREATED)
async def link_workshop(
    insurer_id: int,
    data: InsurerWorkshopCreate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Vincular un taller a esta aseguradora."""
    data.organization_id = tenant.org_id
    data.aseguradora_id = insurer_id
    return await insurer_workshop_service.create(session, data)


@router.delete("/{insurer_id}/talleres/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_workshop(
    insurer_id: int,
    link_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Desvincular un taller de esta aseguradora."""
    await insurer_workshop_service.delete(session, link_id)
