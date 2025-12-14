from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class ApiMetric(SQLModel, table=True):
    """
    API metrics stored in database for historical analysis.
    Complementary to Prometheus for long-term analytics.
    """
    __tablename__ = "api_metrics"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Request information
    method: str = Field(index=True, description="HTTP method (GET, POST, etc.)")
    path: str = Field(index=True, description="Request path/endpoint")
    status_code: int = Field(index=True, description="HTTP status code")

    # Performance metrics
    duration_ms: float = Field(description="Request duration in milliseconds")

    # Client information
    client_ip: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, max_length=500, description="User agent string")

    # User context (if authenticated)
    user_id: Optional[int] = Field(default=None, index=True, description="User ID if authenticated")

    # Error tracking
    error_type: Optional[str] = Field(default=None, description="Exception type if error occurred")
    error_message: Optional[str] = Field(default=None, max_length=1000, description="Error message if failed")

    # Timestamp
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="When the request occurred"
    )


# Pydantic schemas for API
class ApiMetricRead(SQLModel):
    """Schema for reading metric data"""
    id: int
    method: str
    path: str
    status_code: int
    duration_ms: float
    client_ip: Optional[str]
    user_agent: Optional[str]
    user_id: Optional[int]
    error_type: Optional[str]
    error_message: Optional[str]
    timestamp: datetime


class MetricsSummary(SQLModel):
    """Aggregated metrics summary"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p50_duration_ms: Optional[float] = None
    p95_duration_ms: Optional[float] = None
    p99_duration_ms: Optional[float] = None


class EndpointStats(SQLModel):
    """Statistics per endpoint"""
    endpoint: str
    method: str
    total_requests: int
    avg_duration_ms: float
    error_rate: float
    success_rate: float


class ErrorStats(SQLModel):
    """Error statistics"""
    status_code: int
    count: int
    percentage: float
    most_common_path: Optional[str] = None
