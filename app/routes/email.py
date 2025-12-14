"""
Email routes for sending emails.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.services.email_service import email_service


router = APIRouter(prefix="/email", tags=["email"])


# === Schemas ===

class EmailRequest(BaseModel):
    """Schema for sending a basic email"""
    to: List[EmailStr]
    subject: str
    html_content: str
    text_content: Optional[str] = None
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None


class TemplateEmailRequest(BaseModel):
    """Schema for sending a template-based email"""
    to: List[EmailStr]
    subject: str
    template_name: str
    context: dict
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None


class WelcomeEmailRequest(BaseModel):
    """Schema for sending welcome email"""
    to: EmailStr
    name: str
    verification_url: Optional[str] = None


class VerificationEmailRequest(BaseModel):
    """Schema for sending verification email"""
    to: EmailStr
    name: str
    verification_url: str


class PasswordResetEmailRequest(BaseModel):
    """Schema for sending password reset email"""
    to: EmailStr
    name: str
    reset_url: str


class NotificationEmailRequest(BaseModel):
    """Schema for sending notification email"""
    to: EmailStr
    name: str
    notification_title: str
    notification_body: str


# === Routes ===

@router.post("/send")
async def send_email(request: EmailRequest):
    """
    Send a basic email with custom HTML content.

    Example:
    ```json
    {
        "to": ["user@example.com"],
        "subject": "Test Email",
        "html_content": "<h1>Hello World!</h1>",
        "text_content": "Hello World!"
    }
    ```
    """
    success = await email_service.send_email(
        to=request.to,
        subject=request.subject,
        html_content=request.html_content,
        text_content=request.text_content,
        cc=request.cc,
        bcc=request.bcc
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send email. Check SMTP configuration."
        )

    return {
        "message": "Email sent successfully",
        "recipients": request.to
    }


@router.post("/send-template")
async def send_template_email(request: TemplateEmailRequest):
    """
    Send an email using a Jinja2 template.

    Example:
    ```json
    {
        "to": ["user@example.com"],
        "subject": "Welcome!",
        "template_name": "welcome.html",
        "context": {
            "name": "John",
            "app_name": "My App"
        }
    }
    ```
    """
    success = await email_service.send_template_email(
        to=request.to,
        subject=request.subject,
        template_name=request.template_name,
        context=request.context,
        cc=request.cc,
        bcc=request.bcc
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send template email. Check template and SMTP configuration."
        )

    return {
        "message": "Template email sent successfully",
        "recipients": request.to,
        "template": request.template_name
    }


@router.post("/send-welcome")
async def send_welcome_email(request: WelcomeEmailRequest):
    """
    Send welcome email to a new user.

    Example:
    ```json
    {
        "to": "newuser@example.com",
        "name": "John Doe",
        "verification_url": "https://example.com/verify?token=abc123"
    }
    ```
    """
    success = await email_service.send_welcome_email(
        to=request.to,
        name=request.name,
        verification_url=request.verification_url
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send welcome email"
        )

    return {
        "message": "Welcome email sent successfully",
        "recipient": request.to
    }


@router.post("/send-verification")
async def send_verification_email(request: VerificationEmailRequest):
    """
    Send email verification link.

    Example:
    ```json
    {
        "to": "user@example.com",
        "name": "John Doe",
        "verification_url": "https://example.com/verify?token=abc123"
    }
    ```
    """
    success = await email_service.send_verification_email(
        to=request.to,
        name=request.name,
        verification_url=request.verification_url
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send verification email"
        )

    return {
        "message": "Verification email sent successfully",
        "recipient": request.to
    }


@router.post("/send-password-reset")
async def send_password_reset_email(request: PasswordResetEmailRequest):
    """
    Send password reset link.

    Example:
    ```json
    {
        "to": "user@example.com",
        "name": "John Doe",
        "reset_url": "https://example.com/reset-password?token=xyz789"
    }
    ```
    """
    success = await email_service.send_password_reset_email(
        to=request.to,
        name=request.name,
        reset_url=request.reset_url
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send password reset email"
        )

    return {
        "message": "Password reset email sent successfully",
        "recipient": request.to
    }


@router.post("/send-notification")
async def send_notification_email(request: NotificationEmailRequest):
    """
    Send a notification email.

    Example:
    ```json
    {
        "to": "user@example.com",
        "name": "John Doe",
        "notification_title": "New Feature Available",
        "notification_body": "We've just released a new feature that you might find useful..."
    }
    ```
    """
    success = await email_service.send_notification_email(
        to=request.to,
        name=request.name,
        notification_title=request.notification_title,
        notification_body=request.notification_body
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send notification email"
        )

    return {
        "message": "Notification email sent successfully",
        "recipient": request.to
    }


@router.get("/templates")
async def list_templates():
    """
    List available email templates.
    """
    return {
        "templates": [
            {
                "name": "welcome.html",
                "description": "Welcome email for new users",
                "variables": ["name", "verification_url", "app_name"]
            },
            {
                "name": "verify_email.html",
                "description": "Email verification link",
                "variables": ["name", "verification_url", "app_name"]
            },
            {
                "name": "password_reset.html",
                "description": "Password reset link",
                "variables": ["name", "reset_url", "app_name"]
            },
            {
                "name": "notification.html",
                "description": "Generic notification email",
                "variables": ["name", "title", "body", "app_name"]
            }
        ]
    }


@router.get("/config")
async def get_email_config():
    """
    Get current email configuration (without sensitive data).
    """
    from app.config import settings

    return {
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "from_email": settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
        "from_name": settings.SMTP_FROM_NAME,
        "use_tls": settings.SMTP_USE_TLS,
        "configured": bool(settings.SMTP_USER and settings.SMTP_PASSWORD)
    }
