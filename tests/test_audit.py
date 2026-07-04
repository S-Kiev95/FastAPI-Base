"""Tests del sistema de audit log."""
from app.services.audit_service import audit_service, AuditService


class TestAuditService:
    """Tests directos del servicio de auditoría."""

    def test_record_creates_entry(self, session):
        """record() crea una entrada de audit log."""
        entry = audit_service.record(
            session,
            user_id=1,
            action="create",
            resource_type="users",
            resource_id="42",
            changes={"name": {"old": None, "new": "Test"}},
            ip_address="127.0.0.1",
        )
        assert entry is not None
        assert entry.action == "create"
        assert entry.resource_type == "users"
        assert entry.resource_id == "42"
        assert entry.user_id == 1

    def test_get_logs_filters(self, session):
        """get_logs() filtra por resource_type y action."""
        # Crear varias entradas
        audit_service.record(session, action="create", resource_type="users", resource_id="1")
        audit_service.record(session, action="update", resource_type="users", resource_id="1")
        audit_service.record(session, action="create", resource_type="media", resource_id="10")

        # Filtrar por resource_type
        result = audit_service.get_logs(session, resource_type="users")
        assert result["total"] == 2

        # Filtrar por action
        result = audit_service.get_logs(session, action="create")
        assert result["total"] == 2

        # Filtrar por ambos
        result = audit_service.get_logs(session, resource_type="media", action="create")
        assert result["total"] == 1

    def test_compute_changes(self):
        """compute_changes() calcula diff correctamente."""

        class FakeObj:
            name = "Old"
            email = "same@test.com"

        changes = AuditService.compute_changes(FakeObj(), {"name": "New", "email": "same@test.com"})
        assert "name" in changes
        assert changes["name"]["old"] == "Old"
        assert changes["name"]["new"] == "New"
        assert "email" not in changes  # No cambió

    def test_get_logs_pagination(self, session):
        """get_logs() respeta skip y limit."""
        for i in range(5):
            audit_service.record(
                session, action="create", resource_type="tasks", resource_id=str(i)
            )

        result = audit_service.get_logs(session, resource_type="tasks", limit=2)
        assert len(result["items"]) == 2
        assert result["total"] == 5

        result2 = audit_service.get_logs(session, resource_type="tasks", skip=3, limit=10)
        assert len(result2["items"]) == 2  # 5 - 3 = 2


class TestAuditRoutes:
    """Tests de las rutas de auditoría (requieren superadmin)."""

    def _make_superadmin(self, session, user_id: int):
        """Helper: marca un usuario como superadmin."""
        from app.models.user import User
        user = session.get(User, user_id)
        user.is_superadmin = True
        session.add(user)
        session.commit()

    def test_audit_logs_requires_superadmin(self, client, registered_user):
        """GET /audit/logs rechaza usuarios no-superadmin."""
        response = client.get("/audit/logs", headers=registered_user["headers"])
        assert response.status_code == 403

    def test_audit_logs_superadmin_access(self, client, registered_user, session):
        """GET /audit/logs funciona para superadmin."""
        self._make_superadmin(session, registered_user["user"]["id"])

        # Crear un audit log
        audit_service.record(session, action="test", resource_type="test", resource_id="1")

        response = client.get("/audit/logs", headers=registered_user["headers"])
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_resource_audit_trail(self, client, registered_user, session):
        """GET /audit/logs/{type}/{id} retorna trail de un recurso."""
        self._make_superadmin(session, registered_user["user"]["id"])

        audit_service.record(session, action="create", resource_type="users", resource_id="99")
        audit_service.record(session, action="update", resource_type="users", resource_id="99")

        response = client.get("/audit/logs/users/99", headers=registered_user["headers"])
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
