"""
Guards de plan: dependencias FastAPI para verificar features y límites por plan.
Usa PLAN_FEATURES de subscription.py como fuente de verdad.
"""
import logging
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select, func

from app.database import get_session
from app.core.tenant import TenantContext, get_current_organization
from app.models.subscription import PLAN_FEATURES, PlanTier
from app.services.billing.billing_service import billing_service

logger = logging.getLogger(__name__)


def _get_plan_features(db: Session, organization_id) -> dict:
    """Obtiene features del plan actual de la org (desde Subscription, no desde Organization.plan)."""
    sub = billing_service.get_or_create_subscription(db, organization_id)
    try:
        tier = PlanTier(sub.plan)
    except ValueError:
        return PLAN_FEATURES.get(PlanTier.free, {})
    return PLAN_FEATURES.get(tier, {})


def require_feature(feature: str):
    """
    Dependency factory que verifica que el plan de la org incluya un feature.

    Uso:
        @router.get("/some-endpoint")
        async def endpoint(
            tenant: TenantContext = Depends(require_feature("webhooks"))
        ):
            ...

    Retorna TenantContext si el feature está disponible.
    Lanza HTTP 402 si el plan no incluye el feature.
    """
    async def check(
        tenant: TenantContext = Depends(get_current_organization),
        db: Session = Depends(get_session),
    ) -> TenantContext:
        features = _get_plan_features(db, tenant.org_id)
        feature_list = features.get("features", [])

        if feature not in feature_list:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Tu plan no incluye '{feature}'. Actualizá tu suscripción.",
            )
        return tenant

    return check


def require_member_limit():
    """
    Dependency factory que verifica que la org no haya excedido max_members.

    Uso:
        @router.post("/orgs/{org_slug}/members")
        async def add_member(
            _limit_ok: TenantContext = Depends(require_member_limit()),
            tenant: TenantContext = Depends(get_current_organization),
        ):
            ...

    Lanza HTTP 402 si se alcanzó el límite de miembros del plan.
    """
    async def check(
        tenant: TenantContext = Depends(get_current_organization),
        db: Session = Depends(get_session),
    ) -> TenantContext:
        from app.models.organization import Membership

        features = _get_plan_features(db, tenant.org_id)
        max_members = features.get("max_members")

        # None = ilimitado (enterprise)
        if max_members is None:
            return tenant

        current_count = db.exec(
            select(func.count()).select_from(Membership).where(
                Membership.organization_id == tenant.org_id,
                Membership.is_active == True,
            )
        ).one()

        if current_count >= max_members:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Límite de miembros alcanzado ({current_count}/{max_members}). Actualizá tu plan.",
            )
        return tenant

    return check


def require_storage_limit():
    """
    Dependency factory que verifica que la org no haya excedido max_storage_mb.
    Actualmente retorna siempre OK porque Media no tiene organization_id todavía.

    Uso:
        @router.post("/orgs/{org_slug}/upload")
        async def upload(
            _limit_ok: TenantContext = Depends(require_storage_limit()),
        ):
            ...
    """
    async def check(
        tenant: TenantContext = Depends(get_current_organization),
        db: Session = Depends(get_session),
    ) -> TenantContext:
        features = _get_plan_features(db, tenant.org_id)
        max_storage = features.get("max_storage_mb")

        # None = ilimitado
        if max_storage is None:
            return tenant

        # TODO: calcular storage real cuando Media tenga organization_id
        current_mb = 0

        if current_mb >= max_storage:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Límite de storage alcanzado ({current_mb}/{max_storage} MB). Actualizá tu plan.",
            )
        return tenant

    return check


def get_plan_rate_limit(db: Session, organization_id) -> int:
    """
    Retorna el rate limit (requests/hora) del plan de la org.
    Útil para rate limiting dinámico por plan.
    """
    features = _get_plan_features(db, organization_id)
    return features.get("api_rate_limit", 100)
