"""Tests del EmailService: rendering de templates, enqueue fallback, métodos pre-built."""
from unittest.mock import patch, AsyncMock, MagicMock
import pytest


class TestEmailTemplateRendering:
    """Verifica que los templates Jinja2 se renderizan correctamente."""

    def test_render_welcome_template(self):
        from app.services.email_service import email_service

        html = email_service.render_template("welcome.html", {
            "name": "Juan",
            "verification_url": "https://example.com/verify",
            "app_name": "TestApp",
        })
        assert "Juan" in html
        assert "https://example.com/verify" in html

    def test_render_verify_email_template(self):
        from app.services.email_service import email_service

        html = email_service.render_template("verify_email.html", {
            "name": "María",
            "verification_url": "https://example.com/verify/abc",
            "app_name": "TestApp",
        })
        assert "María" in html
        assert "https://example.com/verify/abc" in html

    def test_render_password_reset_template(self):
        from app.services.email_service import email_service

        html = email_service.render_template("password_reset.html", {
            "name": "Pedro",
            "reset_url": "https://example.com/reset/xyz",
            "app_name": "TestApp",
        })
        assert "Pedro" in html
        assert "https://example.com/reset/xyz" in html

    def test_render_invitation_template(self):
        from app.services.email_service import email_service

        html = email_service.render_template("invitation.html", {
            "org_name": "Mi Empresa",
            "inviter_name": "Carlos",
            "role": "admin",
            "accept_url": "https://example.com/accept/tok",
            "expire_hours": 48,
            "app_name": "TestApp",
        })
        assert "Mi Empresa" in html
        assert "Carlos" in html
        assert "admin" in html

    def test_render_invoice_template(self):
        from app.services.email_service import email_service

        html = email_service.render_template("invoice.html", {
            "name": "Ana",
            "invoice_number": "INV-2026-001",
            "amount": "$99.00",
            "due_date": "2026-05-01",
            "invoice_url": "https://example.com/invoices/1",
            "app_name": "TestApp",
        })
        assert "INV-2026-001" in html
        assert "$99.00" in html
        assert "2026-05-01" in html

    def test_render_plan_change_template(self):
        from app.services.email_service import email_service

        html = email_service.render_template("plan_change.html", {
            "name": "Luis",
            "old_plan": "free",
            "new_plan": "pro",
            "effective_date": "2026-04-01",
            "app_name": "TestApp",
        })
        assert "free" in html
        assert "pro" in html
        assert "2026-04-01" in html

    def test_render_notification_template(self):
        from app.services.email_service import email_service

        html = email_service.render_template("notification.html", {
            "name": "Eva",
            "title": "Alerta importante",
            "body": "Tu póliza vence pronto",
            "app_name": "TestApp",
        })
        assert "Eva" in html
        assert "Alerta importante" in html

    def test_render_nonexistent_template_raises(self):
        from app.services.email_service import email_service

        with pytest.raises(Exception):
            email_service.render_template("nonexistent.html", {})


class TestEmailEnqueue:
    """Verifica que enqueue() rutea correctamente según REDIS_ENABLED."""

    @pytest.mark.asyncio
    async def test_enqueue_falls_back_to_direct_when_no_redis(self):
        """Sin Redis, enqueue() llama a send_email directamente."""
        from app.services.email_service import email_service

        with patch.object(email_service, "send_email", new_callable=AsyncMock, return_value=True) as mock_send:
            with patch("app.services.email_service.settings") as mock_settings:
                mock_settings.REDIS_ENABLED = False
                mock_settings.EMAIL_TEMPLATES_DIR = "app/templates/emails"
                mock_settings.SMTP_FROM_NAME = "Test"

                result = await email_service.enqueue(
                    to="test@example.com",
                    subject="Test",
                    template_name="welcome.html",
                    context={"name": "Test", "app_name": "Test"},
                )

                assert result is True
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_renders_template_before_sending(self):
        """enqueue() renderiza el template antes de encolar/enviar."""
        from app.services.email_service import email_service

        with patch.object(email_service, "send_email", new_callable=AsyncMock, return_value=True) as mock_send:
            with patch("app.services.email_service.settings") as mock_settings:
                mock_settings.REDIS_ENABLED = False

                await email_service.enqueue(
                    to="test@example.com",
                    subject="Bienvenido",
                    template_name="welcome.html",
                    context={"name": "Juan", "app_name": "TestApp"},
                )

                # Verificar que el HTML renderizado contiene el nombre
                call_args = mock_send.call_args
                html_content = call_args.kwargs.get("html_content", call_args[1].get("html_content", ""))
                assert "Juan" in html_content


