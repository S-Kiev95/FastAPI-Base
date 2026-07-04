"""
Modelo de suscripción y planes de billing.
Cada Organization tiene una suscripción (1:1).
"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel


class PlanTier(str, Enum):
    """Niveles de plan disponibles."""
    free = "free"
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class SubscriptionStatus(str, Enum):
    """Estados posibles de una suscripción."""
    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    cancelled = "cancelled"
    incomplete = "incomplete"


class PaymentGatewayType(str, Enum):
    """Pasarelas de pago soportadas."""
    stripe = "stripe"
    mercadopago = "mercadopago"
    polar = "polar"
    none = "none"  # Para plan free sin pasarela


# --- Modelo de tabla ---

class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", unique=True, index=True)
    gateway: str = Field(default=PaymentGatewayType.none)
    gateway_customer_id: Optional[str] = Field(default=None)
    gateway_subscription_id: Optional[str] = Field(default=None)
    plan: str = Field(default=PlanTier.free)
    status: str = Field(default=SubscriptionStatus.active)
    current_period_end: Optional[datetime] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Schemas ---

class SubscriptionRead(SQLModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    gateway: str
    plan: str
    status: str
    current_period_end: Optional[datetime]
    cancelled_at: Optional[datetime]
    created_at: datetime


class SubscriptionCreate(SQLModel):
    organization_id: uuid.UUID
    plan: str = PlanTier.free
    gateway: str = PaymentGatewayType.none


class CheckoutRequest(SQLModel):
    plan: str  # PlanTier value
    gateway: str = PaymentGatewayType.stripe  # Pasarela preferida


class WebhookEvent(SQLModel):
    """Evento normalizado de webhook de pasarela."""
    type: str  # "subscription.created", "payment.success", etc.
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None
    plan: Optional[str] = None
    status: Optional[str] = None
    raw: Optional[dict] = None


# --- Definición de planes ---

PLAN_FEATURES = {
    PlanTier.free: {
        "name": "Free",
        "price_monthly": 0,
        "max_members": 3,
        "max_storage_mb": 100,
        "api_rate_limit": 100,  # requests/hora
        "features": ["basic_crud", "email_support"],
    },
    PlanTier.starter: {
        "name": "Starter",
        "price_monthly": 29,
        "max_members": 10,
        "max_storage_mb": 1000,
        "api_rate_limit": 1000,
        "features": ["basic_crud", "email_support", "api_access", "custom_branding"],
    },
    PlanTier.pro: {
        "name": "Pro",
        "price_monthly": 79,
        "max_members": 50,
        "max_storage_mb": 10000,
        "api_rate_limit": 10000,
        "features": ["basic_crud", "email_support", "api_access", "custom_branding", "webhooks", "priority_support"],
    },
    PlanTier.enterprise: {
        "name": "Enterprise",
        "price_monthly": None,  # Precio personalizado
        "max_members": None,  # Sin límite
        "max_storage_mb": None,  # Sin límite
        "api_rate_limit": None,  # Sin límite
        "features": ["basic_crud", "email_support", "api_access", "custom_branding", "webhooks", "priority_support", "sso", "audit_log", "dedicated_support"],
    },
}
