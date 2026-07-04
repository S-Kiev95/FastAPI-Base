"""Tests del sistema de API keys."""
from app.services.api_key_service import api_key_service


class TestApiKeyService:
    """Tests directos del servicio de API keys."""

    def test_generate_key_format(self):
        """generate_key() retorna key con prefijo correcto."""
        raw_key, prefix, key_hash = api_key_service.generate_key()
        assert raw_key.startswith("sk_live_")
        assert len(prefix) == 12
        assert len(key_hash) == 64  # SHA-256 hex

    def test_create_and_verify_key(self, session):
        """Crear una key y verificarla con el raw key."""
        from app.models.user import User

        # Crear usuario de test
        user = User(email="apikey@test.com", provider="local", hashed_password="h")
        session.add(user)
        session.commit()
        session.refresh(user)

        api_key, raw_key = api_key_service.create_key(
            session, user_id=user.id, name="Test Key"
        )
        assert api_key.name == "Test Key"
        assert api_key.is_active is True

        # Verificar con raw key
        verified = api_key_service.verify_key(session, raw_key)
        assert verified is not None
        assert verified.id == api_key.id
        assert verified.last_used_at is not None

    def test_verify_invalid_key_returns_none(self, session):
        """verify_key() retorna None para key inválida."""
        result = api_key_service.verify_key(session, "sk_live_invalid_key_12345")
        assert result is None

    def test_revoke_key(self, session):
        """revoke_key() desactiva la key."""
        from app.models.user import User

        user = User(email="revoke@test.com", provider="local", hashed_password="h")
        session.add(user)
        session.commit()
        session.refresh(user)

        api_key, raw_key = api_key_service.create_key(
            session, user_id=user.id, name="To Revoke"
        )

        # Revocar
        success = api_key_service.revoke_key(session, api_key.id, user.id)
        assert success is True

        # Ya no se puede verificar
        verified = api_key_service.verify_key(session, raw_key)
        assert verified is None

    def test_list_keys(self, session):
        """list_keys() retorna solo keys activas del usuario."""
        from app.models.user import User

        user = User(email="list@test.com", provider="local", hashed_password="h")
        session.add(user)
        session.commit()
        session.refresh(user)

        api_key_service.create_key(session, user_id=user.id, name="Key 1")
        api_key_service.create_key(session, user_id=user.id, name="Key 2")
        key3, _ = api_key_service.create_key(session, user_id=user.id, name="Key 3")

        # Revocar una
        api_key_service.revoke_key(session, key3.id, user.id)

        keys = api_key_service.list_keys(session, user.id)
        assert len(keys) == 2
        names = [k.name for k in keys]
        assert "Key 1" in names
        assert "Key 2" in names

    def test_has_scope(self, session):
        """has_scope() verifica scopes correctamente."""
        from app.models.user import User

        user = User(email="scope@test.com", provider="local", hashed_password="h")
        session.add(user)
        session.commit()
        session.refresh(user)

        # Key con scopes específicos
        api_key, _ = api_key_service.create_key(
            session, user_id=user.id, name="Scoped", scopes="read:users,write:media"
        )
        assert api_key_service.has_scope(api_key, "read:users") is True
        assert api_key_service.has_scope(api_key, "write:media") is True
        assert api_key_service.has_scope(api_key, "delete:users") is False

        # Key sin scopes = acceso total
        api_key2, _ = api_key_service.create_key(
            session, user_id=user.id, name="Full Access"
        )
        assert api_key_service.has_scope(api_key2, "anything") is True


class TestApiKeyRoutes:
    """Tests de las rutas de API keys."""

    def test_create_api_key(self, client, registered_user):
        """POST /api-keys crea una key y retorna el raw key."""
        response = client.post(
            "/api-keys/",
            json={"name": "Mi Key"},
            headers=registered_user["headers"],
        )
        assert response.status_code == 201
        data = response.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("sk_live_")
        assert data["name"] == "Mi Key"
        assert "message" in data

    def test_list_api_keys(self, client, registered_user):
        """GET /api-keys lista las keys del usuario."""
        # Crear dos keys
        client.post("/api-keys/", json={"name": "Key A"}, headers=registered_user["headers"])
        client.post("/api-keys/", json={"name": "Key B"}, headers=registered_user["headers"])

        response = client.get("/api-keys/", headers=registered_user["headers"])
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        # No debe exponer raw key ni hash
        for key in data:
            assert "raw_key" not in key
            assert "key_hash" not in key

    def test_revoke_api_key(self, client, registered_user):
        """DELETE /api-keys/{id} revoca la key."""
        # Crear
        create_resp = client.post(
            "/api-keys/", json={"name": "To Delete"}, headers=registered_user["headers"]
        )
        key_id = create_resp.json()["id"]

        # Revocar
        response = client.delete(f"/api-keys/{key_id}", headers=registered_user["headers"])
        assert response.status_code == 204

        # Ya no aparece en la lista
        list_resp = client.get("/api-keys/", headers=registered_user["headers"])
        ids = [k["id"] for k in list_resp.json()]
        assert key_id not in ids

    def test_auth_with_api_key(self, client, registered_user):
        """Autenticación dual: un API key funciona como Bearer token."""
        # Crear key
        create_resp = client.post(
            "/api-keys/", json={"name": "Auth Test"}, headers=registered_user["headers"]
        )
        raw_key = create_resp.json()["raw_key"]

        # Usar el API key como Bearer token
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["user"]["email"]

    def test_requires_auth(self, client):
        """Las rutas de API keys requieren autenticación."""
        response = client.get("/api-keys/")
        assert response.status_code in (401, 403)
