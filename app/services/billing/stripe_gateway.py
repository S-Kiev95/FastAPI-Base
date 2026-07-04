"""
Stub de Stripe Gateway.
Implementación placeholder — retorna datos simulados.
Para producción: reemplazar con llamadas reales a stripe SDK.
"""
import logging
from typing import Optional

from app.models.subscription import WebhookEvent, PlanTier
from app.services.billing.gateway import PaymentGateway

logger = logging.getLogger(__name__)


# Mapeo de planes internos a price IDs de Stripe (configurar en producción)
STRIPE_PRICE_MAP = {
    PlanTier.starter: "price_starter_placeholder",
    PlanTier.pro: "price_pro_placeholder",
    PlanTier.enterprise: "price_enterprise_placeholder",
}


class StripeGateway(PaymentGateway):
    """Stub de Stripe. Simula operaciones sin llamar a la API real."""

    def __init__(self, secret_key: str, webhook_secret: str):
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
        logger.info("StripeGateway initialized (stub mode)")

    async def create_customer(self, email: str, name: str, metadata: Optional[dict] = None) -> str:
        logger.info(f"[STUB] Stripe create_customer: {email}")
        return f"cus_stub_{email.split('@')[0]}"

    async def create_subscription(self, customer_id: str, plan: str) -> dict:
        logger.info(f"[STUB] Stripe create_subscription: {customer_id} -> {plan}")
        return {
            "subscription_id": f"sub_stub_{plan}",
            "status": "active",
            "current_period_end": None,
        }

    async def cancel_subscription(self, subscription_id: str) -> bool:
        logger.info(f"[STUB] Stripe cancel_subscription: {subscription_id}")
        return True

    async def create_checkout_url(
        self, customer_id: str, plan: str, success_url: str, cancel_url: str,
    ) -> str:
        logger.info(f"[STUB] Stripe create_checkout_url: {customer_id} -> {plan}")
        return f"https://checkout.stripe.com/stub?customer={customer_id}&plan={plan}"

    async def handle_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        logger.info("[STUB] Stripe handle_webhook")
        # En producción: stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
        return WebhookEvent(
            type="webhook.stub",
            customer_id=None,
            subscription_id=None,
        )

    async def get_subscription_status(self, subscription_id: str) -> dict:
        logger.info(f"[STUB] Stripe get_subscription_status: {subscription_id}")
        return {
            "subscription_id": subscription_id,
            "status": "active",
            "plan": "stub",
        }
