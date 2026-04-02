"""
Stub de MercadoPago Gateway.
Implementación placeholder — retorna datos simulados.
Para producción: reemplazar con llamadas reales a la API de MercadoPago.
"""
import logging
from typing import Optional

from app.models.subscription import WebhookEvent
from app.services.billing.gateway import PaymentGateway

logger = logging.getLogger(__name__)


class MercadoPagoGateway(PaymentGateway):
    """Stub de MercadoPago. Simula operaciones sin llamar a la API real."""

    def __init__(self, access_token: str, webhook_secret: str):
        self.access_token = access_token
        self.webhook_secret = webhook_secret
        self.base_url = "https://api.mercadopago.com"
        logger.info("MercadoPagoGateway initialized (stub mode)")

    async def create_customer(self, email: str, name: str, metadata: Optional[dict] = None) -> str:
        logger.info(f"[STUB] MercadoPago create_customer: {email}")
        return f"mp_cus_stub_{email.split('@')[0]}"

    async def create_subscription(self, customer_id: str, plan: str) -> dict:
        logger.info(f"[STUB] MercadoPago create_subscription: {customer_id} -> {plan}")
        return {
            "subscription_id": f"mp_sub_stub_{plan}",
            "status": "active",
            "current_period_end": None,
        }

    async def cancel_subscription(self, subscription_id: str) -> bool:
        logger.info(f"[STUB] MercadoPago cancel_subscription: {subscription_id}")
        return True

    async def create_checkout_url(
        self, customer_id: str, plan: str, success_url: str, cancel_url: str,
    ) -> str:
        logger.info(f"[STUB] MercadoPago create_checkout_url: {customer_id} -> {plan}")
        return f"https://www.mercadopago.com/stub/checkout?customer={customer_id}&plan={plan}"

    async def handle_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        logger.info("[STUB] MercadoPago handle_webhook")
        # En producción: verificar HMAC-SHA256 con x-signature header
        return WebhookEvent(
            type="webhook.stub",
            customer_id=None,
            subscription_id=None,
        )

    async def get_subscription_status(self, subscription_id: str) -> dict:
        logger.info(f"[STUB] MercadoPago get_subscription_status: {subscription_id}")
        return {
            "subscription_id": subscription_id,
            "status": "active",
            "plan": "stub",
        }
