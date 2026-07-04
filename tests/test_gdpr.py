"""Tests del servicio GDPR y rutas de account."""
from datetime import datetime, timezone, timedelta

from app.services.gdpr_service import gdpr_service


class TestGDPRService:
    """Tests directos del servicio GDPR."""

    def _create_user(self, session, email="gdpr@test.com"):
        from app.models.user import User
        user = User(
            email=email, provider="local", hashed_password="h",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def test_export_user_data(self, session):
        """export_user_data() retorna datos completos del usuario."""
        user = self._create_user(session)

        data = gdpr_service.export_user_data(session, user.id)
        assert data["user_id"] == user.id
        assert data["profile"]["email"] == "gdpr@test.com"
        assert "memberships" in data
        assert "api_keys" in data
        assert "audit_log" in data
        assert "export_date" in data

    def test_export_nonexistent_user(self, session):
        """export_user_data() retorna dict vacío para usuario inexistente."""
        data = gdpr_service.export_user_data(session, 99999)
        assert data == {}

    def test_request_account_deletion(self, session):
        """request_account_deletion() marca la cuenta para eliminación."""
        user = self._create_user(session, "delete@test.com")

        deletion_date = gdpr_service.request_account_deletion(session, user.id)
        assert deletion_date is not None

        # Refrescar
        session.refresh(user)
        assert user.is_active is False
        assert user.deleted_at is not None
        # Comparar como aware
        now = datetime.now(timezone.utc)
        deleted_at = user.deleted_at if user.deleted_at.tzinfo else user.deleted_at.replace(tzinfo=timezone.utc)
        assert deleted_at > now  # Fecha futura

    def test_cancel_account_deletion(self, session):
        """cancel_account_deletion() restaura la cuenta."""
        user = self._create_user(session, "cancel@test.com")

        gdpr_service.request_account_deletion(session, user.id)
        success = gdpr_service.cancel_account_deletion(session, user.id)
        assert success is True

        session.refresh(user)
        assert user.is_active is True
        assert user.deleted_at is None

    def test_cancel_expired_deletion_fails(self, session):
        """cancel_account_deletion() falla si el período de gracia expiró."""
        from app.models.user import User
        user = self._create_user(session, "expired@test.com")

        # Marcar con fecha pasada (ya expiró)
        user.deleted_at = datetime.now(timezone.utc) - timedelta(days=1)
        user.is_active = False
        session.add(user)
        session.commit()

        success = gdpr_service.cancel_account_deletion(session, user.id)
        assert success is False

    def test_purge_expired_accounts(self, session):
        """purge_expired_accounts() elimina cuentas cuyo grace period expiró."""
        from app.models.user import User
        from sqlmodel import select

        # Crear: una expirada, una pendiente, una activa
        expired = User(
            email="expired_purge@test.com", provider="local", hashed_password="h",
            is_active=False,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        pending = User(
            email="pending_purge@test.com", provider="local", hashed_password="h",
            is_active=False,
            deleted_at=datetime.now(timezone.utc) + timedelta(days=29),
        )
        active = User(
            email="active_purge@test.com", provider="local", hashed_password="h",
            is_active=True,
        )
        session.add_all([expired, pending, active])
        session.commit()

        count = gdpr_service.purge_expired_accounts(session)
        assert count == 1

        # Verificar que solo la expirada fue eliminada
        remaining = session.exec(
            select(User).where(User.email.in_([
                "expired_purge@test.com", "pending_purge@test.com", "active_purge@test.com"
            ]))
        ).all()
        emails = [u.email for u in remaining]
        assert "expired_purge@test.com" not in emails
        assert "pending_purge@test.com" in emails
        assert "active_purge@test.com" in emails


class TestGDPRRoutes:
    """Tests de las rutas GDPR via API."""

    def test_export_data_authenticated(self, client, registered_user):
        """GET /account/export retorna datos del usuario autenticado."""
        response = client.get("/account/export", headers=registered_user["headers"])
        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["email"] == "test@example.com"

    def test_export_data_unauthenticated(self, client):
        """GET /account/export requiere autenticación."""
        response = client.get("/account/export")
        assert response.status_code in (401, 403)

    def test_request_deletion(self, client, registered_user):
        """POST /account/request-deletion marca la cuenta."""
        response = client.post(
            "/account/request-deletion", headers=registered_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "deletion_date" in data
        assert "cancel_url" in data
