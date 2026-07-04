"""Tests de billing: modelos, gateway factory, servicio, rutas y planes."""
import pytest
from unittest.mock import patch, AsyncMock


class TestPlanDefinitions:
    """Verifica que los planes están correctamente definidos."""

    def test_all_plan_tiers_exist(self):
        from app.models.subscription import PlanTier, PLAN_FEATURES
        for tier in PlanTier:
            assert tier in PLAN_FEATURES, f"Plan {tier} no tiene features definidos"

    def test_free_plan_has_zero_price(self):
        from app.models.subscription import PlanTier, PLAN_FEATURES
        assert PLAN_FEATURES[PlanTier.free]["price_monthly"] == 0

    def test_enterprise_has_no_limits(self):
        from app.models.subscription import PlanTier, PLAN_FEATURES
        enterprise = PLAN_FEATURES[PlanTier.enterprise]
        assert enterprise["max_members"] is None
        assert enterprise["max_storage_mb"] is None

    def test_plan_hierarchy_pricing(self):
        from app.models.subscription import PlanTier, PLAN_FEATURES
        free_price = PLAN_FEATURES[PlanTier.free]["price_monthly"]
        starter_price = PLAN_FEATURES[PlanTier.starter]["price_monthly"]
        pro_price = PLAN_FEATURES[PlanTier.pro]["price_monthly"]
        assert free_price < starter_price < pro_price


class TestGatewayFactory:
    """Verifica que la factory de pasarelas funciona."""

    def test_get_stripe_gateway(self):
        from app.services.billing import get_gateway
        from app.services.billing.stripe_gateway import StripeGateway
        gw = get_gateway("stripe")
        assert isinstance(gw, StripeGateway)

    def test_get_mercadopago_gateway(self):
        from app.services.billing import get_gateway
        from app.services.billing.mercadopago_gateway import MercadoPagoGateway
        gw = get_gateway("mercadopago")
        assert isinstance(gw, MercadoPagoGateway)

    def test_get_polar_gateway(self):
        from app.services.billing import get_gateway
        from app.services.billing.polar_gateway import PolarGateway
        gw = get_gateway("polar")
        assert isinstance(gw, PolarGateway)

    def test_unknown_gateway_raises(self):
        from app.services.billing import get_gateway
        with pytest.raises(ValueError, match="Gateway desconocido"):
            get_gateway("paypal")


class TestStripeGatewayStub:
    """Verifica que los stubs de Stripe retornan datos válidos."""

    @pytest.mark.asyncio
    async def test_create_customer(self):
        from app.services.billing.stripe_gateway import StripeGateway
        gw = StripeGateway("sk_test", "whsec_test")
        customer_id = await gw.create_customer("test@test.com", "Test")
        assert customer_id.startswith("cus_stub_")

    @pytest.mark.asyncio
    async def test_create_subscription(self):
        from app.services.billing.stripe_gateway import StripeGateway
        gw = StripeGateway("sk_test", "whsec_test")
        result = await gw.create_subscription("cus_123", "pro")
        assert result["subscription_id"].startswith("sub_stub_")
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_cancel_subscription(self):
        from app.services.billing.stripe_gateway import StripeGateway
        gw = StripeGateway("sk_test", "whsec_test")
        assert await gw.cancel_subscription("sub_123") is True

    @pytest.mark.asyncio
    async def test_create_checkout_url(self):
        from app.services.billing.stripe_gateway import StripeGateway
        gw = StripeGateway("sk_test", "whsec_test")
        url = await gw.create_checkout_url("cus_123", "pro", "http://ok", "http://cancel")
        assert "checkout.stripe.com" in url

    @pytest.mark.asyncio
    async def test_handle_webhook(self):
        from app.services.billing.stripe_gateway import StripeGateway
        gw = StripeGateway("sk_test", "whsec_test")
        event = await gw.handle_webhook(b"payload", "sig")
        assert event.type == "webhook.stub"


