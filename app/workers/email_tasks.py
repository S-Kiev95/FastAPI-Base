"""
Tareas ARQ de email — usan EmailService para envío real.

Tasks:
- send_single_email: Envía un email (HTML pre-renderizado)
- send_bulk_emails: Envía múltiples emails con rate limiting
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from app.config import settings
from app.utils.logger import get_structured_logger, LogContext

logger = get_structured_logger(__name__)


async def send_single_email(
    ctx: Dict[str, Any],
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None,
    user_id: int = None,
) -> Dict[str, Any]:
    """
    Envía un email individual.

    El html_body ya viene renderizado desde EmailService.enqueue().
    """
    job_id = ctx.get("job_id")
    with LogContext(job_id=job_id, user_id=user_id, task="send_single_email"):
        logger.info("Starting email sending", to_email=to_email, subject=subject)

        await _update_task_status(ctx, "processing", progress=10)

        try:
            # Verificar configuración SMTP
            if not settings.SMTP_HOST or not settings.SMTP_USER:
                logger.warning("SMTP not configured, email skipped", to_email=to_email)
                result = {
                    "to_email": to_email,
                    "subject": subject,
                    "status": "skipped",
                    "message": "SMTP not configured",
                }
                await _update_task_status(ctx, "completed", progress=100)
                await _publish_notification(ctx, user_id, "email_sent", result)
                return result

            await _update_task_status(ctx, "processing", progress=30)

            # Usar EmailService para envío real
            from app.services.email_service import email_service

            content = html_body or f"<p>{body}</p>"
            success = await email_service.send_email(
                to=[to_email],
                subject=subject,
                html_content=content,
                text_content=body,
            )

            await _update_task_status(ctx, "processing", progress=100)

            result = {
                "to_email": to_email,
                "subject": subject,
                "status": "sent" if success else "failed",
                "sent_at": datetime.utcnow().isoformat(),
            }

            event = "email_sent" if success else "email_failed"
            await _publish_notification(ctx, user_id, event, result)

            logger.info("Email task completed", to_email=to_email, status=result["status"])
            return result

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error("Email sending failed", to_email=to_email, error=str(e))
            await _publish_notification(ctx, user_id, "email_failed", {
                "to_email": to_email, "error": error_msg,
            })
            raise


async def send_bulk_emails(
    ctx: Dict[str, Any],
    emails: List[Dict[str, str]],
    rate_limit: int = 10,
    user_id: int = None,
) -> Dict[str, Any]:
    """
    Envía múltiples emails con rate limiting.

    Args:
        emails: Lista de dicts con 'to_email', 'subject', 'body', 'html_body'
        rate_limit: Máximo de emails por minuto
    """
    total = len(emails)
    job_id = ctx.get("job_id")

    with LogContext(job_id=job_id, user_id=user_id, task="send_bulk_emails"):
        logger.info("Starting bulk email", total_emails=total, rate_limit=rate_limit)

        await _update_task_status(ctx, "processing", progress=0)

        results = {"total": total, "sent": 0, "failed": 0, "errors": []}
        delay = 60.0 / rate_limit

        for idx, email_data in enumerate(emails):
            try:
                await send_single_email(
                    ctx,
                    to_email=email_data["to_email"],
                    subject=email_data["subject"],
                    body=email_data["body"],
                    html_body=email_data.get("html_body"),
                    user_id=user_id,
                )
                results["sent"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "to_email": email_data["to_email"],
                    "error": str(e),
                })

            progress = int((idx + 1) / total * 100)
            await _update_task_status(ctx, "processing", progress=progress)

            if (idx + 1) % 10 == 0:
                await _publish_notification(ctx, user_id, "bulk_email_progress", {
                    "sent": results["sent"],
                    "failed": results["failed"],
                    "total": total,
                    "progress": progress,
                })

            if idx < total - 1:
                await asyncio.sleep(delay)

        await _publish_notification(ctx, user_id, "bulk_email_completed", results)
        logger.info("Bulk email completed", sent=results["sent"], failed=results["failed"])
        return results


# ---- Helpers ----

async def _update_task_status(ctx: Dict[str, Any], status: str, progress: int = None):
    """Actualiza estado del job en Redis."""
    job_id = ctx.get("job_id")
    if not job_id:
        return

    redis = ctx.get("redis")
    if not redis:
        return

    data = {"status": status}
    if progress is not None:
        data["progress"] = progress
    data["updated_at"] = datetime.utcnow().isoformat()

    await redis.setex(f"task_status:{job_id}", 3600, str(data))


async def _publish_notification(
    ctx: Dict[str, Any],
    user_id: int,
    event_type: str,
    data: Dict[str, Any],
):
    """Publica notificación via Redis Pub/Sub para relay WebSocket."""
    if user_id is None:
        return

    redis = ctx.get("redis")
    if not redis:
        return

    job_id = ctx.get("job_id")
    notification = {
        "job_id": job_id,
        "user_id": user_id,
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    channel = f"task_notifications:{user_id}"
    await redis.publish(channel, str(notification))
    logger.debug("Published notification", channel=channel, event_type=event_type)
