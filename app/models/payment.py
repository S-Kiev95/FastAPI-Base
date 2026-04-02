"""
Modelo de pagos — historial de transacciones registradas desde webhooks.
Cada Payment pertenece a una Organization y a una Subscription.
"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel


class PaymentStatus(str, Enum):
    """Estados posibles de un pago."""
    succeeded = "succeeded"
    failed = "failed"
    pending = "pending"
    refunded = "refunded"


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", index=True)
    subscription_id: Optional[uuid.UUID] = Field(default=None, foreign_key="subscriptions.id", index=True)
    gateway: str  # "stripe" | "mercadopago"
    gateway_payment_id: Optional[str] = Field(default=None, index=True)
    amount: int  # Monto en centavos
    currency: str = Field(default="usd")
    status: str = Field(default=PaymentStatus.pending)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Schemas ---

class PaymentRead(SQLModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    subscription_id: Optional[uuid.UUID]
    gateway: str
    gateway_payment_id: Optional[str]
    amount: int
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime


class PaymentCreate(SQLModel):
    organization_id: uuid.UUID
    subscription_id: Optional[uuid.UUID] = None
    gateway: str
    gateway_payment_id: Optional[str] = None
    amount: int
    currency: str = "usd"
    status: str = PaymentStatus.succeeded
    description: Optional[str] = None