class TestMercadoPagoGatewayStub:
    """Verifica que los stubs de MercadoPago retornan datos válidos."""

    @pytest.mark.asyncio
    async def test_create_customer(self):
        from app.services.billing.mercadopago_gateway import MercadoPagoGateway
        gw = MercadoPagoGateway("token", "secret")
        customer_id = await gw.create_customer("test@test.com", "Test")
        assert customer_id.startswith("mp_cus_stub_")

    @pytest.mark.asyncio
    async def test_create_checkout_url(self):
        from app.services.billing.mercadopago_gateway import MercadoPagoGateway
        gw = MercadoPagoGateway("token", "secret")
        url = await gw.create_checkout_url("mp_cus_123", "starter", "http://ok", "http://cancel")
        assert "mercadopago.com" in url


class TestPolarGatewayStub:
    """Verifica que los stubs de Polar.sh retornan datos válidos."""

    @pytest.mark.asyncio
    async def test_create_customer(self):
        from app.services.billing.polar_gateway import PolarGateway
        gw = PolarGateway("polar_oat_test", "whsec_test")
        customer_id = await gw.create_customer("test@test.com", "Test")
        assert customer_id.startswith("polar_cus_stub_")

    @pytest.mark.asyncio
    async def test_create_subscription(self):
        from app.services.billing.polar_gateway import PolarGateway
        gw = PolarGateway("polar_oat_test", "whsec_test")
        result = await gw.create_subscription("polar_cus_123", "pro")
        assert result["subscription_id"].startswith("polar_sub_stub_")
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_cancel_subscription(self):
        from app.services.billing.polar_gateway import PolarGateway
        gw = PolarGateway("polar_oat_test", "whsec_test")
        assert await gw.cancel_subscription("polar_sub_123") is True

    @pytest.mark.asyncio
    async def test_create_checkout_url(self):
        from app.services.billing.polar_gateway import PolarGateway
        gw = PolarGateway("polar_oat_test", "whsec_test")
        url = await gw.create_checkout_url("polar_cus_123", "pro", "http://ok", "http://cancel")
        assert "polar.sh" in url

    @pytest.mark.asyncio
    async def test_handle_webhook(self):
        from app.services.billing.polar_gateway import PolarGateway
        gw = PolarGateway("polar_oat_test", "whsec_test")
        event = await gw.handle_webhook(b"payload", "sig")
        assert event.type == "webhook.stub"


