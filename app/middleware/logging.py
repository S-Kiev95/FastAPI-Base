"""
Logging Middleware

Automatically logs all HTTP requests with:
- Unique request ID (for tracing)
- Request details (method, path, client IP)
- Response details (status code, duration)
- Context propagation (request_id available in all logs)
"""
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_structured_logger, LogContext


logger = get_structured_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests and responses

    Features:
    - Generates unique request_id for each request
    - Logs request start and completion
    - Propagates request_id to all logs via LogContext
    - Captures response time
    - Logs errors with full context
    """

    # Paths to exclude from logging (too noisy)
    EXCLUDED_PATHS = {
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json"
    }

    async def dispatch(self, request: Request, call_next):
        """Process request with logging"""

        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Store request_id in request state (accessible in endpoints)
        request.state.request_id = request_id

        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Get user info (if authenticated)
        user_id = getattr(request.state, "user_id", None)

        # Start timer
        start_time = time.time()

        # Create log context for this request
        # All logs within this context will include these fields
        with LogContext(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            user_id=user_id
        ):
            # Log request start
            logger.info(
                "Request started",
                user_agent=request.headers.get("user-agent", "unknown")[:100]
            )

            # Process request
            try:
                response = await call_next(request)
                status_code = response.status_code

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log successful request
                logger.info(
                    "Request completed",
                    status_code=status_code,
                    duration_ms=round(duration_ms, 2)
                )

                # Add request_id to response headers
                response.headers["X-Request-ID"] = request_id

                return response

            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log error with full context
                logger.error(
                    "Request failed",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    duration_ms=round(duration_ms, 2),
                    exc_info=True
                )

                # Re-raise to let FastAPI handle it
                raise
