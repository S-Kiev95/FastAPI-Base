"""
Rutas del admin panel — protegidas con is_superadmin.
Prefijo: /api/admin
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session
from typing import Optional

from app.database import get_session
from app.core.admin_deps import get_current_superadmin
from app.core.security import create_access_token
from app.models.user import User
from app.services.admin_service import admin_service

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_superadmin)],
)


# ---- Dashboard ----

@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_session)):
    """KPIs principales del admin panel."""
    return admin_service.get_dashboard_stats(db)


# ---- Organizations ----

@router.get("/organizations")
def admin_list_organizations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    plan: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
):
    """Lista todas las organizaciones con filtros."""
    items = admin_service.list_organizations(
        db, limit=limit, offset=offset, plan=plan, is_active=is_active, search=search,
    )
    total = admin_service.count_organizations(
        db, plan=plan, is_active=is_active, search=search,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/organizations/{org_id}")
def admin_get_organization(org_id: str, db: Session = Depends(get_session)):
    """Detalle de una organización."""
    from uuid import UUID
    try:
        uid = UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de organización inválido")

    org = admin_service.get_organization(db, uid)
    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    return org


@router.patch("/organizations/{org_id}/toggle-active")
def admin_toggle_org_active(
    org_id: str,
    is_active: bool = Query(...),
    db: Session = Depends(get_session),
):
    """Activa o desactiva una organización."""
    from uuid import UUID
    try:
        uid = UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de organización inválido")

    try:
        org = admin_service.toggle_organization_active(db, uid, is_active)
        return {"ok": True, "is_active": org.is_active}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---- Users ----

@router.get("/users")
def admin_list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
):
    """Lista todos los usuarios con filtros."""
    items = admin_service.list_users(
        db, limit=limit, offset=offset, is_active=is_active, search=search,
    )
    total = admin_service.count_users(db, is_active=is_active, search=search)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.patch("/users/{user_id}/toggle-active")
def admin_toggle_user_active(
    user_id: int,
    is_active: bool = Query(...),
    db: Session = Depends(get_session),
):
    """Activa o desactiva un usuario."""
    try:
        user = admin_service.toggle_user_active(db, user_id, is_active)
        return {"ok": True, "is_active": user.is_active}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---- Subscriptions ----

@router.get("/subscriptions")
def admin_list_subscriptions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    plan: Optional[str] = None,
    sub_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_session),
):
    """Lista todas las suscripciones con filtros."""
    items = admin_service.list_subscriptions(
        db, limit=limit, offset=offset, plan=plan, status=sub_status,
    )
    total = admin_service.count_subscriptions(db, plan=plan, status=sub_status)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/subscriptions/stats")
def admin_subscription_stats(db: Session = Depends(get_session)):
    """Conteo de suscripciones por estado."""
    return admin_service.subscription_stats(db)


# ---- Payments ----

@router.get("/payments")
def admin_list_payments(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pay_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_session),
):
    """Historial global de pagos."""
    items = admin_service.list_payments(db, limit=limit, offset=offset, status=pay_status)
    total = admin_service.count_payments(db, status=pay_status)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---- Metrics ----

@router.get("/metrics")
def admin_metrics(db: Session = Depends(get_session)):
    """Métricas del sistema: distribución de planes, stats generales."""
    return {
        "plan_distribution": admin_service.get_plan_distribution(db),
        "subscription_stats": admin_service.subscription_stats(db),
        "dashboard": admin_service.get_dashboard_stats(db),
    }


# ---- Impersonate ----

@router.post("/impersonate/{user_id}")
def admin_impersonate(
    user_id: int,
    db: Session = Depends(get_session),
    admin: User = Depends(get_current_superadmin),
):
    """
    Genera un access token para un usuario específico (debug/soporte).
    El admin puede iniciar sesión como cualquier usuario.
    """
    target = admin_service.get_user_for_impersonate(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o inactivo")

    token = create_access_token({"sub": target.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "impersonated_user": {
            "id": target.id,
            "email": target.email,
            "name": target.name,
        },
        "admin_email": admin.email,
    }
