"""
Rutas de Clientes — CRUD + búsqueda + vehículos/pólizas por cliente.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List, Optional

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.seguros.client import ClientCreate, ClientRead, ClientUpdate
from app.services.seguros.client_service import client_service
from app.services.seguros.vehicle_service import vehicle_service
from app.services.seguros.policy_service import policy_service
from app.models.seguros.vehicle import VehicleRead
from app.models.seguros.policy import PolicyRead

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("/", response_model=List[ClientRead])
async def list_clients(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = Query(None, description="Buscar por nombre/apellido/documento"),
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Listar clientes de la organización (con búsqueda opcional)."""
    if q:
        return client_service.search(session, tenant.org_id, q, limit=limit)
    return client_service.get_all(session, skip=skip, limit=limit, organization_id=tenant.org_id)


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Detalle de un cliente."""
    obj = client_service.get_by_id(session, client_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return obj


@router.post("/", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Crear un nuevo cliente."""
    data.organization_id = tenant.org_id
    return await client_service.create(session, data)


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: int,
    data: ClientUpdate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Actualizar un cliente."""
    obj = client_service.get_by_id(session, client_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return await client_service.update(session, client_id, data)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Eliminar un cliente (soft delete)."""
    obj = client_service.get_by_id(session, client_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    await client_service.delete(session, client_id)


@router.get("/{client_id}/vehiculos", response_model=List[VehicleRead])
async def get_client_vehicles(
    client_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Vehículos de un cliente."""
    return vehicle_service.get_by_client(session, client_id)


@router.get("/{client_id}/polizas", response_model=List[PolicyRead])
async def get_client_policies(
    client_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Pólizas de un cliente."""
    return policy_service.get_by_client(session, client_id)
