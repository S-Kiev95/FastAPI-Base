"""
Webhook schemas for API validation
"""
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.webhook import WebhookEventType


# Request schemas

class WebhookSubscriptionCreate(BaseModel):
    """Create a new webhook subscription"""
    name: str = Field(..., min_length=1, max_length=255, description="Friendly name for the webhook")
    description: Optional[str] = Field(None, description="Optional description")
    url: str = Field(..., description="Destination URL for webhook calls")
    events: List[WebhookEventType] = Field(..., min_length=1, description="List of events to subscribe to")
    secret: Optional[str] = Field(None, min_length=16, max_length=255, description="HMAC secret (auto-generated if not provided)")
    active: bool = Field(True, description="Whether webhook is active")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers to include in requests")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum number of retry attempts")
    retry_backoff: int = Field(60, ge=10, le=3600, description="Seconds between retries")
    timeout: int = Field(10, ge=1, le=60, description="Request timeout in seconds")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters for events")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @field_validator('headers')
    @classmethod
    def validate_headers(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Ensure header keys and values are strings"""
        if v is None:
            return v
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError('Headers must be string key-value pairs')
        return v


class WebhookSubscriptionUpdate(BaseModel):
    """Update an existing webhook subscription"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[WebhookEventType]] = Field(None, min_length=1)
    secret: Optional[str] = Field(None, min_length=16, max_length=255)
    active: Optional[bool] = None
    headers: Optional[Dict[str, str]] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_backoff: Optional[int] = Field(None, ge=10, le=3600)
    timeout: Optional[int] = Field(None, ge=1, le=60)
    filters: Optional[Dict[str, Any]] = None

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class WebhookTest(BaseModel):
    """Test a webhook endpoint"""
    url: str = Field(..., description="URL to test")
    headers: Optional[Dict[str, str]] = Field(None, description="Headers to send")
    timeout: int = Field(10, ge=1, le=60, description="Request timeout")


# Response schemas

class WebhookSubscriptionResponse(BaseModel):
    """Webhook subscription response"""
    id: int
    name: str
    description: Optional[str]
    url: str
    events: List[str]
    active: bool
    headers: Optional[Dict[str, str]]
    max_retries: int
    retry_backoff: int
    timeout: int
    filters: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[int]

    # Statistics
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_delivery_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]

    # Computed fields
    @property
    def success_rate(self) -> Optional[float]:
        """Calculate success rate percentage"""
        if self.total_deliveries == 0:
            return None
        return (self.successful_deliveries / self.total_deliveries) * 100

    model_config = {"from_attributes": True}


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery log response"""
    id: int
    subscription_id: int
    event_type: str
    payload: Dict[str, Any]
    url: str
    status_code: Optional[int]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    delivered_at: Optional[datetime]
    duration_ms: Optional[int]
    attempt_number: int
    will_retry: bool
    next_retry_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WebhookTestResult(BaseModel):
    """Result of webhook test"""
    success: bool
    status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    duration_ms: int


class WebhookStats(BaseModel):
    """Webhook subscription statistics"""
    subscription_id: int
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: Optional[float]
    last_delivery_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    recent_deliveries: List[WebhookDeliveryResponse]


# Event payload schema (what gets sent to webhook URLs)

class WebhookEventPayload(BaseModel):
    """Standard webhook event payload format"""
    event_type: str = Field(..., description="Type of event (e.g., 'user.created')")
    event_id: str = Field(..., description="Unique event ID")
    timestamp: datetime = Field(..., description="When the event occurred")
    data: Dict[str, Any] = Field(..., description="Event-specific data")

    # Optional metadata
    source: str = Field("fastapi_base", description="Application that generated the event")
    version: str = Field("1.0", description="Event schema version")

    model_config = {"from_attributes": True}
