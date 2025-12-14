"""
Email service for sending emails using SMTP with Jinja2 templates.
Supports both HTML and plain text emails.
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from email_validator import validate_email, EmailNotValidError

from app.config import settings


class EmailService:
    """
    Service for sending emails with template support.

    Features:
    - Async email sending
    - HTML templates with Jinja2
    - Email validation
    - File attachments
    - Multiple recipients
    - CC and BCC support
    """

    def __init__(self):
        """Initialize email service with SMTP configuration"""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS

        # Setup Jinja2 environment for email templates
        templates_dir = Path(settings.EMAIL_TEMPLATES_DIR)
        if templates_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(templates_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            self.jinja_env = None
            print(f"Warning: Email templates directory not found: {templates_dir}")

    def _validate_email(self, email: str) -> bool:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError:
            return False

    def _create_message(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[tuple]] = None
    ) -> MIMEMultipart:
        """
        Create MIME message.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (fallback)
            cc: List of CC recipients
            bcc: List of BCC recipients
            attachments: List of (filename, content) tuples

        Returns:
            MIMEMultipart message object
        """
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{self.from_name} <{self.from_email}>"
        message['To'] = ', '.join(to)

        if cc:
            message['Cc'] = ', '.join(cc)

        # Add plain text version (fallback)
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            message.attach(text_part)

        # Add HTML version
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)

        # Add attachments
        if attachments:
            for filename, content in attachments:
                attachment = MIMEApplication(content)
                attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                message.attach(attachment)

        return message

    async def send_email(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[tuple]] = None
    ) -> bool:
        """
        Send email asynchronously.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (fallback)
            cc: List of CC recipients
            bcc: List of BCC recipients
            attachments: List of (filename, content) tuples

        Returns:
            True if email sent successfully, False otherwise

        Example:
            await email_service.send_email(
                to=["user@example.com"],
                subject="Welcome!",
                html_content="<h1>Hello!</h1>"
            )
        """
        # Validate all email addresses
        all_emails = to + (cc or []) + (bcc or [])
        for email in all_emails:
            if not self._validate_email(email):
                print(f"Invalid email address: {email}")
                return False

        # Check SMTP configuration
        if not self.smtp_user or not self.smtp_password:
            print("Error: SMTP credentials not configured")
            return False

        try:
            # Create message
            message = self._create_message(
                to=to,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                cc=cc,
                bcc=bcc,
                attachments=attachments
            )

            # All recipients (to + cc + bcc)
            recipients = to + (cc or []) + (bcc or [])

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=self.use_tls,
                recipients=recipients
            )

            print(f"Email sent successfully to: {', '.join(to)}")
            return True

        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render email template with context.

        Args:
            template_name: Name of the template file (e.g., "welcome.html")
            context: Dictionary with template variables

        Returns:
            Rendered HTML string

        Example:
            html = email_service.render_template(
                "welcome.html",
                {"name": "John", "verification_url": "https://..."}
            )
        """
        if not self.jinja_env:
            raise ValueError("Email templates directory not configured")

        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    async def send_template_email(
        self,
        to: List[str],
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send email using a template.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            template_name: Name of the template file
            context: Dictionary with template variables
            cc: List of CC recipients
            bcc: List of BCC recipients

        Returns:
            True if email sent successfully, False otherwise

        Example:
            await email_service.send_template_email(
                to=["user@example.com"],
                subject="Welcome to Our Platform",
                template_name="welcome.html",
                context={"name": "John", "url": "https://..."}
            )
        """
        try:
            html_content = self.render_template(template_name, context)
            return await self.send_email(
                to=to,
                subject=subject,
                html_content=html_content,
                cc=cc,
                bcc=bcc
            )
        except Exception as e:
            print(f"Error sending template email: {str(e)}")
            return False

    # === Pre-built email templates ===

    async def send_welcome_email(self, to: str, name: str, verification_url: Optional[str] = None) -> bool:
        """
        Send welcome email to new user.

        Args:
            to: Recipient email address
            name: User's name
            verification_url: Optional email verification URL

        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=[to],
            subject=f"¡Bienvenido a {self.from_name}!",
            template_name="welcome.html",
            context={
                "name": name,
                "verification_url": verification_url,
                "app_name": self.from_name
            }
        )

    async def send_verification_email(self, to: str, name: str, verification_url: str) -> bool:
        """
        Send email verification link.

        Args:
            to: Recipient email address
            name: User's name
            verification_url: Email verification URL

        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=[to],
            subject="Verifica tu correo electrónico",
            template_name="verify_email.html",
            context={
                "name": name,
                "verification_url": verification_url,
                "app_name": self.from_name
            }
        )

    async def send_password_reset_email(self, to: str, name: str, reset_url: str) -> bool:
        """
        Send password reset link.

        Args:
            to: Recipient email address
            name: User's name
            reset_url: Password reset URL

        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=[to],
            subject="Recuperar contraseña",
            template_name="password_reset.html",
            context={
                "name": name,
                "reset_url": reset_url,
                "app_name": self.from_name
            }
        )

    async def send_notification_email(
        self,
        to: str,
        name: str,
        notification_title: str,
        notification_body: str
    ) -> bool:
        """
        Send generic notification email.

        Args:
            to: Recipient email address
            name: User's name
            notification_title: Title of the notification
            notification_body: Body content of the notification

        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=[to],
            subject=notification_title,
            template_name="notification.html",
            context={
                "name": name,
                "title": notification_title,
                "body": notification_body,
                "app_name": self.from_name
            }
        )


# Singleton instance
email_service = EmailService()
