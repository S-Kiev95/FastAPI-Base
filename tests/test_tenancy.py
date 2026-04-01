"""Tests del sistema de multi-tenancy: organizaciones, memberships, aislamiento."""


class TestRegisterCreatesOrg:
    """El registro crea user + org + membership(owner) automáticamente."""

    def test_register_creates_org_and_membership(self, client):
        response = client.post(
            "/auth/register",
            json={"email": "tenant1@example.com", "password": "secret123", "name": "T1"},
        )
        assert response.status_code == 201

        # Login para obtener token
        login = client.post(
            "/auth/login",
            json={"email": "tenant1@example.com", "password": "secret123"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # El usuario debe tener al menos una org
        orgs = client.get("/orgs/", headers=headers)
        assert orgs.status_code == 200
        assert len(orgs.json()) >= 1

    def test_register_generates_slug_from_email(self, client):
        response = client.post(
            "/auth/register",
            json={"email": "alice.smith@company.com", "password": "secret123", "name": "Alice"},
        )
        assert response.status_code == 201

        login = client.post(
            "/auth/login",
            json={"email": "alice.smith@company.com", "password": "secret123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        orgs = client.get("/orgs/", headers=headers)
        assert orgs.status_code == 200
        # El slug se genera del email (parte antes del @)
        slugs = [o["slug"] for o in orgs.json()]
        assert any("alice" in s for s in slugs)

    def test_register_custom_org_name(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "bob@example.com",
                "password": "secret123",
                "name": "Bob",
                "organization_name": "Bob Seguros",
            },
        )
        assert response.status_code == 201

        login = client.post(
            "/auth/login",
            json={"email": "bob@example.com", "password": "secret123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        orgs = client.get("/orgs/", headers=headers)
        assert orgs.status_code == 200
        slugs = [o["slug"] for o in orgs.json()]
        assert "bob-seguros" in slugs


class TestOrganizationCRUD:
    def test_list_user_organizations(self, client, registered_user_with_org):
        headers = registered_user_with_org["headers"]
        response = client.get("/orgs/", headers=headers)
        assert response.status_code == 200
        orgs = response.json()
        assert len(orgs) >= 1
        assert any(o["slug"] == registered_user_with_org["org_slug"] for o in orgs)

    def test_get_organization_by_slug(self, client, registered_user_with_org):
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]
        response = client.get(f"/orgs/{slug}", headers=headers)
        assert response.status_code == 200
        assert response.json()["slug"] == slug

    def test_update_organization(self, client, registered_user_with_org):
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]
        response = client.patch(
            f"/orgs/{slug}",
            headers=headers,
            json={"name": "Nombre Actualizado"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Nombre Actualizado"

    def test_get_org_not_found(self, client, registered_user_with_org):
        headers = registered_user_with_org["headers"]
        response = client.get("/orgs/no-existe", headers=headers)
        assert response.status_code == 404


class TestMembership:
    def test_list_members(self, client, registered_user_with_org):
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]
        response = client.get(f"/orgs/{slug}/members", headers=headers)
        assert response.status_code == 200
        members = response.json()
        assert len(members) >= 1
        # El owner debe estar en la lista
        roles = [m["role"] for m in members]
        assert "owner" in roles

    def test_add_member_to_org(self, client, registered_user_with_org):
        """Admin/owner agrega un nuevo miembro."""
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]

        # Crear un segundo usuario (vía API users)
        new_user = client.post(
            "/users/",
            json={
                "provider": "local",
                "provider_user_id": "member1",
                "email": "member1@example.com",
                "name": "Member One",
            },
        )
        assert new_user.status_code == 201
        new_user_id = new_user.json()["id"]

        # Agregar como miembro
        response = client.post(
            f"/orgs/{slug}/members",
            headers=headers,
            json={"user_id": new_user_id, "role": "member"},
        )
        assert response.status_code == 201
        assert response.json()["role"] == "member"

    def test_add_duplicate_member_fails(self, client, registered_user_with_org):
        """No se puede agregar al mismo usuario dos veces."""
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]
        owner_id = registered_user_with_org["user"]["id"]

        response = client.post(
            f"/orgs/{slug}/members",
            headers=headers,
            json={"user_id": owner_id, "role": "member"},
        )
        assert response.status_code == 400

    def test_remove_member(self, client, registered_user_with_org):
        """Admin puede remover un miembro (no-owner)."""
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]

        # Crear y agregar miembro
        new_user = client.post(
            "/users/",
            json={
                "provider": "local",
                "provider_user_id": "removable",
                "email": "removable@example.com",
                "name": "Removable",
            },
        )
        new_user_id = new_user.json()["id"]

        client.post(
            f"/orgs/{slug}/members",
            headers=headers,
            json={"user_id": new_user_id, "role": "member"},
        )

        # Remover
        response = client.delete(
            f"/orgs/{slug}/members/{new_user_id}", headers=headers
        )
        assert response.status_code == 204

    def test_owner_cannot_be_removed(self, client, registered_user_with_org):
        """El owner no puede ser removido de la org."""
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]
        owner_id = registered_user_with_org["user"]["id"]

        response = client.delete(
            f"/orgs/{slug}/members/{owner_id}", headers=headers
        )
        assert response.status_code == 400


class TestTenantDependency:
    def test_get_org_requires_membership(self, client, registered_user_with_org, second_user_with_org):
        """User sin membership no puede acceder a la org de otro."""
        second_headers = second_user_with_org["headers"]
        first_slug = registered_user_with_org["org_slug"]

        response = client.get(f"/orgs/{first_slug}", headers=second_headers)
        assert response.status_code == 403

    def test_get_org_without_auth(self, client, registered_user_with_org):
        """Sin token → 401/403."""
        slug = registered_user_with_org["org_slug"]
        response = client.get(f"/orgs/{slug}")
        assert response.status_code in (401, 403)


class TestSystemOrganization:
    def test_system_org_created(self, session, system_org):
        """Verifica que el fixture crea la org sistema."""
        assert system_org.is_system is True
        assert system_org.slug == "system"

    def test_system_org_has_is_system_flag(self, session, system_org):
        from app.services.organization_service import organization_service

        org = organization_service.get_system_organization(session)
        assert org is not None
        assert org.is_system is True
