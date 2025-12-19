"""
Webhook helper utilities

Provides easy-to-use functions for triggering webhooks from anywhere in the application.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.services.webhook_service import webhook_service
from app.utils.logger import get_structured_logger

logger = get_structured_logger(__name__)


async def trigger_webhook(
    db: Session,
    event_type: str,
    data: Dict[str, Any]
) -> int:
    """
    Trigger a webhook event

    Convenience function to trigger webhooks from anywhere in the application.

    Args:
        db: Database session
        event_type: Event type (e.g., "user.created", "task.completed")
        data: Event data payload

    Returns:
        Number of webhooks triggered

    Example:
        ```python
        from app.utils.webhooks import trigger_webhook

        # In your endpoint
        user = create_user(user_data)

        # Trigger webhook
        await trigger_webhook(
            db=db,
            event_type="user.created",
            data={
                "user_id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat()
            }
        )
        ```
    """
    try:
        count = await webhook_service.trigger_event(
            db=db,
            event_type=event_type,
            data=data
        )
        return count
    except Exception as e:
        logger.error("Failed to trigger webhook", event_type=event_type, error=str(e))
        # Don't raise - webhooks should not break main functionality
        return 0
