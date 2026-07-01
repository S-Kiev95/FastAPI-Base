"""
Rutas de Siniestros — CRUD + documentos.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.seguros.claim import ClaimCreate, ClaimRead, ClaimUpdate
from app.models.seguros.claim_document import ClaimDocumentCreate, ClaimDocumentRead
from app.services.seguros.claim_service import claim_service
from app.services.seguros.claim_document_service import claim_document_service
from app.services.seguros.enrich import enrich_claims

router = APIRouter(prefix="/siniestros", tags=["siniestros"])


@router.get("/", response_model=List[ClaimRead])
async def list_claims(
    skip: int = 0,
    limit: int = 100,
    estado: str = None,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    if estado:
        claims = claim_service.get_by_status(session, tenant.org_id, estado)
    else:
        claims = claim_service.get_all(session, skip=skip, limit=limit, organization_id=tenant.org_id)
    return enrich_claims(session, claims)


@router.get("/{claim_id}", response_model=ClaimRead)
async def get_claim(
    claim_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = claim_service.get_by_id(session, claim_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    return enrich_claims(session, [obj])[0]


@router.post("/", response_model=ClaimRead, status_code=status.HTTP_201_CREATED)
async def create_claim(
    data: ClaimCreate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    data.organization_id = tenant.org_id
    return await claim_service.create(session, data)


@router.patch("/{claim_id}", response_model=ClaimRead)
async def update_claim(
    claim_id: int,
    data: ClaimUpdate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = claim_service.get_by_id(session, claim_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    return await claim_service.update(session, claim_id, data)


@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_claim(
    claim_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    obj = claim_service.get_by_id(session, claim_id)
    if not obj or obj.organization_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    await claim_service.delete(session, claim_id)


@router.get("/{claim_id}/documentos", response_model=List[ClaimDocumentRead])
async def get_claim_documents(
    claim_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Documentos de un siniestro."""
    return claim_document_service.get_by_claim(session, claim_id)


@router.post("/{claim_id}/documentos", response_model=ClaimDocumentRead, status_code=status.HTTP_201_CREATED)
async def add_claim_document(
    claim_id: int,
    data: ClaimDocumentCreate,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Agregar documento a un siniestro."""
    data.organization_id = tenant.org_id
    data.siniestro_id = claim_id
    return await claim_document_service.create(session, data)


@router.post("/{claim_id}/documentos/{doc_id}/recibido", response_model=ClaimDocumentRead)
async def mark_document_received(
    claim_id: int,
    doc_id: int,
    tenant: TenantContext = Depends(get_current_organization),
    session: Session = Depends(get_session),
):
    """Marcar documento como recibido."""
    result = await claim_document_service.mark_received(session, doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return result
