"""
Rutas de billing: checkout, suscripción, cancelación, webhooks, planes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.database import get_session
from app.core.dependencies import get_current_active_user
from app.core.tenant import TenantContext, get_current_organization
from app.models.subscription import (
    SubscriptionRead, CheckoutRequest, PlanTier, PLAN_FEATURES,
)
from app.services.billing.billing_service import billing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ---- Planes disponibles ----

@router.get("/plans")
def list_plans():
    """Lista todos los planes disponibles con sus features."""
    plans = []
    for tier in PlanTier:
        features = PLAN_FEATURES.get(tier, {})
        plans.append({
            "id": tier.value,
            **features,
        })
    return plans


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    """Detalle de un plan específico."""
    features = billing_service.get_plan_features(plan_id)
    if not features:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return {"id": plan_id, **features}


# ---- Suscripción actual ----

@router.get("/subscription", response_model=SubscriptionRead)
def get_subscription(
    tenant: TenantContext = Depends(get_current_organization),
    db: Session = Depends(get_session),
):
    """Obtiene la suscripción de la organización actual."""
    sub = billing_service.get_or_create_subscription(db, tenant.organization.id)
    return sub


# ---- Checkout ----

@router.post("/checkout")
async def create_checkout(
    data: CheckoutRequest,
    tenant: TenantContext = Depends(get_current_organization),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    """
    Crea sesión de checkout en la pasarela de pago.
    Retorna URL de checkout para redirigir al usuario.
    """
    try:
        from app.config import settings
        result = await billing_service.create_checkout(
            db=db,
            organization_id=tenant.organization.id,
            plan=data.plan,
            gateway_name=data.gateway,
            email=current_user.email,
            org_name=tenant.organization.name,
            success_url=f"{settings.FRONTEND_URL}/billing/success",
            cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Cambio de plan (admin interno) ----

@router.post("/change-plan")
async def change_plan(
    data: CheckoutRequest,
    tenant: TenantContext = Depends(get_current_organization),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    """Cambia el plan de la organización (upgrade/downgrade)."""
    sub = await billing_service.change_plan(
        db=db, organization_id=tenant.organization.id, new_plan=data.plan,
    )

    # Enviar email de cambio de plan
    try:
        from app.services.email_service import email_service
        await email_service.send_plan_change_email(
            to=current_user.email,
            name=current_user.name or current_user.email,
            old_plan=sub.plan,
            new_plan=data.plan,
            effective_date=sub.updated_at.strftime("%Y-%m-%d"),
        )
    except Exception as e:
        logger.warning(f"No se pudo enviar email de cambio de plan: {e}")

    return SubscriptionRead.model_validate(sub)


# ---- Cancelación ----

@router.post("/cancel")
async def cancel_subscription(
    tenant: TenantContext = Depends(get_current_organization),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    """Cancela la suscripción de la organización."""
    try:
        sub = await billing_service.cancel(db, tenant.organization.id)
        return {"message": "Suscripción cancelada", "subscription": SubscriptionRead.model_validate(sub)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Webhooks de pasarelas ----

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_session),
):
    """Recibe webhooks de Stripe. No requiere autenticación (verificación por firma)."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        result = await billing_service.process_webhook(db, "stripe", payload, signature)
        return result
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_session),
):
    """Recibe webhooks de MercadoPago. No requiere autenticación (verificación por firma)."""
    payload = await request.body()
    signature = request.headers.get("x-signature", "")

    try:
        result = await billing_service.process_webhook(db, "mercadopago", payload, signature)
        return result
    except Exception as e:
        logger.error(f"Error processing MercadoPago webhook: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")
