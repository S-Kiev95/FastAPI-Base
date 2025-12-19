"""
Webhook delivery tasks for ARQ workers

Tasks:
- deliver_webhook: Deliver webhook to subscription URL with retries
"""
from typing import Dict, Any
from datetime import datetime

from app.database import SessionLocal
from app.services.webhook_service import webhook_service
from app.services.queue_service import queue_service
from app.utils.logger import get_structured_logger, LogContext

logger = get_structured_logger(__name__)


async def deliver_webhook(
    ctx: Dict[str, Any],
    subscription_id: int,
    event_type: str,
    payload: Dict[str, Any],
    attempt_number: int = 1
) -> Dict[str, Any]:
    """
    Deliver webhook to subscription URL

    Args:
        ctx: ARQ context
        subscription_id: Webhook subscription ID
        event_type: Type of event
        payload: Event payload
        attempt_number: Current attempt number (for retries)

    Returns:
        Dict with delivery result
    """
    job_id = ctx.get("job_id")

    with LogContext(job_id=job_id, subscription_id=subscription_id, task="deliver_webhook"):
        logger.info("Starting webhook delivery",
                   event_type=event_type,
                   attempt=attempt_number)

        db = SessionLocal()
        try:
            # Deliver webhook
            delivery = await webhook_service.deliver_webhook(
                db=db,
                subscription_id=subscription_id,
                event_type=event_type,
                payload=payload,
                attempt_number=attempt_number
            )

            # If delivery failed and will retry, enqueue retry task
            if not delivery.success and delivery.will_retry:
                delay_seconds = int((delivery.next_retry_at - datetime.utcnow()).total_seconds())

                logger.info("Scheduling webhook retry",
                           delivery_id=delivery.id,
                           next_attempt=attempt_number + 1,
                           delay_seconds=delay_seconds)

                # Enqueue retry with delay
                await queue_service.enqueue_webhook_delivery(
                    subscription_id=subscription_id,
                    event_type=event_type,
                    payload=payload,
                    attempt_number=attempt_number + 1
                )

            result = {
                "delivery_id": delivery.id,
                "subscription_id": subscription_id,
                "event_type": event_type,
                "success": delivery.success,
                "status_code": delivery.status_code,
                "attempt_number": attempt_number,
                "will_retry": delivery.will_retry
            }

            if delivery.success:
                logger.info("Webhook delivered successfully",
                           delivery_id=delivery.id,
                           status_code=delivery.status_code,
                           duration_ms=delivery.duration_ms)
            else:
                logger.warning("Webhook delivery failed",
                              delivery_id=delivery.id,
                              error=delivery.error_message,
                              will_retry=delivery.will_retry)

            return result

        except Exception as e:
            logger.error("Webhook delivery task failed", error=str(e))
            raise

        finally:
            db.close()
