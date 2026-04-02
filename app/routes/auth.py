"""
Rutas de autenticación: register, login, refresh tokens, logout,
verificación de email, password reset, aceptar invitación.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional
import logging

from app.database import get_session
from app.models.user import UserRegister, UserLogin, Token, UserRead, User
from app.models.organization import slugify
from app.models.refresh_token import RefreshToken
from app.services.user_service import user_service
from app.services.organization_service import organization_service
from app.services.invitation_service import invitation_service
from app.core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, hash_token,
    create_verification_token, create_password_reset_token,
    verify_purpose_token,
)
from app.core.dependencies import get_current_user, get_current_active_user
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# --- Schemas adicionales ---

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResendVerificationRequest(BaseModel):
    email: str


# --- Register ---

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    session: Session = Depends(get_session),
):
    """
    Registra un usuario nuevo. Crea User + Organization + Membership(owner).
    Envía email de verificación si SMTP está configurado.
    """
    existing_user = user_service.get_user_by_email(session, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_data.email,
        name=user_data.name,
        provider="local",
        provider_user_id=None,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_verified=False,
    )

    session.add(user)
    session.flush()

    # Generar nombre y slug de organización
    org_name = user_data.organization_name or user_data.email.split("@")[0]
    slug = slugify(org_name)

    existing_org = organization_service.get_by_slug(session, slug)
    if existing_org:
        import uuid as _uuid
        slug = f"{slug}-{_uuid.uuid4().hex[:6]}"

    organization_service.create_with_owner(
        session, name=org_name, slug=slug, owner_user_id=user.id
    )
    session.refresh(user)

    # Enviar email de verificación (encolado o directo)
    await _send_verification_email(user.email, user.name)

    # Broadcast via WebSocket
    user_dict = UserRead.model_validate(user).model_dump()
    await user_service.channel.broadcast_created(user_dict)

    return UserRead.model_validate(user)


# --- Login ---

@router.post("/login", response_model=TokenPair)
async def login(
    credentials: UserLogin,
    request: Request,
    session: Session = Depends(get_session),
):
    """
    Login con email y password.
    Retorna access_token (corto) + refresh_token (30 días).
    """
    user = user_service.get_user_by_email(session, credentials.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.provider != "local" or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This account uses {user.provider} authentication.",
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    # Access token
    access_token = create_access_token(data={"sub": user.email})

    # Refresh token — persistir en BD
    raw_refresh, token_hash, expires_at = create_refresh_token()
    user_agent = request.headers.get("user-agent")
    rt = RefreshToken(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=user_agent,
    )
    session.add(rt)

    # Update last login
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
    )


# --- Refresh ---

@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    """
    Intercambia un refresh_token válido por un nuevo par access + refresh.
    El refresh token anterior se revoca (rotación).
    """
    token_h = hash_token(body.refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_h)
    rt = session.exec(stmt).first()

    if not rt or rt.revoked or rt.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revocar el token usado
    rt.revoked = True
    session.add(rt)

    # Buscar usuario
    user = session.get(User, rt.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Nuevo par
    access_token = create_access_token(data={"sub": user.email})
    raw_refresh, new_hash, expires_at = create_refresh_token()
    new_rt = RefreshToken(
        token_hash=new_hash,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(new_rt)
    session.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
    )


# --- Logout ---

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    session: Session = Depends(get_session),
):
    """Revoca el refresh token actual."""
    token_h = hash_token(body.refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_h)
    rt = session.exec(stmt).first()
    if rt:
        rt.revoked = True
        session.add(rt)
        session.commit()


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Revoca TODOS los refresh tokens del usuario actual."""
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False,  # noqa: E712
    )
    tokens = session.exec(stmt).all()
    for rt in tokens:
        rt.revoked = True
        session.add(rt)
    session.commit()


# --- Me ---

@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: UserRead = Depends(get_current_active_user),
):
    """Retorna información del usuario autenticado."""
    return current_user


# --- Email verification ---

@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def resend_verification_email(
    body: ResendVerificationRequest,
    session: Session = Depends(get_session),
):
    """Reenvía email de verificación."""
    user = user_service.get_user_by_email(session, body.email)
    if not user:
        # No revelar si el email existe
        return {"message": "Si el email está registrado, se envió un correo de verificación"}

    if user.is_verified:
        return {"message": "El email ya está verificado"}

    await _send_verification_email(user.email, user.name)
    return {"message": "Si el email está registrado, se envió un correo de verificación"}


@router.get("/verify-email/{token}")
async def verify_email(
    token: str,
    session: Session = Depends(get_session),
):
    """Confirma verificación de email vía token JWT."""
    email = verify_purpose_token(token, "verify")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido o expirado",
        )

    user = user_service.get_user_by_email(session, email)
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")

    if user.is_verified:
        return {"message": "Email ya verificado"}

    user.is_verified = True
    session.add(user)
    session.commit()
    return {"message": "Email verificado exitosamente"}


# --- Password reset ---

@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    session: Session = Depends(get_session),
):
    """Envía email con link de reset de contraseña."""
    user = user_service.get_user_by_email(session, body.email)
    # Siempre retornar el mismo mensaje para no revelar si el email existe
    if user and user.provider == "local":
        await _send_password_reset_email(user.email, user.name)
    return {"message": "Si el email está registrado, se envió un correo de recuperación"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    session: Session = Depends(get_session),
):
    """Cambia la contraseña usando un token de reset válido."""
    email = verify_purpose_token(body.token, "reset")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de reset inválido o expirado",
        )

    user = user_service.get_user_by_email(session, email)
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")

    user.hashed_password = get_password_hash(body.new_password)
    session.add(user)

    # Revocar todos los refresh tokens (forzar re-login)
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,  # noqa: E712
    )
    for rt in session.exec(stmt).all():
        rt.revoked = True
        session.add(rt)

    session.commit()
    return {"message": "Contraseña actualizada exitosamente"}


# --- Accept invitation ---

@router.post("/accept-invitation/{token}")
async def accept_invitation(
    token: str,
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Acepta una invitación a una organización."""
    membership = invitation_service.accept_invitation(session, token, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitación inválida, expirada o ya aceptada",
        )
    return {"message": "Invitación aceptada", "organization_id": str(membership.organization_id)}


# --- Helpers ---

async def _send_verification_email(email: str, name: Optional[str]) -> None:
    """Envía email de verificación via queue (o directo si Redis no está)."""
    try:
        from app.services.email_service import email_service
        token = create_verification_token(email)
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        await email_service.send_verification_email(email, name or email, verification_url)
    except Exception as e:
        logger.warning(f"No se pudo enviar email de verificación: {e}")


async def _send_password_reset_email(email: str, name: Optional[str]) -> None:
    """Envía email de reset via queue (o directo si Redis no está)."""
    try:
        from app.services.email_service import email_service
        token = create_password_reset_token(email)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        await email_service.send_password_reset_email(email, name or email, reset_url)
    except Exception as e:
        logger.warning(f"No se pudo enviar email de reset: {e}")
