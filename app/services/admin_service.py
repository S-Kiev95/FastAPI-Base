"""
Servicio de admin — consultas agregadas para el panel de administración global.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, func, col

from app.models.user import User
from app.models.organization import Organization, Membership
from app.models.subscription import Subscription, PlanTier, SubscriptionStatus, PLAN_FEATURES
from app.models.payment import Payment

logger = logging.getLogger(__name__)


class AdminService:
    """Operaciones de lectura y gestión global para superadmins."""

    # ---- Dashboard KPIs ----

    def get_dashboard_stats(self, db: Session) -> dict:
        """KPIs principales del dashboard admin."""
        total_orgs = db.exec(
            select(func.count()).select_from(Organization).where(
                Organization.is_system == False
            )
        ).one()

        active_orgs = db.exec(
            select(func.count()).select_from(Organization).where(
                Organization.is_active == True,
                Organization.is_system == False,
            )
        ).one()

        total_users = db.exec(select(func.count()).select_from(User)).one()

        active_subs = db.exec(
            select(func.count()).select_from(Subscription).where(
                Subscription.status == SubscriptionStatus.active
            )
        ).one()

        # MRR estimado: sumar precio mensual de suscripciones activas
        mrr = 0
        active_sub_list = db.exec(
            select(Subscription).where(Subscription.status == SubscriptionStatus.active)
        ).all()
        for sub in active_sub_list:
            try:
                tier = PlanTier(sub.plan)
                price = PLAN_FEATURES.get(tier, {}).get("price_monthly", 0)
                if price:
                    mrr += price
            except ValueError:
                pass

        # Orgs nuevas últimos 30 días
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_orgs_30d = db.exec(
            select(func.count()).select_from(Organization).where(
                Organization.created_at >= thirty_days_ago,
                Organization.is_system == False,
            )
        ).one()

        return {
            "total_organizations": total_orgs,
            "active_organizations": active_orgs,
            "total_users": total_users,
            "active_subscriptions": active_subs,
            "mrr": mrr,
            "new_organizations_30d": new_orgs_30d,
        }

    # ---- Organizations ----

    def list_organizations(
        self, db: Session, *, limit: int = 50, offset: int = 0,
        plan: Optional[str] = None, is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> list[Organization]:
        """Lista todas las organizaciones con filtros opcionales."""
        stmt = select(Organization).where(Organization.is_system == False)

        if plan:
            stmt = stmt.where(Organization.plan == plan)
        if is_active is not None:
            stmt = stmt.where(Organization.is_active == is_active)
        if search:
            stmt = stmt.where(
                Organization.name.ilike(f"%{search}%") | Organization.slug.ilike(f"%{search}%")
            )

        stmt = stmt.order_by(col(Organization.created_at).desc()).offset(offset).limit(limit)
        return list(db.exec(stmt).all())

    def count_organizations(
        self, db: Session, *,
        plan: Optional[str] = None, is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(Organization).where(
            Organization.is_system == False
        )
        if plan:
            stmt = stmt.where(Organization.plan == plan)
        if is_active is not None:
            stmt = stmt.where(Organization.is_active == is_active)
        if search:
            stmt = stmt.where(
                Organization.name.ilike(f"%{search}%") | Organization.slug.ilike(f"%{search}%")
            )
        return db.exec(stmt).one()

    def get_organization(self, db: Session, org_id: UUID) -> Optional[Organization]:
        return db.get(Organization, org_id)

    def toggle_organization_active(self, db: Session, org_id: UUID, is_active: bool) -> Organization:
        org = db.get(Organization, org_id)
        if not org:
            raise ValueError(f"Organización {org_id} no encontrada")
        org.is_active = is_active
        org.updated_at = datetime.utcnow()
        db.add(org)
        db.commit()
        db.refresh(org)
        return org

    # ---- Users ----

    def list_users(
        self, db: Session, *, limit: int = 50, offset: int = 0,
        is_active: Optional[bool] = None, search: Optional[str] = None,
    ) -> list[User]:
        stmt = select(User)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if search:
            stmt = stmt.where(
                User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%")
            )
        stmt = stmt.order_by(col(User.created_at).desc()).offset(offset).limit(limit)
        return list(db.exec(stmt).all())

    def count_users(
        self, db: Session, *,
        is_active: Optional[bool] = None, search: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(User)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if search:
            stmt = stmt.where(
                User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%")
            )
        return db.exec(stmt).one()

    def toggle_user_active(self, db: Session, user_id: int, is_active: bool) -> User:
        user = db.get(User, user_id)
        if not user:
            raise ValueError(f"Usuario {user_id} no encontrado")
        user.is_active = is_active
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ---- Subscriptions ----

    def list_subscriptions(
        self, db: Session, *, limit: int = 50, offset: int = 0,
        plan: Optional[str] = None, status: Optional[str] = None,
    ) -> list[Subscription]:
        stmt = select(Subscription)
        if plan:
            stmt = stmt.where(Subscription.plan == plan)
        if status:
            stmt = stmt.where(Subscription.status == status)
        stmt = stmt.order_by(col(Subscription.created_at).desc()).offset(offset).limit(limit)
        return list(db.exec(stmt).all())

    def count_subscriptions(
        self, db: Session, *,
        plan: Optional[str] = None, status: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(Subscription)
        if plan:
            stmt = stmt.where(Subscription.plan == plan)
        if status:
            stmt = stmt.where(Subscription.status == status)
        return db.exec(stmt).one()

    def subscription_stats(self, db: Session) -> dict:
        """Conteo de suscripciones por estado."""
        result = {}
        for s in SubscriptionStatus:
            count = db.exec(
                select(func.count()).select_from(Subscription).where(
                    Subscription.status == s.value
                )
            ).one()
            result[s.value] = count
        return result

    # ---- Payments ----

    def list_payments(
        self, db: Session, *, limit: int = 50, offset: int = 0,
        status: Optional[str] = None,
    ) -> list[Payment]:
        stmt = select(Payment)
        if status:
            stmt = stmt.where(Payment.status == status)
        stmt = stmt.order_by(col(Payment.created_at).desc()).offset(offset).limit(limit)
        return list(db.exec(stmt).all())

    def count_payments(self, db: Session, *, status: Optional[str] = None) -> int:
        stmt = select(func.count()).select_from(Payment)
        if status:
            stmt = stmt.where(Payment.status == status)
        return db.exec(stmt).one()

    # ---- Impersonate ----

    def get_user_for_impersonate(self, db: Session, user_id: int) -> Optional[User]:
        """Obtiene un usuario para generar token de impersonación."""
        user = db.get(User, user_id)
        if not user or not user.is_active:
            return None
        return user

    # ---- Metrics ----

    def get_plan_distribution(self, db: Session) -> dict:
        """Distribución de organizaciones por plan."""
        result = {}
        for tier in PlanTier:
            count = db.exec(
                select(func.count()).select_from(Subscription).where(
                    Subscription.plan == tier.value
                )
            ).one()
            result[tier.value] = count
        return result


admin_service = AdminService()
