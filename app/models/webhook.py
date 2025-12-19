"""
Webhook models for external integrations

Allows external systems to subscribe to events in the application.
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.database import Base


class WebhookEventType(str, enum.Enum):
    """Available webhook event types"""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"

    # Entity events (dynamic)
    ENTITY_CREATED = "entity.created"
    ENTITY_UPDATED = "entity.updated"
    ENTITY_DELETED = "entity.deleted"

    # Task events
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_STARTED = "task.started"

    # Media events
    MEDIA_PROCESSED = "media.processed"
    MEDIA_FAILED = "media.failed"

    # Email events
    EMAIL_SENT = "email.sent"
    EMAIL_FAILED = "email.failed"
    BULK_EMAIL_COMPLETED = "bulk_email.completed"

    # Permission events
    PERMISSIONS_UPDATED = "permissions.updated"
    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"


class WebhookSubscription(Base):
    """
    Webhook subscription configuration

    Stores webhook endpoints that should be called when specific events occur.
    """
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(255), nullable=False)  # Friendly name
    description = Column(Text, nullable=True)
    url = Column(String(2048), nullable=False)  # Destination URL

    # Events to listen to
    events = Column(JSON, nullable=False)  # List of event types: ["user.created", "task.completed"]

    # Security
    secret = Column(String(255), nullable=False)  # HMAC secret for signature

    # Configuration
    active = Column(Boolean, default=True, nullable=False)
    headers = Column(JSON, nullable=True)  # Custom headers: {"Authorization": "Bearer xxx"}

    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_backoff = Column(Integer, default=60, nullable=False)  # Seconds between retries
    timeout = Column(Integer, default=10, nullable=False)  # Request timeout in seconds

    # Filters (optional)
    filters = Column(JSON, nullable=True)  # Filter events: {"user_id": 123}

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=True)  # User ID who created this

    # Statistics
    total_deliveries = Column(Integer, default=0, nullable=False)
    successful_deliveries = Column(Integer, default=0, nullable=False)
    failed_deliveries = Column(Integer, default=0, nullable=False)
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<WebhookSubscription(id={self.id}, name='{self.name}', url='{self.url}', active={self.active})>"


class WebhookDelivery(Base):
    """
    Log of webhook delivery attempts

    Stores history of each webhook call for debugging and monitoring.
    """
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    subscription_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)

    # Payload
    payload = Column(JSON, nullable=False)  # The data sent

    # Request details
    url = Column(String(2048), nullable=False)
    headers = Column(JSON, nullable=True)

    # Response details
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSON, nullable=True)

    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Request duration in milliseconds

    # Status
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)

    # Retry tracking
    attempt_number = Column(Integer, default=1, nullable=False)
    will_retry = Column(Boolean, default=False, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f"<WebhookDelivery(id={self.id}, subscription_id={self.subscription_id}, event='{self.event_type}', status={status})>"