class TestPreBuiltMethods:
    """Verifica que los métodos pre-built llaman a enqueue por defecto."""

    @pytest.mark.asyncio
    async def test_send_verification_email_uses_enqueue(self):
        from app.services.email_service import email_service

        with patch.object(email_service, "enqueue", new_callable=AsyncMock, return_value=True) as mock:
            await email_service.send_verification_email(
                to="user@test.com",
                name="User",
                verification_url="https://example.com/verify",
                queue=True,
            )
            mock.assert_called_once()
            assert mock.call_args.kwargs["template_name"] == "verify_email.html"

    @pytest.mark.asyncio
    async def test_send_password_reset_uses_enqueue(self):
        from app.services.email_service import email_service

        with patch.object(email_service, "enqueue", new_callable=AsyncMock, return_value=True) as mock:
            await email_service.send_password_reset_email(
                to="user@test.com",
                name="User",
                reset_url="https://example.com/reset",
                queue=True,
            )
            mock.assert_called_once()
            assert mock.call_args.kwargs["template_name"] == "password_reset.html"

    @pytest.mark.asyncio
    async def test_send_invitation_uses_enqueue(self):
        from app.services.email_service import email_service

        with patch.object(email_service, "enqueue", new_callable=AsyncMock, return_value=True) as mock:
            await email_service.send_invitation_email(
                to="invitee@test.com",
                org_name="Mi Org",
                inviter_name="Admin",
                role="member",
                accept_url="https://example.com/accept",
                queue=True,
            )
            mock.assert_called_once()
            assert mock.call_args.kwargs["template_name"] == "invitation.html"

    @pytest.mark.asyncio
    async def test_send_invoice_uses_enqueue(self):
        from app.services.email_service import email_service

        with patch.object(email_service, "enqueue", new_callable=AsyncMock, return_value=True) as mock:
            await email_service.send_invoice_email(
                to="user@test.com",
                name="User",
                invoice_number="INV-001",
                amount="$50",
                due_date="2026-05-01",
                invoice_url="https://example.com/inv/1",
                queue=True,
            )
            mock.assert_called_once()
            assert mock.call_args.kwargs["template_name"] == "invoice.html"

    @pytest.mark.asyncio
    async def test_send_plan_change_uses_enqueue(self):
        from app.services.email_service import email_service

        with patch.object(email_service, "enqueue", new_callable=AsyncMock, return_value=True) as mock:
            await email_service.send_plan_change_email(
                to="user@test.com",
                name="User",
                old_plan="free",
                new_plan="pro",
                effective_date="2026-04-01",
                queue=True,
            )
            mock.assert_called_once()
            assert mock.call_args.kwargs["template_name"] == "plan_change.html"

    @pytest.mark.asyncio
    async def test_send_with_queue_false_uses_direct(self):
        """queue=False usa send_template_email en vez de enqueue."""
        from app.services.email_service import email_service

        with patch.object(email_service, "send_template_email", new_callable=AsyncMock, return_value=True) as mock:
            await email_service.send_notification_email(
                to="user@test.com",
                name="User",
                notification_title="Alerta",
                notification_body="Contenido",
                queue=False,
            )
            mock.assert_called_once()


class TestEmailValidation:
    """Verifica validación de emails."""

    def test_valid_email(self):
        from app.services.email_service import email_service
        assert email_service._validate_email("user@example.com") is True

    def test_invalid_email(self):
        from app.services.email_service import email_service
        assert email_service._validate_email("not-an-email") is False

    def test_empty_email(self):
        from app.services.email_service import email_service
        assert email_service._validate_email("") is False
