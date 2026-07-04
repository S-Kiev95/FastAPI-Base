"""Tests de endpoints básicos de la API."""


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "database" in data
        assert "timestamp" in data


class TestUsersCRUD:
    def test_create_user(self, client):
        response = client.post(
            "/users/",
            json={
                "provider": "google",
                "provider_user_id": "g123",
                "email": "crud@test.com",
                "name": "CRUD User",
            },
        )
        assert response.status_code == 201
        assert response.json()["email"] == "crud@test.com"

    def test_get_users_list(self, client, sample_users):
        response = client.get("/users/")
        assert response.status_code == 200
        assert len(response.json()) == 4

    def test_get_user_by_id(self, client, sample_users):
        user_id = sample_users[0]["id"]
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["email"] == "alice@gmail.com"

    def test_get_user_not_found(self, client):
        response = client.get("/users/99999")
        assert response.status_code == 404

    def test_update_user(self, client, sample_users):
        user_id = sample_users[0]["id"]
        response = client.patch(
            f"/users/{user_id}", json={"name": "Alice Updated"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Alice Updated"

    def test_delete_user(self, client, sample_users):
        user_id = sample_users[0]["id"]
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 204

        # Verificar que no existe
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 404

    def test_get_user_by_email(self, client, sample_users):
        response = client.get("/users/email/alice@gmail.com")
        assert response.status_code == 200
        assert response.json()["name"] == "Alice Gmail"

    def test_paginated_list(self, client, sample_users):
        response = client.get("/users/paginated/list?skip=0&limit=2")
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 4
        assert len(result["data"]) == 2
        assert result["has_more"] is True
