"""
Servicio de billing — orquesta pasarela de pago + modelo de suscripción + historial de pagos.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, func, col

from app.models.subscription import (
    Subscription, SubscriptionStatus,
    PlanTier, PaymentGatewayType, PLAN_FEATURES,
)
from app.models.payment import Payment, PaymentStatus
from app.services.billing import get_gateway

logger = logging.getLogger(__name__)


class BillingService:
    """Operaciones de billing: checkout, cambio de plan, cancelación, pagos, uso."""

    # ---- Subscription queries ----

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
        if plan == PlanTier.free:
            raise ValueError("No se necesita checkout para el plan free")

        if plan not in [t.value for t in PlanTier]:
            raise ValueError(f"Plan no válido: {plan}")

        sub = self.get_or_create_subscription(db, organization_id)
        gateway = get_gateway(gateway_name)

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

    # ---- Cambio de plan ----

    async def change_plan(
        self, db: Session, organization_id: UUID, new_plan: str,
    ) -> Subscription:
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
        sub = self.get_subscription(db, organization_id)
        if not sub:
            raise ValueError("No existe suscripción para esta organización")

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
        """Procesa webhook de pasarela, actualiza suscripción y registra pagos."""
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

        elif event.type == "payment.success":
            sub = self._find_subscription_by_gateway(db, event.subscription_id)
            if sub:
                # Registrar pago exitoso
                self._record_payment(
                    db,
                    organization_id=sub.organization_id,
                    subscription_id=sub.id,
                    gateway=gateway_name,
                    gateway_payment_id=event.raw.get("payment_id") if event.raw else None,
                    amount=event.raw.get("amount", 0) if event.raw else 0,
                    currency=event.raw.get("currency", "usd") if event.raw else "usd",
                    status=PaymentStatus.succeeded,
                    description=f"Pago de suscripción - Plan {sub.plan}",
                )
                result["processed"] = True
                result["payment_recorded"] = True

        elif event.type == "payment.failed":
            sub = self._find_subscription_by_gateway(db, event.subscription_id)
            if sub:
                sub.status = SubscriptionStatus.past_due
                sub.updated_at = datetime.utcnow()
                db.add(sub)
                db.commit()
                # Registrar pago fallido
                self._record_payment(
                    db,
                    organization_id=sub.organization_id,
                    subscription_id=sub.id,
                    gateway=gateway_name,
                    gateway_payment_id=event.raw.get("payment_id") if event.raw else None,
                    amount=event.raw.get("amount", 0) if event.raw else 0,
                    currency=event.raw.get("currency", "usd") if event.raw else "usd",
                    status=PaymentStatus.failed,
                    description=f"Pago fallido - Plan {sub.plan}",
                )
                result["processed"] = True
                result["payment_recorded"] = True

        return result

    # ---- Payments (dashboard) ----

    def _record_payment(
        self, db: Session, *,
        organization_id: UUID,
        subscription_id: UUID,
        gateway: str,
        gateway_payment_id: Optional[str],
        amount: int,
        currency: str,
        status: str,
        description: Optional[str],
    ) -> Payment:
        """Registra un pago en la BD."""
        payment = Payment(
            organization_id=organization_id,
            subscription_id=subscription_id,
            gateway=gateway,
            gateway_payment_id=gateway_payment_id,
            amount=amount,
            currency=currency,
            status=status,
            description=description,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        logger.info(f"Payment recorded: {status} ${amount/100:.2f} for org {organization_id}")
        return payment

    def get_payments(
        self, db: Session, organization_id: UUID,
        *, limit: int = 20, offset: int = 0,
    ) -> list[Payment]:
        """Historial de pagos de una org, más reciente primero."""
        statement = (
            select(Payment)
            .where(Payment.organization_id == organization_id)
            .order_by(col(Payment.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.exec(statement).all())

    def get_payments_count(self, db: Session, organization_id: UUID) -> int:
        """Total de pagos de una org."""
        statement = select(func.count()).select_from(Payment).where(
            Payment.organization_id == organization_id
        )
        return db.exec(statement).one()

    def get_payment_by_id(
        self, db: Session, payment_id: UUID, organization_id: UUID,
    ) -> Optional[Payment]:
        """Obtiene un pago por ID, verificando que pertenece a la org."""
        statement = select(Payment).where(
            Payment.id == payment_id,
            Payment.organization_id == organization_id,
        )
        return db.exec(statement).first()

    def create_payment(self, db: Session, **kwargs) -> Payment:
        """Crea un pago manualmente (para tests o admin)."""
        return self._record_payment(db, **kwargs)

    # ---- Usage (dashboard) ----

    def get_usage(self, db: Session, organization_id: UUID) -> dict:
        """Calcula uso actual vs límites del plan."""
        from app.models.organization import Membership

        sub = self.get_or_create_subscription(db, organization_id)
        features = self.get_plan_features(sub.plan)

        # Contar miembros activos
        member_count = db.exec(
            select(func.count()).select_from(Membership).where(
                Membership.organization_id == organization_id,
                Membership.is_active == True,
            )
        ).one()

        max_members = features.get("max_members")  # None = ilimitado

        return {
            "plan": sub.plan,
            "status": sub.status,
            "members": {
                "current": member_count,
                "max": max_members,
                "percentage": round(member_count / max_members * 100, 1) if max_members else 0,
                "unlimited": max_members is None,
            },
            "storage": {
                "current_mb": 0,  # TODO: calcular cuando haya media con org_id
                "max_mb": features.get("max_storage_mb"),
                "percentage": 0,
                "unlimited": features.get("max_storage_mb") is None,
            },
            "features": features.get("features", []),
        }

    # ---- Utilidades ----

    def get_plan_features(self, plan: str) -> dict:
        try:
            tier = PlanTier(plan)
        except ValueError:
            return {}
        return PLAN_FEATURES.get(tier, {})

    def _find_subscription_by_gateway(
        self, db: Session, gateway_subscription_id: Optional[str],
    ) -> Optional[Subscription]:
        if not gateway_subscription_id:
            return None
        statement = select(Subscription).where(
            Subscription.gateway_subscription_id == gateway_subscription_id
        )
        return db.exec(statement).first()


billing_service = BillingService()
