"""
Rate Limiting Middleware

Global rate limiting middleware that applies to all requests
or specific path patterns.
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.rate_limiter import rate_limiter
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware

    Applies rate limits based on:
    - Client IP address
    - Request path patterns
    - Configurable limits per path

    Example:
        app.add_middleware(
            RateLimitMiddleware,
            default_limit=100,
            default_window=60
        )
    """

    def __init__(
        self,
        app,
        default_limit: int = 100,  # 100 requests
        default_window: int = 60,  # per minute
        exclude_paths: list = None  # Paths to exclude from rate limiting
    ):
        """
        Initialize rate limit middleware

        Args:
            app: FastAPI app
            default_limit: Default max requests
            default_window: Default time window in seconds
            exclude_paths: List of paths to exclude (e.g., ["/health", "/metrics"])
        """
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]

        # Path-specific limits (more restrictive for heavy endpoints)
        self.path_limits = {
            "/tasks/": (50, 60),              # 50 requests/minute for task endpoints
            "/tasks/email/bulk": (5, 3600),   # 5 bulk emails/hour
            "/media/upload": (30, 60),        # 30 uploads/minute
        }

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""

        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Skip if Redis is disabled
        if not settings.REDIS_ENABLED:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Determine limit based on path
        limit, window = self._get_limit_for_path(request.url.path)

        # Create rate limit key
        rate_key = f"ip:{client_ip}:{request.url.path}"

        # Check rate limit
        allowed, info = await rate_limiter.check_rate_limit(
            key=rate_key,
            limit=limit,
            window=window
        )

        # Add rate limit headers to response
        async def add_rate_limit_headers(response):
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_at"])
            return response

        if not allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {limit} requests per {window} seconds",
                    "limit": info["limit"],
                    "current_usage": info["current_usage"],
                    "retry_after": info["retry_after"],
                    "reset_at": info["reset_at"]
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset_at"]),
                    "Retry-After": str(info["retry_after"])
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit info headers
        response = await add_rate_limit_headers(response)

        return response

    def _get_limit_for_path(self, path: str) -> tuple:
        """
        Get rate limit for specific path

        Args:
            path: Request path

        Returns:
            Tuple of (limit, window)
        """
        # Check for exact match first
        if path in self.path_limits:
            return self.path_limits[path]

        # Check for prefix match
        for pattern, limits in self.path_limits.items():
            if path.startswith(pattern):
                return limits

        # Return default
        return self.default_limit, self.default_window
