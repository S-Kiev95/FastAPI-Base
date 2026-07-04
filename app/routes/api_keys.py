"""
Rutas de API Keys — CRUD para gestión de keys del usuario autenticado.
Prefijo: /api-keys
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.core.dependencies import get_current_active_user
from app.models.user import UserRead
from app.models.api_key import ApiKeyCreate, ApiKeyRead, ApiKeyCreateResponse
from app.services.api_key_service import api_key_service

router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"],
)


@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    data: ApiKeyCreate,
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Genera una nueva API key. El raw key solo se muestra una vez."""
    api_key, raw_key = api_key_service.create_key(
        session,
        user_id=current_user.id,
        name=data.name,
        scopes=data.scopes,
        expires_in_days=data.expires_in_days,
    )
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        raw_key=raw_key,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("/", response_model=list[ApiKeyRead])
def list_api_keys(
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Lista las API keys activas del usuario."""
    return api_key_service.list_keys(session, current_user.id)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Revoca una API key."""
    success = api_key_service.revoke_key(session, key_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key no encontrada o no pertenece al usuario",
        )
