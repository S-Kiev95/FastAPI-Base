"""
Rate Limit Decorator for FastAPI Endpoints

Provides fine-grained rate limiting for specific endpoints
with customizable limits per endpoint.
"""
from functools import wraps
from typing import Callable, Optional
from fastapi import Request, HTTPException

from app.services.rate_limiter import rate_limiter


def rate_limit(
    limit: int = 100,
    window: int = 60,
    key_func: Optional[Callable] = None
):
    """
    Rate limit decorator for FastAPI endpoints

    Args:
        limit: Maximum number of requests
        window: Time window in seconds
        key_func: Function to generate rate limit key (default: by IP)

    Example:
        @app.post("/media/upload")
        @rate_limit(limit=50, window=60)  # 50 uploads per minute
        async def upload_media(request: Request):
            ...

        # Custom key function (rate limit by user ID)
        @app.post("/api/action")
        @rate_limit(
            limit=10,
            window=60,
            key_func=lambda req, user: f"user:{user.id}"
        )
        async def action(request: Request, current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request and "request" in kwargs:
                request = kwargs["request"]

            if not request:
                raise ValueError("rate_limit decorator requires Request parameter")

            # Generate rate limit key
            if key_func:
                # Custom key function
                rate_key = key_func(request, *args, **kwargs)
            else:
                # Default: rate limit by IP
                client_ip = request.client.host
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    client_ip = forwarded_for.split(",")[0].strip()

                rate_key = f"ip:{client_ip}:{request.url.path}"

            # Check rate limit
            allowed, info = await rate_limiter.check_rate_limit(
                key=rate_key,
                limit=limit,
                window=window
            )

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
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

            # Execute endpoint
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def rate_limit_by_user(limit: int = 100, window: int = 60):
    """
    Rate limit by authenticated user ID

    Example:
        @app.post("/api/action")
        @rate_limit_by_user(limit=10, window=60)
        async def action(
            request: Request,
            current_user: User = Depends(get_current_user)
        ):
            ...
    """
    def key_func(request: Request, *args, **kwargs):
        # Extract user from kwargs
        current_user = kwargs.get("current_user")
        if not current_user:
            # Fallback to IP if no user
            return f"ip:{request.client.host}:{request.url.path}"

        return f"user:{current_user.id}:{request.url.path}"

    return rate_limit(limit=limit, window=window, key_func=key_func)


def rate_limit_by_api_key(limit: int = 1000, window: int = 60):
    """
    Rate limit by API key (for programmatic access)

    Example:
        @app.post("/api/bulk-operation")
        @rate_limit_by_api_key(limit=1000, window=60)
        async def bulk_operation(
            request: Request,
            api_key: str = Header(...)
        ):
            ...
    """
    def key_func(request: Request, *args, **kwargs):
        api_key = kwargs.get("api_key") or request.headers.get("X-API-Key")
        if not api_key:
            return f"ip:{request.client.host}:{request.url.path}"

        return f"api_key:{api_key}:{request.url.path}"

    return rate_limit(limit=limit, window=window, key_func=key_func)
