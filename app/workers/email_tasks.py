"""
Email sending tasks for ARQ workers

Tasks:
- send_single_email: Send one email
- send_bulk_emails: Send multiple emails with rate limiting
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings
from app.utils.logger import get_structured_logger, LogContext

logger = get_structured_logger(__name__)


async def send_single_email(
    ctx: Dict[str, Any],
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    Send a single email

    Args:
        ctx: ARQ context
        to_email: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: HTML email body (optional)
        user_id: ID of user who triggered this (optional)

    Returns:
        Dict with send status
    """
    job_id = ctx.get("job_id")
    with LogContext(job_id=job_id, user_id=user_id, task="send_single_email"):
        logger.info("Starting email sending", to_email=to_email, subject=subject)

        await _update_task_status(ctx, "processing", progress=10)

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg['To'] = to_email

            # Attach plain text
            msg.attach(MIMEText(body, 'plain'))

            # Attach HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            await _update_task_status(ctx, "processing", progress=30)

            # Connect to SMTP server and send
            if not settings.SMTP_HOST or not settings.SMTP_USER:
                logger.warning("SMTP not configured, email skipped (dev mode)", to_email=to_email)
                result = {
                    "to_email": to_email,
                    "subject": subject,
                    "status": "skipped",
                    "message": "SMTP not configured",
                }
            else:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    if settings.SMTP_USE_TLS:
                        server.starttls()

                    await _update_task_status(ctx, "processing", progress=60)

                    if settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

                    await _update_task_status(ctx, "processing", progress=80)

                    server.send_message(msg)

                result = {
                    "to_email": to_email,
                    "subject": subject,
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat(),
                }

            await _update_task_status(ctx, "processing", progress=100)

            # Publish notification
            await _publish_notification(ctx, user_id, "email_sent", result)

            logger.info("Email sent successfully", to_email=to_email, status=result["status"])
            return result

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error("Email sending failed", to_email=to_email, error=str(e))
            await _publish_notification(ctx, user_id, "email_failed", {"to_email": to_email, "error": error_msg})
            raise


async def send_bulk_emails(
    ctx: Dict[str, Any],
    emails: List[Dict[str, str]],
    rate_limit: int = 10,
    user_id: int = None
) -> Dict[str, Any]:
    """
    Send multiple emails with rate limiting

    Args:
        ctx: ARQ context
        emails: List of dicts with 'to_email', 'subject', 'body', 'html_body'
        rate_limit: Max emails per minute
        user_id: ID of user who triggered this

    Returns:
        Dict with sending statistics
    """
    total = len(emails)
    job_id = ctx.get("job_id")

    with LogContext(job_id=job_id, user_id=user_id, task="send_bulk_emails"):
        logger.info("Starting bulk email sending", total_emails=total, rate_limit=rate_limit)

        await _update_task_status(ctx, "processing", progress=0)

        results = {
            "total": total,
            "sent": 0,
            "failed": 0,
            "errors": [],
        }

        delay = 60.0 / rate_limit  # Delay between emails in seconds

        for idx, email_data in enumerate(emails):
            try:
                # Send individual email
                await send_single_email(
                    ctx,
                    to_email=email_data["to_email"],
                    subject=email_data["subject"],
                    body=email_data["body"],
                    html_body=email_data.get("html_body"),
                    user_id=user_id
                )
                results["sent"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "to_email": email_data["to_email"],
                    "error": str(e)
                })

            # Update progress
            progress = int((idx + 1) / total * 100)
            await _update_task_status(ctx, "processing", progress=progress)

            # Publish intermediate update every 10 emails
            if (idx + 1) % 10 == 0:
                await _publish_notification(ctx, user_id, "bulk_email_progress", {
                    "sent": results["sent"],
                    "failed": results["failed"],
                    "total": total,
                    "progress": progress,
                })
                logger.info("Bulk email progress update",
                           sent=results["sent"],
                           failed=results["failed"],
                           progress=progress)

            # Rate limiting: wait between emails
            if idx < total - 1:  # Don't wait after last email
                await asyncio.sleep(delay)

        # Final notification
        await _publish_notification(ctx, user_id, "bulk_email_completed", results)

        logger.info("Bulk email completed",
                   sent=results["sent"],
                   failed=results["failed"],
                   total=total)
        return results


# Helper functions

async def _update_task_status(ctx: Dict[str, Any], status: str, progress: int = None):
    """Update task status in Redis"""
    job_id = ctx.get("job_id")
    if not job_id:
        return

    redis = ctx["redis"]

    data = {"status": status}
    if progress is not None:
        data["progress"] = progress
    data["updated_at"] = datetime.utcnow().isoformat()

    # Store in Redis with TTL of 1 hour
    await redis.setex(
        f"task_status:{job_id}",
        3600,  # 1 hour TTL
        str(data)
    )


async def _publish_notification(
    ctx: Dict[str, Any],
    user_id: int,
    event_type: str,
    data: Dict[str, Any]
):
    """Publish notification via Redis Pub/Sub for WebSocket relay"""
    if user_id is None:
        return

    redis = ctx["redis"]
    job_id = ctx.get("job_id")

    notification = {
        "job_id": job_id,
        "user_id": user_id,
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Publish to channel that WebSocket handler will listen to
    channel = f"task_notifications:{user_id}"
    await redis.publish(channel, str(notification))

    logger.debug("Published notification", channel=channel, event_type=event_type)
