"""Tests de rate limiting per-tenant (unit tests, no requieren Redis)."""


class TestRateLimitMiddleware:
    """Tests del middleware de rate limiting con soporte per-tenant."""

    def test_path_specific_limits(self):
        """_get_limit_for_path() retorna límites específicos por path."""
        from app.middleware.rate_limit import RateLimitMiddleware

        class FakeApp:
            pass

        middleware = RateLimitMiddleware(FakeApp(), default_limit=100, default_window=60)

        # Path exacto
        assert middleware._get_limit_for_path("/tasks/email/bulk") == (5, 3600)

        # Path con prefijo
        assert middleware._get_limit_for_path("/tasks/123") == (50, 60)

        # Path sin límite específico
        assert middleware._get_limit_for_path("/auth/login") is None

    def test_get_plan_rate_limit(self, session):
        """get_plan_rate_limit() retorna el límite correcto por plan."""
        from app.core.plan_guards import get_plan_rate_limit
        from app.models.organization import Organization
        from app.models.subscription import Subscription

        # Crear org + sub con plan free
        org = Organization(name="Test Rate", slug="test-rate", plan="free", is_active=True)
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = Subscription(
            organization_id=org.id, plan="free", status="active",
            gateway="manual",
        )
        session.add(sub)
        session.commit()

        limit = get_plan_rate_limit(session, org.id)
        assert limit == 100  # free plan = 100 req/hora

    def test_enterprise_has_no_rate_limit(self, session):
        """Enterprise plan tiene rate limit None (ilimitado)."""
        from app.core.plan_guards import get_plan_rate_limit
        from app.models.organization import Organization
        from app.models.subscription import Subscription

        org = Organization(name="Enterprise", slug="enterprise-rl", plan="enterprise", is_active=True)
        session.add(org)
        session.commit()
        session.refresh(org)

        sub = Subscription(
            organization_id=org.id, plan="enterprise", status="active",
            gateway="manual",
        )
        session.add(sub)
        session.commit()

        limit = get_plan_rate_limit(session, org.id)
        assert limit is None
