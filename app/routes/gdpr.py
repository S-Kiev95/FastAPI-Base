"""
Rutas GDPR — exportación de datos y eliminación de cuenta.
Prefijo: /account
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.core.dependencies import get_current_active_user
from app.models.user import UserRead
from app.services.gdpr_service import gdpr_service
from app.services.audit_service import audit_service
from app.config import settings

router = APIRouter(
    prefix="/account",
    tags=["account"],
)


@router.get("/export")
def export_my_data(
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """
    Exporta todos los datos personales del usuario (Art. 15 GDPR).
    Retorna un JSON con perfil, membresías, API keys y audit trail.
    """
    if not settings.GDPR_EXPORT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Exportación de datos deshabilitada",
        )

    data = gdpr_service.export_user_data(session, current_user.id)

    # Audit
    audit_service.record(
        session,
        user_id=current_user.id,
        action="export",
        resource_type="users",
        resource_id=str(current_user.id),
    )

    return data


@router.post("/request-deletion")
def request_deletion(
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """
    Solicita eliminación de cuenta con período de gracia.
    La cuenta se desactiva inmediatamente y se purga tras N días.
    """
    deletion_date = gdpr_service.request_account_deletion(session, current_user.id)
    if not deletion_date:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    audit_service.record(
        session,
        user_id=current_user.id,
        action="request_deletion",
        resource_type="users",
        resource_id=str(current_user.id),
    )

    return {
        "message": f"Cuenta marcada para eliminación. Período de gracia: {settings.ACCOUNT_DELETION_GRACE_DAYS} días.",
        "deletion_date": deletion_date.isoformat(),
        "cancel_url": "/account/cancel-deletion",
    }


@router.post("/cancel-deletion")
def cancel_deletion(
    current_user: UserRead = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Cancela una solicitud de eliminación pendiente."""
    # Nota: get_current_active_user falla si is_active=False,
    # pero el usuario puede re-login con JWT aún vigente
    success = gdpr_service.cancel_account_deletion(session, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay solicitud de eliminación pendiente o el período de gracia ya expiró",
        )

    audit_service.record(
        session,
        user_id=current_user.id,
        action="cancel_deletion",
        resource_type="users",
        resource_id=str(current_user.id),
    )

    return {"message": "Solicitud de eliminación cancelada. Tu cuenta ha sido reactivada."}
