"""Tests del sistema de autenticación JWT."""


class TestRegister:
    def test_register_creates_user(self, client):
        response = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "secret123", "name": "New"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert data["provider"] == "local"

    def test_register_duplicate_email_fails(self, client, registered_user):
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "other", "name": "Dup"},
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]


class TestLogin:
    def test_login_returns_token(self, client, registered_user):
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, registered_user):
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post(
            "/auth/login",
            json={"email": "ghost@example.com", "password": "whatever"},
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    def test_me_with_valid_token(self, client, registered_user):
        response = client.get("/auth/me", headers=registered_user["headers"])
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_me_without_token(self, client):
        response = client.get("/auth/me")
        assert response.status_code in (401, 403)

    def test_me_with_invalid_token(self, client):
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer invalidtoken"}
        )
        assert response.status_code == 401


class TestRefreshToken:
    def test_refresh_returns_valid_token(self, client, registered_user):
        response = client.post(
            "/auth/refresh", headers=registered_user["headers"]
        )
        assert response.status_code == 200
        new_token = response.json()["access_token"]
        assert new_token  # token no vacío

        # Verificar que el nuevo token funciona
        me_response = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "test@example.com"
