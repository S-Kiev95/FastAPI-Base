"""
Email service para envío de correos con SMTP + Jinja2.
Soporta envío directo y encolado via ARQ para delivery en background.
"""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from email_validator import validate_email, EmailNotValidError

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio de email con soporte de templates y cola ARQ.

    Modos de envío:
    - Directo: await email_service.send_email(...)
    - Queue:   await email_service.enqueue(...) — requiere REDIS_ENABLED=True
    """

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS

        # Jinja2 templates
        templates_dir = Path(settings.EMAIL_TEMPLATES_DIR)
        if templates_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(templates_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            self.jinja_env = None
            logger.warning(f"Email templates directory not found: {templates_dir}")

    # ---- Validación ----

    def _validate_email(self, email: str) -> bool:
        try:
            validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError:
            return False

    # ---- Construcción de mensaje MIME ----

    def _create_message(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[tuple]] = None,
    ) -> MIMEMultipart:
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{self.from_name} <{self.from_email}>"
        message['To'] = ', '.join(to)

        if cc:
            message['Cc'] = ', '.join(cc)

        if text_content:
            message.attach(MIMEText(text_content, 'plain', 'utf-8'))

        message.attach(MIMEText(html_content, 'html', 'utf-8'))

        if attachments:
            for filename, content in attachments:
                attachment = MIMEApplication(content)
                attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                message.attach(attachment)

        return message

    # ---- Envío directo ----

    async def send_email(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[tuple]] = None,
    ) -> bool:
        """Envía email directamente via SMTP (síncrono en el request)."""
        all_emails = to + (cc or []) + (bcc or [])
        for email in all_emails:
            if not self._validate_email(email):
                logger.warning(f"Invalid email address: {email}")
                return False

        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured, email skipped")
            return False

        try:
            message = self._create_message(
                to=to, subject=subject, html_content=html_content,
                text_content=text_content, cc=cc, bcc=bcc, attachments=attachments,
            )
            recipients = to + (cc or []) + (bcc or [])

            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=self.use_tls,
                recipients=recipients,
            )

            logger.info(f"Email sent to: {', '.join(to)}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    # ---- Rendering de templates ----

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Renderiza un template Jinja2 y retorna HTML."""
        if not self.jinja_env:
            raise ValueError("Email templates directory not configured")
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    # ---- Envío con template (directo) ----

    async def send_template_email(
        self,
        to: str | List[str],
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """Renderiza template y envía directamente."""
        if isinstance(to, str):
            to = [to]
        try:
            html_content = self.render_template(template_name, context)
            return await self.send_email(
                to=to, subject=subject, html_content=html_content,
                cc=cc, bcc=bcc,
            )
        except Exception as e:
            logger.error(f"Error sending template email: {e}")
            return False

    # ---- Encolado via ARQ ----

    async def enqueue(
        self,
        to: str | List[str],
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> bool:
        """
        Encola email para envío en background via ARQ.

        Si Redis no está habilitado, envía directamente como fallback.
        Renderiza el template antes de encolar para no depender de Jinja2 en el worker.
        """
        if isinstance(to, str):
            to = [to]

        # Renderizar template ANTES de encolar (evita dependencia de templates en worker)
        try:
            html_content = self.render_template(template_name, context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            return False

        # Si Redis está habilitado, encolar via ARQ
        if settings.REDIS_ENABLED:
            try:
                from arq import create_pool
                from arq.connections import RedisSettings

                redis_settings = RedisSettings(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    database=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD or None,
                )
                pool = await create_pool(redis_settings)

                for recipient in to:
                    await pool.enqueue_job(
                        "send_single_email",
                        to_email=recipient,
                        subject=subject,
                        body=subject,  # Plain text fallback
                        html_body=html_content,
                        user_id=user_id,
                    )

                await pool.close()
                logger.info(f"Email enqueued for: {', '.join(to)}")
                return True

            except Exception as e:
                logger.warning(f"ARQ enqueue failed, sending directly: {e}")
                # Fallback a envío directo
                return await self.send_email(
                    to=to, subject=subject, html_content=html_content,
                )
        else:
            # Sin Redis: envío directo
            return await self.send_email(
                to=to, subject=subject, html_content=html_content,
            )

    # ---- Pre-built email methods ----

    async def send_welcome_email(
        self, to: str, name: str,
        verification_url: Optional[str] = None,
        queue: bool = True,
    ) -> bool:
        method = self.enqueue if queue else self.send_template_email
        return await method(
            to=to,
            subject=f"¡Bienvenido a {self.from_name}!",
            template_name="welcome.html",
            context={"name": name, "verification_url": verification_url, "app_name": self.from_name},
        )

    async def send_verification_email(
        self, to: str, name: str, verification_url: str,
        queue: bool = True,
    ) -> bool:
        method = self.enqueue if queue else self.send_template_email
        return await method(
            to=to,
            subject="Verifica tu correo electrónico",
            template_name="verify_email.html",
            context={"name": name, "verification_url": verification_url, "app_name": self.from_name},
        )

    async def send_password_reset_email(
        self, to: str, name: str, reset_url: str,
        queue: bool = True,
    ) -> bool:
        method = self.enqueue if queue else self.send_template_email
        return await method(
            to=to,
            subject="Recuperar contraseña",
            template_name="password_reset.html",
            context={"name": name, "reset_url": reset_url, "app_name": self.from_name},
        )

    async def send_invitation_email(
        self, to: str, org_name: str, inviter_name: str,
        role: str, accept_url: str,
        queue: bool = True,
    ) -> bool:
        method = self.enqueue if queue else self.send_template_email
        return await method(
            to=to,
            subject=f"Invitación a {org_name}",
            template_name="invitation.html",
            context={
                "org_name": org_name,
                "inviter_name": inviter_name,
                "role": role,
                "accept_url": accept_url,
                "expire_hours": settings.INVITATION_EXPIRE_HOURS,
                "app_name": settings.API_TITLE,
            },
        )

    async def send_notification_email(
        self, to: str, name: str,
        notification_title: str, notification_body: str,
        queue: bool = True,
    ) -> bool:
        method = self.enqueue if queue else self.send_template_email
        return await method(
            to=to,
            subject=notification_title,
            template_name="notification.html",
            context={
                "name": name,
                "title": notification_title,
                "body": notification_body,
                "app_name": self.from_name,
            },
        )

    async def send_invoice_email(
        self, to: str, name: str,
        invoice_number: str, amount: str, due_date: str,
        invoice_url: str,
        queue: bool = True,
    ) -> bool:
        method = self.enqueue if queue else self.send_template_email
        return await method(
            to=to,
            subject=f"Factura {invoice_number}",
            template_name="invoice.html",
            context={
                "name": name,
                "invoice_number": invoice_number,
                "amount": amount,
                "due_date": due_date,
                "invoice_url": invoice_url,
                "app_name": self.from_name,
            },
        )

    async def send_plan_change_email(
        self, to: str, name: str,
        old_plan: str, new_plan: str,
        effective_date: str,
        queue: bool = True,
    ) -> bool:
        method = self.enqueue if queue else self.send_template_email
        return await method(
            to=to,
            subject=f"Tu plan ha cambiado a {new_plan}",
            template_name="plan_change.html",
            context={
                "name": name,
                "old_plan": old_plan,
                "new_plan": new_plan,
                "effective_date": effective_date,
                "app_name": self.from_name,
            },
        )


# Singleton
email_service = EmailService()
