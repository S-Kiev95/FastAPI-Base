"""Tests de soft delete via API."""


class TestSoftDeleteUsers:
    """Soft delete de usuarios a través de endpoints."""

    def test_delete_user_soft_deletes(self, client, registered_user, session):
        """DELETE /users/{id} marca deleted_at en lugar de borrar."""
        from app.models.user import User

        user_id = registered_user["user"]["id"]
        headers = registered_user["headers"]

        # Eliminar
        response = client.delete(f"/users/{user_id}", headers=headers)
        assert response.status_code in (200, 204, True)

        # El usuario ya no aparece en GET
        response = client.get(f"/users/{user_id}", headers=headers)
        # Puede dar 401 (el user eliminado ya no puede autenticarse) o 404
        assert response.status_code in (401, 404)

    def test_soft_deleted_user_still_in_db(self, client, session):
        """El registro sigue en BD con deleted_at != NULL."""
        from app.models.user import User
        from sqlmodel import select

        # Crear usuario
        resp = client.post(
            "/auth/register",
            json={"email": "softdel@example.com", "password": "pass123", "name": "SD"},
        )
        assert resp.status_code == 201
        user_id = resp.json()["id"]

        # Login
        login = client.post(
            "/auth/login",
            json={"email": "softdel@example.com", "password": "pass123"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Eliminar
        client.delete(f"/users/{user_id}", headers=headers)

        # Verificar que sigue en BD
        user = session.exec(select(User).where(User.id == user_id)).first()
        assert user is not None
        assert user.deleted_at is not None


class TestSoftDeleteService:
    """Tests directos del servicio con soft delete."""

    def test_service_restore(self, session):
        """restore() recupera un registro soft-deleted."""
        from app.models.user import User
        from app.services.user_service import user_service
        from datetime import datetime, timezone

        # Crear usuario manualmente
        user = User(
            email="restore@test.com",
            provider="local",
            hashed_password="hash",
            is_active=True,
            deleted_at=datetime.now(timezone.utc),  # Ya eliminado
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # No debe aparecer en get_by_id
        result = user_service.get_by_id(session, user.id)
        assert result is None

        # Restaurar
        restored = user_service.restore(session, user.id)
        assert restored is not None
        assert restored.deleted_at is None

        # Ahora sí aparece
        result = user_service.get_by_id(session, user.id)
        assert result is not None

    def test_service_get_deleted(self, session):
        """get_deleted() lista solo registros eliminados."""
        from app.models.user import User
        from app.services.user_service import user_service
        from datetime import datetime, timezone

        # Crear usuarios: uno activo, uno eliminado
        active = User(email="active@test.com", provider="local", hashed_password="h")
        deleted = User(
            email="deleted@test.com", provider="local", hashed_password="h",
            deleted_at=datetime.now(timezone.utc),
        )
        session.add_all([active, deleted])
        session.commit()

        deleted_list = user_service.get_deleted(session)
        emails = [u.email for u in deleted_list]
        assert "deleted@test.com" in emails
        assert "active@test.com" not in emails

    def test_service_count_excludes_deleted(self, session):
        """count() no cuenta registros soft-deleted."""
        from app.models.user import User
        from app.services.user_service import user_service
        from datetime import datetime, timezone

        initial_count = user_service.count(session)

        active = User(email="cnt_active@test.com", provider="local", hashed_password="h")
        deleted = User(
            email="cnt_del@test.com", provider="local", hashed_password="h",
            deleted_at=datetime.now(timezone.utc),
        )
        session.add_all([active, deleted])
        session.commit()

        new_count = user_service.count(session)
        assert new_count == initial_count + 1  # Solo el activo
