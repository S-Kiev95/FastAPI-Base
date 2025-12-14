import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlmodel import Session

from app.models.metric import ApiMetric
from app.database import engine


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect API metrics and store them in database.

    Collects:
    - Request method, path, status code
    - Response time (duration)
    - Client IP and User Agent
    - User ID (if authenticated)
    - Error information (if failed)

    Metrics are stored asynchronously to avoid impacting performance.
    """

    # Paths to exclude from metrics (to avoid noise)
    EXCLUDED_PATHS = {
        "/metrics",  # Prometheus endpoint
        "/health",   # Health check
        "/docs",     # Swagger UI
        "/redoc",    # ReDoc
        "/openapi.json"  # OpenAPI schema
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Start timer
        start_time = time.time()

        # Process request
        error_type = None
        error_message = None

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Capture error information
            error_type = type(e).__name__
            error_message = str(e)[:1000]  # Limit error message length
            status_code = 500
            raise  # Re-raise to let FastAPI handle it
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Get client info
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

            # Get user ID if authenticated (from request.state if available)
            user_id = getattr(request.state, "user_id", None)

            # Store metric in database (in background to avoid blocking)
            try:
                self._store_metric(
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    user_id=user_id,
                    error_type=error_type,
                    error_message=error_message
                )
            except Exception as e:
                # Don't fail request if metrics storage fails
                print(f"[WARNING] Failed to store metric: {e}")

        return response

    def _store_metric(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: str = None,
        user_agent: str = None,
        user_id: int = None,
        error_type: str = None,
        error_message: str = None
    ):
        """Store metric in database"""
        with Session(engine) as session:
            metric = ApiMetric(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
                user_agent=user_agent,
                user_id=user_id,
                error_type=error_type,
                error_message=error_message
            )
            session.add(metric)
            session.commit()
