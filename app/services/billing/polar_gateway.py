"""
Stub de Polar.sh Gateway.
Implementación placeholder — retorna datos simulados.
Para producción: usar polar-python SDK o API REST (api.polar.sh/v1).

Polar usa Standard Webhooks (HMAC) para verificación de firmas.
Headers: webhook-id, webhook-timestamp, webhook-signature.
Docs: https://polar.sh/docs/api-reference/introduction
"""
import logging
from typing import Optional

from app.models.subscription import WebhookEvent
from app.services.billing.gateway import PaymentGateway

logger = logging.getLogger(__name__)


class PolarGateway(PaymentGateway):
    """Stub de Polar.sh. Simula operaciones sin llamar a la API real."""

    def __init__(self, access_token: str, webhook_secret: str):
        self.access_token = access_token
        self.webhook_secret = webhook_secret
        self.base_url = "https://api.polar.sh/v1"
        logger.info("PolarGateway initialized (stub mode)")

    async def create_customer(self, email: str, name: str, metadata: Optional[dict] = None) -> str:
        # POST /v1/customers
        logger.info(f"[STUB] Polar create_customer: {email}")
        return f"polar_cus_stub_{email.split('@')[0]}"

    async def create_subscription(self, customer_id: str, plan: str) -> dict:
        # POST /v1/subscriptions
        logger.info(f"[STUB] Polar create_subscription: {customer_id} -> {plan}")
        return {
            "subscription_id": f"polar_sub_stub_{plan}",
            "status": "active",
            "current_period_end": None,
        }

    async def cancel_subscription(self, subscription_id: str) -> bool:
        # DELETE /v1/subscriptions/{id}
        logger.info(f"[STUB] Polar cancel_subscription: {subscription_id}")
        return True

    async def create_checkout_url(
        self, customer_id: str, plan: str, success_url: str, cancel_url: str,
    ) -> str:
        # POST /v1/checkouts
        logger.info(f"[STUB] Polar create_checkout_url: {customer_id} -> {plan}")
        return f"https://polar.sh/checkout/stub?customer={customer_id}&plan={plan}"

    async def handle_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        # En producción: verificar Standard Webhooks HMAC con webhook-signature header
        logger.info("[STUB] Polar handle_webhook")
        return WebhookEvent(
            type="webhook.stub",
            customer_id=None,
            subscription_id=None,
        )

    async def get_subscription_status(self, subscription_id: str) -> dict:
        # GET /v1/subscriptions/{id}
        logger.info(f"[STUB] Polar get_subscription_status: {subscription_id}")
        return {
            "subscription_id": subscription_id,
            "status": "active",
            "plan": "stub",
        }
