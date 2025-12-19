"""
Webhook management endpoints

Allows users to manage webhook subscriptions, view delivery logs, and test webhooks.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.services.webhook_service import webhook_service
from app.schemas.webhook import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
    WebhookSubscriptionResponse,
    WebhookDeliveryResponse,
    WebhookTest,
    WebhookTestResult,
    WebhookStats
)
from app.utils.logger import get_structured_logger

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_structured_logger(__name__)


# Subscription management

@router.post("/subscriptions", response_model=WebhookSubscriptionResponse, status_code=201)
async def create_webhook_subscription(
    subscription_data: WebhookSubscriptionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new webhook subscription

    Subscribe to events and receive HTTP POST requests when they occur.

    **Required fields:**
    - `name`: Friendly name for this webhook
    - `url`: Destination URL (must be HTTPS in production)
    - `events`: List of event types to subscribe to

    **Optional fields:**
    - `secret`: HMAC secret for signature verification (auto-generated if not provided)
    - `headers`: Custom headers to include in requests
    - `max_retries`: Maximum retry attempts (default: 3)
    - `retry_backoff`: Seconds between retries (default: 60)
    - `timeout`: Request timeout in seconds (default: 10)
    - `filters`: Filter events by specific criteria

    **Example:**
    ```json
    {
      "name": "User Events Webhook",
      "url": "https://example.com/webhooks/users",
      "events": ["user.created", "user.updated"],
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
    ```
    """
    try:
        subscription = webhook_service.create_subscription(
            db=db,
            **subscription_data.model_dump()
        )
        return subscription

    except Exception as e:
        logger.error("Failed to create webhook subscription", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions", response_model=List[WebhookSubscriptionResponse])
async def list_webhook_subscriptions(
    active_only: bool = Query(False, description="Only return active subscriptions"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db)
):
    """
    List all webhook subscriptions

    **Query parameters:**
    - `active_only`: If true, only return active subscriptions
    - `event_type`: Filter by specific event type
    """
    subscriptions = webhook_service.list_subscriptions(
        db=db,
        active_only=active_only,
        event_type=event_type
    )
    return subscriptions


@router.get("/subscriptions/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """Get webhook subscription by ID"""
    subscription = webhook_service.get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    return subscription


@router.patch("/subscriptions/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook_subscription(
    subscription_id: int,
    subscription_data: WebhookSubscriptionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update webhook subscription

    Only provided fields will be updated. All fields are optional.
    """
    # Filter out None values
    updates = {k: v for k, v in subscription_data.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    subscription = webhook_service.update_subscription(
        db=db,
        subscription_id=subscription_id,
        **updates
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    return subscription


@router.delete("/subscriptions/{subscription_id}", status_code=204)
async def delete_webhook_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """Delete webhook subscription"""
    success = webhook_service.delete_subscription(db, subscription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")


# Delivery logs

@router.get("/deliveries", response_model=List[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    subscription_id: Optional[int] = Query(None, description="Filter by subscription ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    success_only: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    List webhook delivery logs

    View history of webhook deliveries, including success/failure status,
    response codes, and error messages.

    **Query parameters:**
    - `subscription_id`: Filter by specific subscription
    - `event_type`: Filter by event type
    - `success_only`: If true, only show successful deliveries; if false, only failures
    - `limit`: Maximum number of results (default: 100, max: 1000)
    """
    deliveries = webhook_service.get_deliveries(
        db=db,
        subscription_id=subscription_id,
        event_type=event_type,
        success_only=success_only,
        limit=limit
    )
    return deliveries


@router.get("/subscriptions/{subscription_id}/stats", response_model=WebhookStats)
async def get_webhook_stats(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """
    Get webhook subscription statistics

    Returns delivery stats and recent delivery history.
    """
    subscription = webhook_service.get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    # Get recent deliveries
    recent_deliveries = webhook_service.get_deliveries(
        db=db,
        subscription_id=subscription_id,
        limit=10
    )

    # Calculate success rate
    success_rate = None
    if subscription.total_deliveries > 0:
        success_rate = (subscription.successful_deliveries / subscription.total_deliveries) * 100

    return WebhookStats(
        subscription_id=subscription.id,
        total_deliveries=subscription.total_deliveries,
        successful_deliveries=subscription.successful_deliveries,
        failed_deliveries=subscription.failed_deliveries,
        success_rate=success_rate,
        last_delivery_at=subscription.last_delivery_at,
        last_success_at=subscription.last_success_at,
        last_failure_at=subscription.last_failure_at,
        recent_deliveries=recent_deliveries
    )


# Testing

@router.post("/test", response_model=WebhookTestResult)
async def test_webhook(
    test_data: WebhookTest
):
    """
    Test a webhook URL

    Sends a test payload to the specified URL to verify it's reachable
    and responding correctly.

    **Example payload sent:**
    ```json
    {
      "event_type": "test.ping",
      "event_id": "uuid-here",
      "timestamp": "2025-12-19T...",
      "data": {
        "message": "This is a test webhook",
        "test": true
      }
    }
    ```

    **Recommended response:** Return HTTP 200 with any body
    """
    result = await webhook_service.test_webhook_url(
        url=test_data.url,
        headers=test_data.headers,
        timeout=test_data.timeout
    )

    return WebhookTestResult(**result)


# Event types reference

@router.get("/events")
async def list_event_types():
    """
    List all available webhook event types

    Returns a list of event types you can subscribe to.
    """
    from app.models.webhook import WebhookEventType

    return {
        "events": [
            {
                "type": event.value,
                "category": event.value.split(".")[0],
                "description": _get_event_description(event.value)
            }
            for event in WebhookEventType
        ]
    }


def _get_event_description(event_type: str) -> str:
    """Get human-readable description for event type"""
    descriptions = {
        "user.created": "Triggered when a new user is created",
        "user.updated": "Triggered when a user is updated",
        "user.deleted": "Triggered when a user is deleted",
        "user.login": "Triggered when a user logs in",
        "entity.created": "Triggered when any entity is created",
        "entity.updated": "Triggered when any entity is updated",
        "entity.deleted": "Triggered when any entity is deleted",
        "task.completed": "Triggered when a background task completes successfully",
        "task.failed": "Triggered when a background task fails",
        "task.started": "Triggered when a background task starts",
        "media.processed": "Triggered when media processing completes",
        "media.failed": "Triggered when media processing fails",
        "email.sent": "Triggered when an email is sent successfully",
        "email.failed": "Triggered when an email fails to send",
        "bulk_email.completed": "Triggered when a bulk email operation completes",
        "permissions.updated": "Triggered when permissions are updated",
        "role.created": "Triggered when a new role is created",
        "role.updated": "Triggered when a role is updated",
    }
    return descriptions.get(event_type, "No description available")
