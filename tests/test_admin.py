"""Tests de Fase 6: admin panel API routes."""
import pytest


# ---- Fixtures locales ----

@pytest.fixture(name="superadmin_headers")
def superadmin_headers_fixture(client, session):
    """Crea un superadmin y retorna headers con su token."""
    from app.models.user import User
    from app.core.security import get_password_hash, create_access_token

    user = User(
        email="superadmin@test.com",
        name="Super Admin",
        provider="local",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_verified=True,
        is_superadmin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token({"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="normal_headers")
def normal_headers_fixture(client):
    """Registra un usuario normal y retorna headers."""
    resp = client.post("/auth/register", json={
        "email": "normal@test.com", "password": "password123", "name": "Normal",
    })
    assert resp.status_code == 201
    login = client.post("/auth/login", json={
        "email": "normal@test.com", "password": "password123",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="seeded_data")
def seeded_data_fixture(session):
    """Crea datos de prueba: orgs, users, subscriptions, payments."""
    from app.models.organization import Organization, Membership
    from app.models.user import User
    from app.models.subscription import Subscription, SubscriptionStatus, PaymentGatewayType
    from app.models.payment import Payment
    from app.core.security import get_password_hash

    orgs = []
    for i, (name, plan) in enumerate([
        ("Org Alpha", "starter"),
        ("Org Beta", "pro"),
        ("Org Gamma", "free"),
    ]):
        org = Organization(name=name, slug=f"org-{i}", plan=plan, is_active=True)
        session.add(org)
        session.commit()
        session.refresh(org)
        orgs.append(org)

        # Suscripción
        sub = Subscription(
            organization_id=org.id,
            plan=plan,
            status=SubscriptionStatus.active,
            gateway=PaymentGatewayType.none,
        )
        session.add(sub)
        session.commit()
        session.refresh(sub)

        # Un usuario por org
        user = User(
            email=f"user{i}@org.com", name=f"User {i}",
            provider="local", hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        m = Membership(user_id=user.id, organization_id=org.id, role="owner")
        session.add(m)
        session.commit()

        # Pago para org pro
        if plan == "pro":
            payment = Payment(
                organization_id=org.id,
                subscription_id=sub.id,
                gateway="stripe",
                gateway_payment_id="pi_test",
                amount=7900,
                currency="usd",
                status="succeeded",
                description="Pago Pro",
            )
            session.add(payment)
            session.commit()

    return orgs


# ---- Tests de acceso ----

class TestAdminAccess:
    """Solo superadmins pueden acceder a /api/admin/*."""

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/api/admin/dashboard")
        assert resp.status_code in (401, 403)

    def test_dashboard_requires_superadmin(self, client, normal_headers):
        resp = client.get("/api/admin/dashboard", headers=normal_headers)
        assert resp.status_code == 403

    def test_dashboard_ok_for_superadmin(self, client, superadmin_headers):
        resp = client.get("/api/admin/dashboard", headers=superadmin_headers)
        assert resp.status_code == 200


# ---- Tests de dashboard ----

class TestAdminDashboard:
    """Tests del endpoint /api/admin/dashboard."""

    def test_dashboard_returns_kpis(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/dashboard", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_organizations" in data
        assert "total_users" in data
        assert "active_subscriptions" in data
        assert "mrr" in data
        assert data["total_organizations"] >= 3

    def test_dashboard_mrr_calculation(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/dashboard", headers=superadmin_headers)
        data = resp.json()
        # starter(29) + pro(79) + free(0) = 108
        assert data["mrr"] == 108


# ---- Tests de organizations ----

class TestAdminOrganizations:
    """Tests de /api/admin/organizations."""

    def test_list_organizations(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/organizations", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3

    def test_list_filter_by_plan(self, client, superadmin_headers, seeded_data):
        resp = client.get(
            "/api/admin/organizations?plan=pro", headers=superadmin_headers,
        )
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_list_search(self, client, superadmin_headers, seeded_data):
        resp = client.get(
            "/api/admin/organizations?search=Alpha", headers=superadmin_headers,
        )
        data = resp.json()
        assert data["total"] == 1

    def test_get_organization_detail(self, client, superadmin_headers, seeded_data):
        # Primero obtener un ID
        resp = client.get("/api/admin/organizations?limit=1", headers=superadmin_headers)
        org_id = resp.json()["items"][0]["id"]

        resp = client.get(f"/api/admin/organizations/{org_id}", headers=superadmin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == org_id

    def test_toggle_org_active(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/organizations?limit=1", headers=superadmin_headers)
        org_id = resp.json()["items"][0]["id"]

        # Desactivar
        resp = client.patch(
            f"/api/admin/organizations/{org_id}/toggle-active?is_active=false",
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        # Reactivar
        resp = client.patch(
            f"/api/admin/organizations/{org_id}/toggle-active?is_active=true",
            headers=superadmin_headers,
        )
        assert resp.json()["is_active"] is True


# ---- Tests de users ----

class TestAdminUsers:
    """Tests de /api/admin/users."""

    def test_list_users(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/users", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 4  # 3 seeded + 1 superadmin

    def test_list_search_users(self, client, superadmin_headers, seeded_data):
        resp = client.get(
            "/api/admin/users?search=user0", headers=superadmin_headers,
        )
        data = resp.json()
        assert data["total"] >= 1

    def test_toggle_user_active(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/users?limit=1", headers=superadmin_headers)
        user_id = resp.json()["items"][0]["id"]

        resp = client.patch(
            f"/api/admin/users/{user_id}/toggle-active?is_active=false",
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


# ---- Tests de subscriptions ----

class TestAdminSubscriptions:
    """Tests de /api/admin/subscriptions."""

    def test_list_subscriptions(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/subscriptions", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3

    def test_filter_by_plan(self, client, superadmin_headers, seeded_data):
        resp = client.get(
            "/api/admin/subscriptions?plan=pro", headers=superadmin_headers,
        )
        data = resp.json()
        assert data["total"] == 1

    def test_subscription_stats(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/subscriptions/stats", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data
        assert data["active"] >= 3


# ---- Tests de payments ----

class TestAdminPayments:
    """Tests de /api/admin/payments."""

    def test_list_payments(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/payments", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_filter_by_status(self, client, superadmin_headers, seeded_data):
        resp = client.get(
            "/api/admin/payments?status=succeeded", headers=superadmin_headers,
        )
        data = resp.json()
        assert data["total"] >= 1


# ---- Tests de metrics ----

class TestAdminMetrics:
    """Tests de /api/admin/metrics."""

    def test_metrics(self, client, superadmin_headers, seeded_data):
        resp = client.get("/api/admin/metrics", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_distribution" in data
        assert "subscription_stats" in data
        assert "dashboard" in data


# ---- Tests de impersonate ----

class TestAdminImpersonate:
    """Tests de /api/admin/impersonate."""

    def test_impersonate_user(self, client, superadmin_headers, seeded_data):
        # Obtener un user para impersonar
        resp = client.get("/api/admin/users?limit=1", headers=superadmin_headers)
        user_id = resp.json()["items"][0]["id"]

        resp = client.post(
            f"/api/admin/impersonate/{user_id}", headers=superadmin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["impersonated_user"]["id"] == user_id
        assert "admin_email" in data

        # Verificar que el token funciona
        imp_headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_resp = client.get("/auth/me", headers=imp_headers)
        assert me_resp.status_code == 200

    def test_impersonate_nonexistent_user(self, client, superadmin_headers):
        resp = client.post(
            "/api/admin/impersonate/99999", headers=superadmin_headers,
        )
        assert resp.status_code == 404

    def test_impersonate_requires_superadmin(self, client, normal_headers):
        resp = client.post("/api/admin/impersonate/1", headers=normal_headers)
        assert resp.status_code == 403
