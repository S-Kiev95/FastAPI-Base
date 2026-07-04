"""
Rutas de Vehículos — CRUD estándar.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.seguros.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.services.seguros.vehicle_service import vehicle_service

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])


@router.get("/", response_model=List[VehicleRead])
async def list_vehicles(
    skip: int = 0,
    limit: int = 100,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    return vehicle_service.get_all(session, skip=skip, limit=limit, organization_id=tenant.org_id)


@router.get("/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(
    vehicle_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = vehicle_service.get_by_id(session, vehicle_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return obj


@router.post("/", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    data: VehicleCreate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    data.organization_id = tenant.org_id
    return await vehicle_service.create(session, data)


@router.patch("/{vehicle_id}", response_model=VehicleRead)
async def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = vehicle_service.get_by_id(session, vehicle_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return await vehicle_service.update(session, vehicle_id, data)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = vehicle_service.get_by_id(session, vehicle_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    await vehicle_service.delete(session, vehicle_id)
