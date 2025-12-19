"""
Webhook service for managing and delivering webhooks

Handles webhook subscriptions, delivery, retries, and HMAC signatures.
"""
import hmac
import hashlib
import secrets
import httpx
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.webhook import WebhookSubscription, WebhookDelivery, WebhookEventType
from app.schemas.webhook import WebhookEventPayload
from app.utils.logger import get_structured_logger, LogContext

logger = get_structured_logger(__name__)


class WebhookService:
    """
    Service for managing webhook subscriptions and deliveries

    Features:
    - HMAC signature generation for security
    - Automatic retry with exponential backoff
    - Delivery logging and statistics
    - Event filtering
    """

    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None

    async def get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return self.http_client

    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    # Subscription management

    def create_subscription(
        self,
        db: Session,
        name: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        **kwargs
    ) -> WebhookSubscription:
        """
        Create a new webhook subscription

        Args:
            db: Database session
            name: Friendly name
            url: Destination URL
            events: List of event types to subscribe to
            secret: HMAC secret (auto-generated if not provided)
            **kwargs: Additional fields (headers, max_retries, etc.)

        Returns:
            Created WebhookSubscription
        """
        # Generate secret if not provided
        if not secret:
            secret = secrets.token_urlsafe(32)

        subscription = WebhookSubscription(
            name=name,
            url=url,
            events=events,
            secret=secret,
            **kwargs
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        logger.info("Webhook subscription created",
                   subscription_id=subscription.id,
                   name=name,
                   url=url,
                   events=events)

        return subscription

    def get_subscription(self, db: Session, subscription_id: int) -> Optional[WebhookSubscription]:
        """Get subscription by ID"""
        return db.query(WebhookSubscription).filter(WebhookSubscription.id == subscription_id).first()

    def list_subscriptions(
        self,
        db: Session,
        active_only: bool = False,
        event_type: Optional[str] = None
    ) -> List[WebhookSubscription]:
        """
        List webhook subscriptions

        Args:
            db: Database session
            active_only: Only return active subscriptions
            event_type: Filter by event type

        Returns:
            List of subscriptions
        """
        query = db.query(WebhookSubscription)

        if active_only:
            query = query.filter(WebhookSubscription.active == True)

        if event_type:
            # Filter subscriptions that listen to this event
            query = query.filter(WebhookSubscription.events.contains([event_type]))

        return query.all()

    def update_subscription(
        self,
        db: Session,
        subscription_id: int,
        **updates
    ) -> Optional[WebhookSubscription]:
        """Update subscription"""
        subscription = self.get_subscription(db, subscription_id)
        if not subscription:
            return None

        for key, value in updates.items():
            if value is not None and hasattr(subscription, key):
                setattr(subscription, key, value)

        db.commit()
        db.refresh(subscription)

        logger.info("Webhook subscription updated",
                   subscription_id=subscription_id,
                   updates=list(updates.keys()))

        return subscription

    def delete_subscription(self, db: Session, subscription_id: int) -> bool:
        """Delete subscription"""
        subscription = self.get_subscription(db, subscription_id)
        if not subscription:
            return False

        db.delete(subscription)
        db.commit()

        logger.info("Webhook subscription deleted", subscription_id=subscription_id)
        return True

    # Event triggering

    async def trigger_event(
        self,
        db: Session,
        event_type: str,
        data: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Trigger a webhook event

        Finds all subscriptions listening to this event and enqueues delivery.

        Args:
            db: Database session
            event_type: Type of event (e.g., "user.created")
            data: Event data payload
            filters: Optional filters to match against subscription filters

        Returns:
            Number of webhooks triggered
        """
        # Find active subscriptions for this event
        subscriptions = db.query(WebhookSubscription).filter(
            and_(
                WebhookSubscription.active == True,
                WebhookSubscription.events.contains([event_type])
            )
        ).all()

        if not subscriptions:
            logger.debug("No webhook subscriptions for event", event_type=event_type)
            return 0

        # Create event payload
        event_id = str(uuid.uuid4())
        payload = WebhookEventPayload(
            event_type=event_type,
            event_id=event_id,
            timestamp=datetime.utcnow(),
            data=data
        )

        triggered = 0
        for subscription in subscriptions:
            # Check if subscription filters match event
            if subscription.filters and not self._matches_filters(data, subscription.filters):
                logger.debug("Event filtered out by subscription filters",
                           subscription_id=subscription.id,
                           event_type=event_type)
                continue

            # Enqueue delivery (will be processed by worker)
            await self._enqueue_delivery(db, subscription, payload)
            triggered += 1

        logger.info("Webhook event triggered",
                   event_type=event_type,
                   event_id=event_id,
                   subscriptions_notified=triggered)

        return triggered

    def _matches_filters(self, data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if event data matches subscription filters"""
        for key, expected_value in filters.items():
            actual_value = data.get(key)
            if actual_value != expected_value:
                return False
        return True

    async def _enqueue_delivery(
        self,
        db: Session,
        subscription: WebhookSubscription,
        payload: WebhookEventPayload
    ):
        """
        Enqueue webhook delivery

        In production, this would use the queue system (ARQ).
        For now, we'll deliver immediately in background.
        """
        # Import here to avoid circular dependency
        from app.services.queue_service import queue_service

        # Enqueue webhook delivery task
        job_id = await queue_service.enqueue_webhook_delivery(
            subscription_id=subscription.id,
            event_type=payload.event_type,
            payload=payload.model_dump()
        )

        logger.debug("Webhook delivery enqueued",
                    subscription_id=subscription.id,
                    event_type=payload.event_type,
                    job_id=job_id)

    # Delivery

    async def deliver_webhook(
        self,
        db: Session,
        subscription_id: int,
        event_type: str,
        payload: Dict[str, Any],
        attempt_number: int = 1
    ) -> WebhookDelivery:
        """
        Deliver webhook to subscription URL

        Args:
            db: Database session
            subscription_id: Subscription ID
            event_type: Event type
            payload: Event payload
            attempt_number: Current attempt number (for retries)

        Returns:
            WebhookDelivery record with delivery result
        """
        subscription = self.get_subscription(db, subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        with LogContext(subscription_id=subscription_id, event_type=event_type, attempt=attempt_number):
            logger.info("Delivering webhook",
                       url=subscription.url,
                       event_type=event_type)

            # Prepare delivery record
            delivery = WebhookDelivery(
                subscription_id=subscription_id,
                event_type=event_type,
                payload=payload,
                url=subscription.url,
                attempt_number=attempt_number
            )

            try:
                # Generate signature
                signature = self._generate_signature(payload, subscription.secret)

                # Prepare headers
                headers = {
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Delivery": str(uuid.uuid4()),
                    "User-Agent": "FastAPI-Webhooks/1.0"
                }

                # Add custom headers
                if subscription.headers:
                    headers.update(subscription.headers)

                delivery.headers = headers

                # Make request
                start_time = datetime.utcnow()
                client = await self.get_http_client()

                response = await client.post(
                    subscription.url,
                    json=payload,
                    headers=headers,
                    timeout=subscription.timeout
                )

                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # Record response
                delivery.status_code = response.status_code
                delivery.response_body = response.text[:10000]  # Limit to 10KB
                delivery.response_headers = dict(response.headers)
                delivery.delivered_at = end_time
                delivery.duration_ms = duration_ms

                # Check if successful (2xx status codes)
                if 200 <= response.status_code < 300:
                    delivery.success = True
                    subscription.successful_deliveries += 1
                    subscription.last_success_at = end_time

                    logger.info("Webhook delivered successfully",
                               status_code=response.status_code,
                               duration_ms=duration_ms)
                else:
                    delivery.success = False
                    delivery.error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                    subscription.failed_deliveries += 1
                    subscription.last_failure_at = end_time

                    # Schedule retry if applicable
                    if attempt_number < subscription.max_retries:
                        delivery.will_retry = True
                        delivery.next_retry_at = self._calculate_next_retry(
                            attempt_number,
                            subscription.retry_backoff
                        )

                    logger.warning("Webhook delivery failed",
                                  status_code=response.status_code,
                                  error=delivery.error_message,
                                  will_retry=delivery.will_retry)

            except httpx.TimeoutException as e:
                delivery.success = False
                delivery.error_message = f"Request timeout after {subscription.timeout}s"
                subscription.failed_deliveries += 1
                subscription.last_failure_at = datetime.utcnow()

                # Schedule retry
                if attempt_number < subscription.max_retries:
                    delivery.will_retry = True
                    delivery.next_retry_at = self._calculate_next_retry(
                        attempt_number,
                        subscription.retry_backoff
                    )

                logger.error("Webhook delivery timeout",
                            error=str(e),
                            will_retry=delivery.will_retry)

            except Exception as e:
                delivery.success = False
                delivery.error_message = str(e)
                subscription.failed_deliveries += 1
                subscription.last_failure_at = datetime.utcnow()

                # Schedule retry
                if attempt_number < subscription.max_retries:
                    delivery.will_retry = True
                    delivery.next_retry_at = self._calculate_next_retry(
                        attempt_number,
                        subscription.retry_backoff
                    )

                logger.error("Webhook delivery error",
                            error=str(e),
                            will_retry=delivery.will_retry)

            # Update subscription stats
            subscription.total_deliveries += 1
            subscription.last_delivery_at = datetime.utcnow()

            # Save delivery and subscription
            db.add(delivery)
            db.commit()
            db.refresh(delivery)

            return delivery

    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """
        Generate HMAC SHA256 signature for payload

        Format: sha256=<hex_digest>
        """
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def verify_signature(self, payload: Dict[str, Any], signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        expected_signature = self._generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)

    def _calculate_next_retry(self, attempt_number: int, retry_backoff: int) -> datetime:
        """Calculate next retry time with exponential backoff"""
        # Exponential backoff: backoff * (2 ^ attempt_number)
        delay_seconds = retry_backoff * (2 ** attempt_number)
        return datetime.utcnow() + timedelta(seconds=delay_seconds)

    # Testing

    async def test_webhook_url(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Test a webhook URL

        Sends a test payload to verify the endpoint is reachable.

        Returns:
            Dict with success status and response details
        """
        test_payload = {
            "event_type": "test.ping",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message": "This is a test webhook from FastAPI Webhooks",
                "test": True
            }
        }

        request_headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": "test.ping",
            "User-Agent": "FastAPI-Webhooks/1.0"
        }

        if headers:
            request_headers.update(headers)

        try:
            start_time = datetime.utcnow()
            client = await self.get_http_client()

            response = await client.post(
                url,
                json=test_payload,
                headers=request_headers,
                timeout=timeout
            )

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "response_body": response.text[:1000],
                "duration_ms": duration_ms,
                "error_message": None if 200 <= response.status_code < 300 else response.text[:500]
            }

        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_body": None,
                "duration_ms": 0,
                "error_message": str(e)
            }

    # Delivery logs

    def get_deliveries(
        self,
        db: Session,
        subscription_id: Optional[int] = None,
        event_type: Optional[str] = None,
        success_only: Optional[bool] = None,
        limit: int = 100
    ) -> List[WebhookDelivery]:
        """Get webhook delivery logs"""
        query = db.query(WebhookDelivery)

        if subscription_id:
            query = query.filter(WebhookDelivery.subscription_id == subscription_id)

        if event_type:
            query = query.filter(WebhookDelivery.event_type == event_type)

        if success_only is not None:
            query = query.filter(WebhookDelivery.success == success_only)

        return query.order_by(WebhookDelivery.created_at.desc()).limit(limit).all()


# Global instance
webhook_service = WebhookService()
