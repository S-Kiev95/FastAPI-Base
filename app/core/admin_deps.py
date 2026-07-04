"""
Dependencias de autenticación para el admin panel.
Requiere is_superadmin=True en el modelo User.
"""
from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.core.dependencies import get_current_active_user
from app.models.user import UserRead, User


async def get_current_superadmin(
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
) -> User:
    """
    Verifica que el usuario actual sea superadmin.
    Retorna el User completo (no UserRead) para acceso a is_superadmin.

    Uso:
        @router.get("/api/admin/something")
        async def admin_endpoint(admin: User = Depends(get_current_superadmin)):
            ...
    """
    from sqlmodel import select
    user = session.exec(select(User).where(User.id == current_user.id)).first()

    if not user or not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requiere rol superadmin",
        )
    return user
