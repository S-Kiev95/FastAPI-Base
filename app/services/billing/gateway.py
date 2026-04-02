"""
Interfaz abstracta de pasarela de pago.
Todas las implementaciones (Stripe, MercadoPago, etc.) deben heredar de PaymentGateway.
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.models.subscription import WebhookEvent


class PaymentGateway(ABC):
    """Contrato que deben cumplir todas las pasarelas de pago."""

    @abstractmethod
    async def create_customer(self, email: str, name: str, metadata: Optional[dict] = None) -> str:
        """Crea un cliente en la pasarela. Retorna customer_id externo."""
        ...

    @abstractmethod
    async def create_subscription(self, customer_id: str, plan: str) -> dict:
        """Crea suscripción. Retorna {subscription_id, status, current_period_end}."""
        ...

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancela suscripción. Retorna True si se canceló correctamente."""
        ...

    @abstractmethod
    async def create_checkout_url(self, customer_id: str, plan: str, success_url: str, cancel_url: str) -> str:
        """Genera URL de checkout hosted. Retorna la URL."""
        ...

    @abstractmethod
    async def handle_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        """Verifica firma y retorna evento normalizado."""
        ...

    @abstractmethod
    async def get_subscription_status(self, subscription_id: str) -> dict:
        """Consulta estado actual de la suscripción en la pasarela."""
        ...
