"""
Billing package — factory para obtener la pasarela de pago activa.
"""
from app.config import settings
from app.models.subscription import PaymentGatewayType
from app.services.billing.gateway import PaymentGateway
from app.services.billing.stripe_gateway import StripeGateway
from app.services.billing.mercadopago_gateway import MercadoPagoGateway
from app.services.billing.polar_gateway import PolarGateway


def get_gateway(provider: str | None = None) -> PaymentGateway:
    """
    Factory que retorna la pasarela de pago según configuración.

    Args:
        provider: Forzar pasarela ("stripe" | "mercadopago" | "polar"). Si None, usa settings.
    """
    provider = provider or settings.ACTIVE_PAYMENT_GATEWAY

    if provider == PaymentGatewayType.stripe:
        return StripeGateway(
            secret_key=settings.STRIPE_SECRET_KEY,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    elif provider == PaymentGatewayType.mercadopago:
        return MercadoPagoGateway(
            access_token=settings.MERCADOPAGO_ACCESS_TOKEN,
            webhook_secret=settings.MERCADOPAGO_WEBHOOK_SECRET,
        )
    elif provider == PaymentGatewayType.polar:
        return PolarGateway(
            access_token=settings.POLAR_ACCESS_TOKEN,
            webhook_secret=settings.POLAR_WEBHOOK_SECRET,
        )
    else:
        raise ValueError(f"Gateway desconocido: {provider}")
