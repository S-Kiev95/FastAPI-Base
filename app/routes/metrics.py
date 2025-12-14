from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database import get_session
from app.models.metric import (
    ApiMetricRead,
    MetricsSummary,
    EndpointStats,
    ErrorStats
)
from app.services.metrics_service import metrics_service

router = APIRouter(prefix="/analytics", tags=["Analytics & Metrics"])


@router.get("/summary", response_model=MetricsSummary)
def get_metrics_summary(
    hours: Optional[int] = Query(24, description="Time window in hours (default: 24h)"),
    session: Session = Depends(get_session)
):
    """
    Get aggregated metrics summary.

    Returns:
    - Total requests
    - Successful vs failed requests
    - Average, min, max duration
    - Duration percentiles (p50, p95, p99)

    Example response:
    ```json
    {
        "total_requests": 1500,
        "successful_requests": 1450,
        "failed_requests": 50,
        "avg_duration_ms": 125.5,
        "min_duration_ms": 5.2,
        "max_duration_ms": 3500.0,
        "p50_duration_ms": 98.5,
        "p95_duration_ms": 450.2,
        "p99_duration_ms": 1200.5
    }
    ```
    """
    return metrics_service.get_summary(session, hours=hours)


@router.get("/endpoints", response_model=List[EndpointStats])
def get_endpoint_stats(
    hours: Optional[int] = Query(24, description="Time window in hours"),
    limit: int = Query(20, description="Max number of endpoints to return"),
    session: Session = Depends(get_session)
):
    """
    Get statistics per endpoint.

    Returns top endpoints by request count with:
    - Total requests
    - Average duration
    - Error rate
    - Success rate

    Example response:
    ```json
    [
        {
            "endpoint": "/users/",
            "method": "GET",
            "total_requests": 500,
            "avg_duration_ms": 45.2,
            "error_rate": 2.5,
            "success_rate": 97.5
        }
    ]
    ```
    """
    return metrics_service.get_endpoint_stats(session, hours=hours, limit=limit)


@router.get("/endpoints/slowest", response_model=List[EndpointStats])
def get_slowest_endpoints(
    hours: Optional[int] = Query(24, description="Time window in hours"),
    limit: int = Query(10, description="Max number of endpoints"),
    session: Session = Depends(get_session)
):
    """
    Get slowest endpoints by average duration.

    Useful for identifying performance bottlenecks.
    Only includes endpoints with at least 10 requests to avoid outliers.

    Example response:
    ```json
    [
        {
            "endpoint": "/users/filter",
            "method": "POST",
            "total_requests": 150,
            "avg_duration_ms": 850.5,
            "error_rate": 0.0,
            "success_rate": 0.0
        }
    ]
    ```
    """
    return metrics_service.get_slowest_endpoints(session, hours=hours, limit=limit)


@router.get("/errors", response_model=List[ErrorStats])
def get_error_stats(
    hours: Optional[int] = Query(24, description="Time window in hours"),
    session: Session = Depends(get_session)
):
    """
    Get error statistics grouped by HTTP status code.

    Returns:
    - Status code
    - Count
    - Percentage of total requests
    - Most common path for this error

    Example response:
    ```json
    [
        {
            "status_code": 404,
            "count": 25,
            "percentage": 1.67,
            "most_common_path": "/users/999"
        },
        {
            "status_code": 500,
            "count": 5,
            "percentage": 0.33,
            "most_common_path": "/users/filter"
        }
    ]
    ```
    """
    return metrics_service.get_error_stats(session, hours=hours)


@router.get("/recent", response_model=List[ApiMetricRead])
def get_recent_metrics(
    limit: int = Query(100, description="Number of recent metrics"),
    hours: Optional[int] = Query(None, description="Filter last N hours (optional)"),
    session: Session = Depends(get_session)
):
    """
    Get recent API metrics (raw data).

    Useful for debugging and detailed analysis.

    Example response:
    ```json
    [
        {
            "id": 1,
            "method": "GET",
            "path": "/users/",
            "status_code": 200,
            "duration_ms": 45.2,
            "client_ip": "127.0.0.1",
            "user_agent": "Mozilla/5.0...",
            "user_id": null,
            "error_type": null,
            "error_message": null,
            "timestamp": "2025-12-09T20:00:00"
        }
    ]
    ```
    """
    return metrics_service.get_recent_metrics(session, limit=limit, hours=hours)


@router.get("/health-check")
def metrics_health_check(session: Session = Depends(get_session)):
    """
    Check if metrics system is working.

    Returns basic stats and system status.
    """
    summary = metrics_service.get_summary(session, hours=1)

    return {
        "status": "healthy",
        "metrics_enabled": True,
        "last_hour_requests": summary.total_requests,
        "database": "connected"
    }
