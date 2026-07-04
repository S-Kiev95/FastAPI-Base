"""Tests de Fase 5: feature flags y límites por plan."""
import pytest
from unittest.mock import patch


class TestPlanFeatureDefinitions:
    """Verifica que PLAN_FEATURES incluye api_rate_limit."""

    def test_all_plans_have_rate_limit(self):
        from app.models.subscription import PlanTier, PLAN_FEATURES
        for tier in PlanTier:
            features = PLAN_FEATURES[tier]
            assert "api_rate_limit" in features, f"Plan {tier} sin api_rate_limit"

    def test_rate_limit_hierarchy(self):
        from app.models.subscription import PlanTier, PLAN_FEATURES
        free_limit = PLAN_FEATURES[PlanTier.free]["api_rate_limit"]
        starter_limit = PLAN_FEATURES[PlanTier.starter]["api_rate_limit"]
        pro_limit = PLAN_FEATURES[PlanTier.pro]["api_rate_limit"]
        assert free_limit < starter_limit < pro_limit

    def test_enterprise_unlimited_rate_limit(self):
        from app.models.subscription import PlanTier, PLAN_FEATURES
        assert PLAN_FEATURES[PlanTier.enterprise]["api_rate_limit"] is None


class TestGetPlanFeatures:
    """Tests de _get_plan_features helper."""

    def test_returns_features_for_valid_plan(self, session):
        from app.models.organization import Organization
        from app.core.plan_guards import _get_plan_features

        org = Organization(name="Guard Org", slug="guard-org", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        features = _get_plan_features(session, org.id)
        assert features["name"] == "Free"
        assert features["max_members"] == 3

    def test_returns_free_for_invalid_plan(self, session):
        from app.models.organization import Organization
        from app.models.subscription import Subscription, SubscriptionStatus, PaymentGatewayType
        from app.core.plan_guards import _get_plan_features

        org = Organization(name="Bad Plan Org", slug="bad-plan-org", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        # Crear suscripción con plan inválido
        sub = Subscription(
            organization_id=org.id,
            plan="nonexistent",
            status=SubscriptionStatus.active,
            gateway=PaymentGatewayType.none,
        )
        session.add(sub)
        session.commit()

        features = _get_plan_features(session, org.id)
        # Debería devolver features de free como fallback
        assert features["name"] == "Free"


class TestRequireFeature:
    """Tests de la dependencia require_feature."""

    def test_feature_available_passes(self, session):
        """Un feature que existe en el plan no lanza excepción."""
        from app.models.organization import Organization
        from app.core.plan_guards import _get_plan_features

        org = Organization(name="Feat Org", slug="feat-org", plan="pro")
        session.add(org)
        session.commit()
        session.refresh(org)

        # Forzar plan pro en suscripción
        from app.services.billing.billing_service import billing_service
        sub = billing_service.get_or_create_subscription(session, org.id)
        sub.plan = "pro"
        session.add(sub)
        session.commit()

        features = _get_plan_features(session, org.id)
        assert "webhooks" in features["features"]
        assert "api_access" in features["features"]

    def test_feature_not_in_plan(self, session):
        """Un feature que NO existe en el plan free."""
        from app.models.organization import Organization
        from app.core.plan_guards import _get_plan_features

        org = Organization(name="Free Org", slug="free-org-feat", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        from app.services.billing.billing_service import billing_service
        billing_service.get_or_create_subscription(session, org.id)

        features = _get_plan_features(session, org.id)
        assert "webhooks" not in features["features"]
        assert "sso" not in features["features"]
        assert "api_access" not in features["features"]

    def test_all_features_in_enterprise(self, session):
        """Enterprise tiene todos los features."""
        from app.models.organization import Organization
        from app.core.plan_guards import _get_plan_features

        org = Organization(name="Ent Org", slug="ent-org-feat", plan="enterprise")
        session.add(org)
        session.commit()
        session.refresh(org)

        from app.services.billing.billing_service import billing_service
        sub = billing_service.get_or_create_subscription(session, org.id)
        sub.plan = "enterprise"
        session.add(sub)
        session.commit()

        features = _get_plan_features(session, org.id)
        assert "webhooks" in features["features"]
        assert "sso" in features["features"]
        assert "audit_log" in features["features"]
        assert "dedicated_support" in features["features"]


class TestRequireMemberLimit:
    """Tests del guard de límite de miembros."""

    def test_under_limit_ok(self, session):
        """Con menos miembros que el límite, no hay problema."""
        from app.models.organization import Organization, Membership
        from app.models.user import User
        from app.core.plan_guards import _get_plan_features
        from app.services.billing.billing_service import billing_service
        from sqlmodel import select, func

        org = Organization(name="Limit Org", slug="limit-org", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        billing_service.get_or_create_subscription(session, org.id)

        # Agregar 1 miembro (límite free = 3)
        user = User(email="limit1@test.com", name="User1", hashed_password="x")
        session.add(user)
        session.commit()
        session.refresh(user)
        session.add(Membership(user_id=user.id, organization_id=org.id, role="member"))
        session.commit()

        count = session.exec(
            select(func.count()).select_from(Membership).where(
                Membership.organization_id == org.id,
                Membership.is_active == True,
            )
        ).one()

        features = _get_plan_features(session, org.id)
        assert count < features["max_members"]

    def test_at_limit_blocks(self, session):
        """Con miembros == max_members, el guard debería bloquear."""
        from app.models.organization import Organization, Membership
        from app.models.user import User
        from app.core.plan_guards import _get_plan_features
        from app.services.billing.billing_service import billing_service
        from sqlmodel import select, func

        org = Organization(name="Full Org", slug="full-org", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        billing_service.get_or_create_subscription(session, org.id)

        # Agregar 3 miembros (límite free = 3)
        for i in range(3):
            user = User(email=f"full{i}@test.com", name=f"User{i}", hashed_password="x")
            session.add(user)
            session.commit()
            session.refresh(user)
            session.add(Membership(user_id=user.id, organization_id=org.id, role="member"))
        session.commit()

        count = session.exec(
            select(func.count()).select_from(Membership).where(
                Membership.organization_id == org.id,
                Membership.is_active == True,
            )
        ).one()

        features = _get_plan_features(session, org.id)
        assert count >= features["max_members"]

    def test_enterprise_unlimited(self, session):
        """Enterprise no tiene límite de miembros."""
        from app.models.organization import Organization
        from app.core.plan_guards import _get_plan_features
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Ent Limit", slug="ent-limit", plan="enterprise")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        sub.plan = "enterprise"
        session.add(sub)
        session.commit()

        features = _get_plan_features(session, org.id)
        assert features["max_members"] is None  # ilimitado


class TestGetPlanRateLimit:
    """Tests del helper get_plan_rate_limit."""

    def test_free_rate_limit(self, session):
        from app.models.organization import Organization
        from app.core.plan_guards import get_plan_rate_limit
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Rate Org", slug="rate-org", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        billing_service.get_or_create_subscription(session, org.id)
        limit = get_plan_rate_limit(session, org.id)
        assert limit == 100

    def test_pro_rate_limit(self, session):
        from app.models.organization import Organization
        from app.core.plan_guards import get_plan_rate_limit
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Rate Pro", slug="rate-pro", plan="pro")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        sub.plan = "pro"
        session.add(sub)
        session.commit()

        limit = get_plan_rate_limit(session, org.id)
        assert limit == 10000

    def test_enterprise_unlimited_rate(self, session):
        from app.models.organization import Organization
        from app.core.plan_guards import get_plan_rate_limit
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Rate Ent", slug="rate-ent", plan="enterprise")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        sub.plan = "enterprise"
        session.add(sub)
        session.commit()

        limit = get_plan_rate_limit(session, org.id)
        assert limit is None  # sin límite


class TestMemberLimitIntegration:
    """Tests de integración: add_member y create_invitation bloquean con plan lleno."""

    def test_add_member_blocked_at_limit(self, client, registered_user_with_org):
        """POST /orgs/{slug}/members devuelve 402 si el plan está lleno."""
        headers = registered_user_with_org["headers"]
        org_slug = registered_user_with_org["org_slug"]

        # El user registrado ya es owner (1 miembro). Free permite 3.
        # Agregar 2 más para llegar al límite.
        for i in range(2):
            user_data = {
                "email": f"extra{i}@test.com",
                "password": "password123",
                "name": f"Extra {i}",
            }
            resp = client.post("/auth/register", json=user_data)
            assert resp.status_code == 201
            user_id = resp.json()["id"]

            # Agregar como miembro directamente
            resp = client.post(
                f"/orgs/{org_slug}/members",
                json={"user_id": user_id, "role": "member"},
                headers=headers,
            )
            assert resp.status_code == 201

        # Ahora estamos en 3 miembros (límite free). El siguiente debería dar 402.
        extra_data = {
            "email": "blocked@test.com",
            "password": "password123",
            "name": "Blocked User",
        }
        resp = client.post("/auth/register", json=extra_data)
        assert resp.status_code == 201
        blocked_id = resp.json()["id"]

        resp = client.post(
            f"/orgs/{org_slug}/members",
            json={"user_id": blocked_id, "role": "member"},
            headers=headers,
        )
        assert resp.status_code == 402
        assert "Límite de miembros" in resp.json()["detail"]
