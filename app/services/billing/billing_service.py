"""
Servicio de billing — orquesta pasarela de pago + modelo de suscripción.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from app.models.subscription import (
    Subscription, SubscriptionCreate, SubscriptionStatus,
    PlanTier, PaymentGatewayType, PLAN_FEATURES,
)
from app.services.billing import get_gateway

logger = logging.getLogger(__name__)


class BillingService:
    """Operaciones de billing: checkout, cambio de plan, cancelación."""

    # ---- Queries ----

    def get_subscription(self, db: Session, organization_id: UUID) -> Optional[Subscription]:
        """Obtiene la suscripción de una organización."""
        statement = select(Subscription).where(
            Subscription.organization_id == organization_id
        )
        return db.exec(statement).first()

    def get_or_create_subscription(self, db: Session, organization_id: UUID) -> Subscription:
        """Obtiene suscripción existente o crea una free por defecto."""
        sub = self.get_subscription(db, organization_id)
        if sub:
            return sub

        sub = Subscription(
            organization_id=organization_id,
            plan=PlanTier.free,
            status=SubscriptionStatus.active,
            gateway=PaymentGatewayType.none,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        logger.info(f"Created free subscription for org {organization_id}")
        return sub

    # ---- Checkout ----

    async def create_checkout(
        self,
        db: Session,
        organization_id: UUID,
        plan: str,
        gateway_name: str,
        email: str,
        org_name: str,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        """
        Crea sesión de checkout en la pasarela.
        Retorna {checkout_url, subscription_id}.
        """
        if plan == PlanTier.free:
            raise ValueError("No se necesita checkout para el plan free")

        if plan not in [t.value for t in PlanTier]:
            raise ValueError(f"Plan no válido: {plan}")

        sub = self.get_or_create_subscription(db, organization_id)
        gateway = get_gateway(gateway_name)

        # Crear o reusar customer en la pasarela
        if not sub.gateway_customer_id or sub.gateway != gateway_name:
            customer_id = await gateway.create_customer(
                email=email, name=org_name,
                metadata={"organization_id": str(organization_id)},
            )
            sub.gateway_customer_id = customer_id
            sub.gateway = gateway_name

        checkout_url = await gateway.create_checkout_url(
            customer_id=sub.gateway_customer_id,
            plan=plan,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        sub.updated_at = datetime.utcnow()
        db.add(sub)
        db.commit()

        return {"checkout_url": checkout_url, "subscription_id": str(sub.id)}

    # ---- Cambio de plan (directo, sin checkout) ----

    async def change_plan(
        self, db: Session, organization_id: UUID, new_plan: str,
    ) -> Subscription:
        """Cambia el plan de una suscripción (para upgrades/downgrades internos)."""
        sub = self.get_or_create_subscription(db, organization_id)
        old_plan = sub.plan
        sub.plan = new_plan
        sub.status = SubscriptionStatus.active
        sub.updated_at = datetime.utcnow()
        db.add(sub)
        db.commit()
        db.refresh(sub)
        logger.info(f"Plan changed for org {organization_id}: {old_plan} -> {new_plan}")
        return sub

    # ---- Cancelación ----

    async def cancel(self, db: Session, organization_id: UUID) -> Subscription:
        """Cancela la suscripción activa."""
        sub = self.get_subscription(db, organization_id)
        if not sub:
            raise ValueError("No existe suscripción para esta organización")

        # Si hay suscripción en pasarela, cancelar allá también
        if sub.gateway_subscription_id and sub.gateway != PaymentGatewayType.none:
            gateway = get_gateway(sub.gateway)
            await gateway.cancel_subscription(sub.gateway_subscription_id)

        sub.status = SubscriptionStatus.cancelled
        sub.cancelled_at = datetime.utcnow()
        sub.updated_at = datetime.utcnow()
        db.add(sub)
        db.commit()
        db.refresh(sub)
        logger.info(f"Subscription cancelled for org {organization_id}")
        return sub

    # ---- Webhook processing ----

    async def process_webhook(
        self, db: Session, gateway_name: str, payload: bytes, signature: str,
    ) -> dict:
        """Procesa webhook de pasarela y actualiza suscripción local."""
        gateway = get_gateway(gateway_name)
        event = await gateway.handle_webhook(payload, signature)

        result = {"event_type": event.type, "processed": False}

        if event.type in ("subscription.created", "subscription.updated"):
            sub = self._find_subscription_by_gateway(db, event.subscription_id)
            if sub:
                sub.status = event.status or SubscriptionStatus.active
                if event.plan:
                    sub.plan = event.plan
                sub.updated_at = datetime.utcnow()
                db.add(sub)
                db.commit()
                result["processed"] = True

        elif event.type == "subscription.cancelled":
            sub = self._find_subscription_by_gateway(db, event.subscription_id)
            if sub:
                sub.status = SubscriptionStatus.cancelled
                sub.cancelled_at = datetime.utcnow()
                sub.updated_at = datetime.utcnow()
                db.add(sub)
                db.commit()
                result["processed"] = True

        elif event.type == "payment.failed":
            sub = self._find_subscription_by_gateway(db, event.subscription_id)
            if sub:
                sub.status = SubscriptionStatus.past_due
                sub.updated_at = datetime.utcnow()
                db.add(sub)
                db.commit()
                result["processed"] = True

        return result

    # ---- Utilidades ----

    def get_plan_features(self, plan: str) -> dict:
        """Retorna features del plan."""
        try:
            tier = PlanTier(plan)
        except ValueError:
            return {}
        return PLAN_FEATURES.get(tier, {})

    def _find_subscription_by_gateway(
        self, db: Session, gateway_subscription_id: Optional[str],
    ) -> Optional[Subscription]:
        """Busca suscripción por ID de la pasarela."""
        if not gateway_subscription_id:
            return None
        statement = select(Subscription).where(
            Subscription.gateway_subscription_id == gateway_subscription_id
        )
        return db.exec(statement).first()


billing_service = BillingService()
