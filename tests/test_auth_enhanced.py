"""Tests de auth mejorado: refresh tokens, logout, verificación email, password reset, invitaciones."""
from app.core.security import (
    create_verification_token,
    create_password_reset_token,
    hash_token,
)


class TestRefreshTokens:
    def test_login_returns_refresh_token(self, client):
        """Login retorna access_token + refresh_token."""
        client.post("/auth/register", json={
            "email": "refresh@test.com", "password": "secret123", "name": "Ref",
        })
        resp = client.post("/auth/login", json={
            "email": "refresh@test.com", "password": "secret123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_rotates_token(self, client):
        """Refresh retorna nuevo par de tokens y el anterior queda revocado."""
        client.post("/auth/register", json={
            "email": "rot@test.com", "password": "secret123", "name": "Rot",
        })
        login = client.post("/auth/login", json={
            "email": "rot@test.com", "password": "secret123",
        })
        refresh_token = login.json()["refresh_token"]

        # Usar refresh token
        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        new_data = resp.json()
        assert "access_token" in new_data
        assert "refresh_token" in new_data
        assert new_data["refresh_token"] != refresh_token  # Rotado

    def test_refresh_with_revoked_token_fails(self, client):
        """Usar un refresh token ya usado (revocado) falla."""
        client.post("/auth/register", json={
            "email": "revoked@test.com", "password": "secret123", "name": "Rev",
        })
        login = client.post("/auth/login", json={
            "email": "revoked@test.com", "password": "secret123",
        })
        refresh_token = login.json()["refresh_token"]

        # Primer refresh OK
        client.post("/auth/refresh", json={"refresh_token": refresh_token})

        # Segundo refresh con mismo token falla (ya revocado)
        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 401

    def test_refresh_with_invalid_token_fails(self, client):
        """Token inventado falla."""
        resp = client.post("/auth/refresh", json={"refresh_token": "token-falso"})
        assert resp.status_code == 401


class TestLogout:
    def test_logout_revokes_current_token(self, client):
        """POST /auth/logout revoca el refresh token."""
        client.post("/auth/register", json={
            "email": "logout@test.com", "password": "secret123", "name": "Lo",
        })
        login = client.post("/auth/login", json={
            "email": "logout@test.com", "password": "secret123",
        })
        refresh_token = login.json()["refresh_token"]

        # Logout
        resp = client.post("/auth/logout", json={"refresh_token": refresh_token})
        assert resp.status_code == 204

        # Intentar refresh con token revocado
        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 401

    def test_logout_all_revokes_all_tokens(self, client):
        """POST /auth/logout-all revoca todos los refresh tokens del usuario."""
        client.post("/auth/register", json={
            "email": "logoutall@test.com", "password": "secret123", "name": "LA",
        })

        # Hacer 2 logins (2 refresh tokens)
        login1 = client.post("/auth/login", json={
            "email": "logoutall@test.com", "password": "secret123",
        })
        login2 = client.post("/auth/login", json={
            "email": "logoutall@test.com", "password": "secret123",
        })
        access_token = login2.json()["access_token"]
        rt1 = login1.json()["refresh_token"]
        rt2 = login2.json()["refresh_token"]

        # Logout-all
        resp = client.post(
            "/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 204

        # Ambos refresh tokens deben estar revocados
        assert client.post("/auth/refresh", json={"refresh_token": rt1}).status_code == 401
        assert client.post("/auth/refresh", json={"refresh_token": rt2}).status_code == 401


class TestEmailVerification:
    def test_verify_email_success(self, client, session):
        """GET /auth/verify-email/{token} pone is_verified=True."""
        client.post("/auth/register", json={
            "email": "verify@test.com", "password": "secret123", "name": "V",
        })

        # Generar token de verificación directamente
        token = create_verification_token("verify@test.com")

        resp = client.get(f"/auth/verify-email/{token}")
        assert resp.status_code == 200
        assert "verificado" in resp.json()["message"].lower()

        # Verificar que el usuario ahora tiene is_verified=True
        login = client.post("/auth/login", json={
            "email": "verify@test.com", "password": "secret123",
        })
        me = client.get("/auth/me", headers={
            "Authorization": f"Bearer {login.json()['access_token']}"
        })
        assert me.json()["is_verified"] is True

    def test_verify_email_invalid_token(self, client):
        """Token inválido retorna 400."""
        resp = client.get("/auth/verify-email/token-invalido")
        assert resp.status_code == 400

    def test_verify_email_already_verified(self, client):
        """Si ya está verificado, retorna mensaje sin error."""
        client.post("/auth/register", json={
            "email": "already@test.com", "password": "secret123", "name": "A",
        })
        token = create_verification_token("already@test.com")

        # Primera verificación
        client.get(f"/auth/verify-email/{token}")
        # Segunda verificación (ya verificado)
        token2 = create_verification_token("already@test.com")
        resp = client.get(f"/auth/verify-email/{token2}")
        assert resp.status_code == 200


class TestPasswordReset:
    def test_forgot_password_returns_ok(self, client):
        """POST /auth/forgot-password siempre retorna 200 (no revela si email existe)."""
        resp = client.post("/auth/forgot-password", json={"email": "noexiste@test.com"})
        assert resp.status_code == 200

    def test_reset_password_success(self, client):
        """POST /auth/reset-password con token válido cambia la contraseña."""
        client.post("/auth/register", json={
            "email": "reset@test.com", "password": "oldpass123", "name": "R",
        })

        # Generar token de reset
        token = create_password_reset_token("reset@test.com")

        resp = client.post("/auth/reset-password", json={
            "token": token,
            "new_password": "newpass456",
        })
        assert resp.status_code == 200

        # Login con nueva contraseña
        login = client.post("/auth/login", json={
            "email": "reset@test.com", "password": "newpass456",
        })
        assert login.status_code == 200

        # Login con contraseña vieja falla
        login_old = client.post("/auth/login", json={
            "email": "reset@test.com", "password": "oldpass123",
        })
        assert login_old.status_code == 401

    def test_reset_password_invalid_token(self, client):
        """Token inválido retorna 400."""
        resp = client.post("/auth/reset-password", json={
            "token": "token-falso",
            "new_password": "newpass",
        })
        assert resp.status_code == 400

    def test_reset_revokes_all_refresh_tokens(self, client):
        """Después del reset, todos los refresh tokens se revocan."""
        client.post("/auth/register", json={
            "email": "resetrt@test.com", "password": "oldpass123", "name": "RR",
        })
        login = client.post("/auth/login", json={
            "email": "resetrt@test.com", "password": "oldpass123",
        })
        rt = login.json()["refresh_token"]

        # Reset password
        token = create_password_reset_token("resetrt@test.com")
        client.post("/auth/reset-password", json={
            "token": token,
            "new_password": "newpass456",
        })

        # Refresh token anterior revocado
        resp = client.post("/auth/refresh", json={"refresh_token": rt})
        assert resp.status_code == 401


class TestInvitations:
    def test_create_invitation(self, client, registered_user_with_org):
        """Admin crea invitación."""
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]

        resp = client.post(
            f"/orgs/{slug}/invitations",
            headers=headers,
            json={"email": "invited@test.com", "role": "member"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "invited@test.com"
        assert data["role"] == "member"

    def test_list_pending_invitations(self, client, registered_user_with_org):
        """Listar invitaciones pendientes."""
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]

        # Crear invitación
        client.post(
            f"/orgs/{slug}/invitations",
            headers=headers,
            json={"email": "pending@test.com", "role": "member"},
        )

        resp = client.get(f"/orgs/{slug}/invitations", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_accept_invitation_creates_membership(self, client, registered_user_with_org, session):
        """Aceptar invitación crea membership."""
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]

        # Crear invitación para un email
        resp_inv = client.post(
            f"/orgs/{slug}/invitations",
            headers=headers,
            json={"email": "accepter@test.com", "role": "member"},
        )
        assert resp_inv.status_code == 201

        # El token raw lo necesitamos del servicio directamente (no se expone en la API)
        # Usamos el servicio para obtenerlo
        from app.services.invitation_service import invitation_service
        from app.models.invitation import Invitation
        from sqlmodel import select

        inv = session.exec(
            select(Invitation).where(Invitation.email == "accepter@test.com")
        ).first()

        # Crear el usuario que aceptará
        client.post("/auth/register", json={
            "email": "accepter@test.com", "password": "secret123", "name": "Accepter",
        })
        login = client.post("/auth/login", json={
            "email": "accepter@test.com", "password": "secret123",
        })
        accepter_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Para aceptar necesitamos el raw_token — creamos una invitación via servicio
        import secrets
        raw_token = secrets.token_urlsafe(48)
        from app.core.security import hash_token as ht
        inv.token_hash = ht(raw_token)
        session.add(inv)
        session.commit()

        resp = client.post(
            f"/auth/accept-invitation/{raw_token}",
            headers=accepter_headers,
        )
        assert resp.status_code == 200
        assert "aceptada" in resp.json()["message"].lower()

    def test_revoke_invitation(self, client, registered_user_with_org):
        """Admin revoca invitación."""
        headers = registered_user_with_org["headers"]
        slug = registered_user_with_org["org_slug"]

        # Crear invitación
        resp = client.post(
            f"/orgs/{slug}/invitations",
            headers=headers,
            json={"email": "revoke@test.com", "role": "member"},
        )
        invitation_id = resp.json()["id"]

        # Revocar
        resp = client.delete(
            f"/orgs/{slug}/invitations/{invitation_id}",
            headers=headers,
        )
        assert resp.status_code == 204

        # Verificar que ya no aparece en pendientes
        resp = client.get(f"/orgs/{slug}/invitations", headers=headers)
        ids = [i["id"] for i in resp.json()]
        assert invitation_id not in ids