class TestBillingService:
    """Tests del servicio de billing con BD."""

    def test_get_or_create_subscription(self, session):
        """Crea suscripción free si no existe."""
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Test Org", slug="test-org", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        assert sub.plan == "free"
        assert sub.status == "active"
        assert sub.organization_id == org.id

    def test_get_or_create_returns_existing(self, session):
        """Si ya existe, retorna la existente."""
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Test Org", slug="test-org-2", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub1 = billing_service.get_or_create_subscription(session, org.id)
        sub2 = billing_service.get_or_create_subscription(session, org.id)
        assert sub1.id == sub2.id

    @pytest.mark.asyncio
    async def test_change_plan(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Test Org", slug="test-org-3", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        billing_service.get_or_create_subscription(session, org.id)
        sub = await billing_service.change_plan(session, org.id, "pro")
        assert sub.plan == "pro"
        assert sub.status == "active"

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Test Org", slug="test-org-4", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        billing_service.get_or_create_subscription(session, org.id)
        sub = await billing_service.cancel(session, org.id)
        assert sub.status == "cancelled"
        assert sub.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_raises(self, session):
        import uuid
        from app.services.billing.billing_service import billing_service

        with pytest.raises(ValueError, match="No existe suscripción"):
            await billing_service.cancel(session, uuid.uuid4())

    def test_get_plan_features(self):
        from app.services.billing.billing_service import billing_service

        features = billing_service.get_plan_features("pro")
        assert features["name"] == "Pro"
        assert features["price_monthly"] == 79

    def test_get_plan_features_invalid(self):
        from app.services.billing.billing_service import billing_service

        features = billing_service.get_plan_features("nonexistent")
        assert features == {}


class TestBillingRoutes:
    """Tests de rutas HTTP de billing."""

    def test_list_plans(self, client):
        response = client.get("/billing/plans")
        assert response.status_code == 200
        plans = response.json()
        assert len(plans) == 4
        plan_ids = [p["id"] for p in plans]
        assert "free" in plan_ids
        assert "starter" in plan_ids
        assert "pro" in plan_ids
        assert "enterprise" in plan_ids

    def test_get_plan_detail(self, client):
        response = client.get("/billing/plans/pro")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "pro"
        assert data["name"] == "Pro"
        assert data["price_monthly"] == 79

    def test_get_plan_not_found(self, client):
        response = client.get("/billing/plans/nonexistent")
        assert response.status_code == 404

    def test_get_subscription_requires_org(self, registered_user_with_org, client):
        """GET /billing/subscription requiere contexto de organización."""
        # Sin slug de org, debería fallar
        response = client.get(
            "/billing/subscription",
            headers=registered_user_with_org["headers"],
        )
        # Puede ser 403/422 dependiendo de cómo get_current_organization maneja la falta de org
        assert response.status_code in (403, 422, 400, 404)

    def test_stripe_webhook_endpoint_exists(self, client):
        """POST /billing/webhooks/stripe responde (aunque sea stub)."""
        response = client.post(
            "/billing/webhooks/stripe",
            content=b'{"test": true}',
            headers={"stripe-signature": "test_sig", "content-type": "application/json"},
        )
        assert response.status_code == 200

    def test_mercadopago_webhook_endpoint_exists(self, client):
        """POST /billing/webhooks/mercadopago responde (aunque sea stub)."""
        response = client.post(
            "/billing/webhooks/mercadopago",
            content=b'{"test": true}',
            headers={"x-signature": "test_sig", "content-type": "application/json"},
        )
        assert response.status_code == 200

    def test_polar_webhook_endpoint_exists(self, client):
        """POST /billing/webhooks/polar responde (Standard Webhooks)."""
        response = client.post(
            "/billing/webhooks/polar",
            content=b'{"test": true}',
            headers={"webhook-signature": "test_sig", "content-type": "application/json"},
        )
        assert response.status_code == 200


# ============================================================
# Fase 4.1 — Dashboard de billing: pagos, detalle, uso
# ============================================================

class TestPaymentModel:
    """Tests del modelo Payment y operaciones de servicio."""

    def test_record_payment(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Pay Org", slug="pay-org", plan="pro")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        payment = billing_service.create_payment(
            db=session,
            organization_id=org.id,
            subscription_id=sub.id,
            gateway="stripe",
            gateway_payment_id="pi_test_123",
            amount=7900,
            currency="usd",
            status="succeeded",
            description="Pago de suscripción Pro",
        )
        assert payment.amount == 7900
        assert payment.status == "succeeded"
        assert payment.gateway_payment_id == "pi_test_123"

    def test_get_payments_list(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="List Org", slug="list-org", plan="starter")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)

        # Crear 3 pagos
        for i in range(3):
            billing_service.create_payment(
                db=session,
                organization_id=org.id,
                subscription_id=sub.id,
                gateway="stripe",
                gateway_payment_id=f"pi_{i}",
                amount=2900,
                currency="usd",
                status="succeeded",
                description=f"Pago #{i}",
            )

        payments = billing_service.get_payments(session, org.id)
        assert len(payments) == 3

    def test_get_payments_count(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Count Org", slug="count-org", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        billing_service.create_payment(
            db=session, organization_id=org.id, subscription_id=sub.id,
            gateway="stripe", gateway_payment_id=None, amount=100,
            currency="usd", status="succeeded", description=None,
        )

        count = billing_service.get_payments_count(session, org.id)
        assert count == 1

    def test_get_payments_pagination(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Page Org", slug="page-org", plan="pro")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        for i in range(5):
            billing_service.create_payment(
                db=session, organization_id=org.id, subscription_id=sub.id,
                gateway="stripe", gateway_payment_id=f"pi_p{i}", amount=1000,
                currency="usd", status="succeeded", description=None,
            )

        page1 = billing_service.get_payments(session, org.id, limit=2, offset=0)
        page2 = billing_service.get_payments(session, org.id, limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    def test_get_payment_by_id(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Detail Org", slug="detail-org", plan="pro")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        payment = billing_service.create_payment(
            db=session, organization_id=org.id, subscription_id=sub.id,
            gateway="stripe", gateway_payment_id="pi_detail", amount=7900,
            currency="usd", status="succeeded", description=None,
        )

        found = billing_service.get_payment_by_id(session, payment.id, org.id)
        assert found is not None
        assert found.id == payment.id

    def test_get_payment_by_id_wrong_org(self, session):
        """Un pago de otra org no es visible."""
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org1 = Organization(name="Org A", slug="org-a", plan="pro")
        org2 = Organization(name="Org B", slug="org-b", plan="pro")
        session.add_all([org1, org2])
        session.commit()
        session.refresh(org1)
        session.refresh(org2)

        sub1 = billing_service.get_or_create_subscription(session, org1.id)
        payment = billing_service.create_payment(
            db=session, organization_id=org1.id, subscription_id=sub1.id,
            gateway="stripe", gateway_payment_id="pi_iso", amount=7900,
            currency="usd", status="succeeded", description=None,
        )

        # Org B no puede ver el pago de Org A
        found = billing_service.get_payment_by_id(session, payment.id, org2.id)
        assert found is None


class TestUsageEndpoint:
    """Tests del cálculo de uso vs plan."""

    def test_get_usage_free_plan(self, session):
        from app.models.organization import Organization, Membership
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Usage Org", slug="usage-org", plan="free")
        session.add(org)
        session.commit()
        session.refresh(org)

        # Agregar 2 miembros
        for uid in [1, 2]:
            from app.models.user import User
            user = User(email=f"usage{uid}@test.com", name=f"User{uid}", hashed_password="x")
            session.add(user)
            session.commit()
            session.refresh(user)
            m = Membership(user_id=user.id, organization_id=org.id, role="member")
            session.add(m)
        session.commit()

        usage = billing_service.get_usage(session, org.id)
        assert usage["plan"] == "free"
        assert usage["members"]["current"] == 2
        assert usage["members"]["max"] == 3  # free plan
        assert usage["members"]["unlimited"] is False
        assert usage["members"]["percentage"] > 0

    def test_get_usage_enterprise_unlimited(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Ent Org", slug="ent-org", plan="enterprise")
        session.add(org)
        session.commit()
        session.refresh(org)

        # Forzar plan enterprise en la suscripción
        sub = billing_service.get_or_create_subscription(session, org.id)
        sub.plan = "enterprise"
        session.add(sub)
        session.commit()

        usage = billing_service.get_usage(session, org.id)
        assert usage["plan"] == "enterprise"
        assert usage["members"]["unlimited"] is True
        assert usage["members"]["max"] is None

    def test_usage_includes_features(self, session):
        from app.models.organization import Organization
        from app.services.billing.billing_service import billing_service

        org = Organization(name="Feat Org", slug="feat-org", plan="pro")
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = billing_service.get_or_create_subscription(session, org.id)
        sub.plan = "pro"
        session.add(sub)
        session.commit()

        usage = billing_service.get_usage(session, org.id)
        assert "webhooks" in usage["features"]
        assert "priority_support" in usage["features"]


class TestBillingDashboardRoutes:
    """Tests de rutas HTTP de dashboard de billing."""

    def test_payments_endpoint_exists(self, client):
        """GET /billing/payments existe (requiere org context)."""
        response = client.get("/billing/payments")
        # Sin auth/org debería dar error, no 404
        assert response.status_code in (401, 403, 422)

    def test_usage_endpoint_exists(self, client):
        """GET /billing/usage existe (requiere org context)."""
        response = client.get("/billing/usage")
        assert response.status_code in (401, 403, 422)
