"""Tests de seguridad: headers, validators, rate limiting."""


class TestSecurityHeaders:
    """Verifica que los security headers se agregan correctamente."""

    def test_security_headers_present(self, client):
        """GET /health debe incluir security headers."""
        response = client.get("/health")
        assert response.status_code == 200

        headers = response.headers
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in headers
        assert headers["X-XSS-Protection"] == "1; mode=block"

        assert "Referrer-Policy" in headers
        assert "Content-Security-Policy" in headers

    def test_hsts_not_enabled_in_dev(self, client):
        """HSTS no debe estar en desarrollo (ENVIRONMENT != production)."""
        from app.config import settings

        response = client.get("/health")
        if settings.ENVIRONMENT != "production":
            # No debería tener HSTS en development
            assert "Strict-Transport-Security" not in response.headers or \
                   response.headers.get("Strict-Transport-Security") == ""


class TestPasswordValidation:
    """Tests de validación de contraseñas."""

    def test_weak_password_rejected(self, client, monkeypatch):
        """Contraseñas débiles deben ser rechazadas."""
        # Habilitar validators para este test
        from app.config import settings
        monkeypatch.setattr(settings, "ENFORCE_STRONG_PASSWORDS", True)
        # Password demasiado corta
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "short", "name": "Test"},
        )
        assert response.status_code == 422
        assert "8 caracteres" in response.json()["detail"][0]["msg"]

    def test_no_uppercase_password_rejected(self, client, monkeypatch):
        """Password sin mayúscula debe fallar."""
        from app.config import settings
        monkeypatch.setattr(settings, "ENFORCE_STRONG_PASSWORDS", True)
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "alllowercase123", "name": "Test"},
        )
        assert response.status_code == 422
        assert "mayúscula" in response.json()["detail"][0]["msg"].lower()

    def test_no_number_password_rejected(self, client, monkeypatch):
        """Password sin número debe fallar."""
        from app.config import settings
        monkeypatch.setattr(settings, "ENFORCE_STRONG_PASSWORDS", True)
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "NoNumbers", "name": "Test"},
        )
        assert response.status_code == 422
        assert "número" in response.json()["detail"][0]["msg"].lower()

    def test_common_password_rejected(self, client, monkeypatch):
        """Passwords comunes deben ser bloqueadas."""
        from app.config import settings
        monkeypatch.setattr(settings, "ENFORCE_STRONG_PASSWORDS", True)
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "Password123", "name": "Test"},
        )
        # "password123" está en la lista de comunes (case-insensitive)
        assert response.status_code == 422

    def test_strong_password_accepted(self, client, monkeypatch):
        """Password fuerte debe ser aceptada."""
        from app.config import settings
        monkeypatch.setattr(settings, "ENFORCE_STRONG_PASSWORDS", True)
        response = client.post(
            "/auth/register",
            json={
                "email": "strong@example.com",
                "password": "Str0ngP@ssw0rd!",
                "name": "Strong",
            },
        )
        assert response.status_code == 201


class TestEmailValidation:
    """Tests de validación de emails."""

    def test_invalid_email_format_rejected(self, client):
        """Emails con formato inválido deben ser rechazados."""
        response = client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "ValidPass123", "name": "Test"},
        )
        assert response.status_code == 422
        assert "email" in response.json()["detail"][0]["msg"].lower()

    def test_disposable_email_rejected(self, client, monkeypatch):
        """Emails temporales deben ser bloqueados."""
        from app.config import settings
        monkeypatch.setattr(settings, "ENFORCE_STRONG_PASSWORDS", True)
        response = client.post(
            "/auth/register",
            json={
                "email": "test@tempmail.com",
                "password": "ValidPass123",
                "name": "Test",
            },
        )
        assert response.status_code == 422
        assert "temporal" in response.json()["detail"][0]["msg"].lower()

    def test_valid_email_accepted(self, client):
        """Email válido debe ser aceptado."""
        response = client.post(
            "/auth/register",
            json={
                "email": "valid@gmail.com",
                "password": "SecurePass123",
                "name": "Valid",
            },
        )
        assert response.status_code == 201


class TestRateLimitingAuth:
    """Tests de rate limiting en endpoints de auth."""

    def test_login_rate_limit(self, client):
        """
        Login debe tener rate limit estricto (5 intentos cada 5 min).
        Nota: este test solo verifica que el limit existe, no que se aplica
        (requeriría Redis habilitado).
        """
        from app.middleware.rate_limit import RateLimitMiddleware

        class FakeApp:
            pass

        middleware = RateLimitMiddleware(FakeApp())

        # Verificar que /auth/login tiene un límite específico
        limit = middleware._get_limit_for_path("/auth/login")
        assert limit is not None
        assert limit[0] == 5  # 5 requests
        assert limit[1] == 300  # cada 5 minutos

    def test_register_rate_limit(self, client):
        """Register debe tener rate limit (3/hora)."""
        from app.middleware.rate_limit import RateLimitMiddleware

        class FakeApp:
            pass

        middleware = RateLimitMiddleware(FakeApp())

        limit = middleware._get_limit_for_path("/auth/register")
        assert limit is not None
        assert limit[0] == 3  # 3 requests
        assert limit[1] == 3600  # por hora
