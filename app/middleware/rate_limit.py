"""
Rate Limiting Middleware

Middleware con rate limiting global y **per-tenant** basado en plan.
Si el request incluye Bearer token y se puede resolver la organización,
usa el `api_rate_limit` del plan; si no, usa el límite por IP.
"""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.rate_limiter import rate_limiter
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware con soporte per-tenant.

    Prioridad de límites:
    1. Path-specific limits (ej. /media/upload → 30/min)
    2. Per-tenant limit basado en PLAN_FEATURES.api_rate_limit (req/hora)
    3. Default IP-based limit (100/min)
    """

    def __init__(
        self,
        app,
        default_limit: int = 100,
        default_window: int = 60,
        exclude_paths: list = None,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]

        # Path-specific limits (más restrictivos para endpoints pesados y auth)
        self.path_limits = {
            # Auth endpoints (prevenir brute force)
            "/auth/login": (5, 300),       # 5 intentos cada 5 minutos
            "/auth/register": (3, 3600),   # 3 registros por hora (por IP)
            "/auth/password-reset": (3, 3600),  # 3 resets por hora
            # Task endpoints
            "/tasks/": (50, 60),
            "/tasks/email/bulk": (5, 3600),
            # Media
            "/media/upload": (30, 60),
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _get_client_ip(self, request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        return client_ip

    def _resolve_tenant_limit(self, request: Request):
        """
        Intenta resolver org_id y rate limit del plan desde el Bearer token.
        Retorna (rate_key_suffix, limit, window) o None si no aplica.
        """
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return None

        token = auth_header[7:]
        try:
            from app.core.security import verify_token
            from app.services.user_service import user_service
            from sqlmodel import Session
            from app.database import engine

            # Resolver usuario
            if settings.API_KEYS_ENABLED and token.startswith(settings.API_KEY_PREFIX):
                from app.services.api_key_service import api_key_service
                with Session(engine) as session:
                    api_key = api_key_service.verify_key(session, token)
                    if not api_key:
                        return None
                    user_id = api_key.user_id
                    org_id = api_key.organization_id
            else:
                email = verify_token(token)
                if not email:
                    return None
                with Session(engine) as session:
                    user = user_service.get_user_by_email(session, email)
                    if not user:
                        return None
                    user_id = user.id
                    org_id = None

            # Resolver organización (primera membership activa)
            if not org_id:
                from app.models.organization import Membership
                from sqlmodel import select
                with Session(engine) as session:
                    membership = session.exec(
                        select(Membership).where(
                            Membership.user_id == user_id,
                            Membership.is_active == True,
                        ).limit(1)
                    ).first()
                    org_id = membership.organization_id if membership else None

            if not org_id:
                return None

            # Obtener rate limit del plan
            from app.core.plan_guards import get_plan_rate_limit
            with Session(engine) as session:
                plan_limit = get_plan_rate_limit(session, org_id)

            if plan_limit is None:
                return None  # Enterprise = sin límite

            # Rate limit del plan es por hora
            return f"org:{org_id}", plan_limit, 3600

        except Exception as e:
            logger.debug(f"No se pudo resolver tenant rate limit: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #

    async def dispatch(self, request: Request, call_next):
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        if not settings.REDIS_ENABLED:
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # 1. Path-specific limit
        path_limit = self._get_limit_for_path(request.url.path)
        if path_limit:
            limit, window = path_limit
            rate_key = f"ip:{client_ip}:{request.url.path}"
        else:
            # 2. Per-tenant limit
            tenant_info = self._resolve_tenant_limit(request)
            if tenant_info:
                key_suffix, limit, window = tenant_info
                rate_key = f"tenant:{key_suffix}"
            else:
                # 3. Default IP limit
                limit, window = self.default_limit, self.default_window
                rate_key = f"ip:{client_ip}"

        # Check rate limit
        allowed, info = await rate_limiter.check_rate_limit(
            key=rate_key, limit=limit, window=window
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {limit} requests per {window} seconds",
                    "limit": info["limit"],
                    "current_usage": info["current_usage"],
                    "retry_after": info["retry_after"],
                    "reset_at": info["reset_at"],
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset_at"]),
                    "Retry-After": str(info["retry_after"]),
                },
            )

        response = await call_next(request)

        # Rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset_at"])

        return response

    def _get_limit_for_path(self, path: str):
        """Retorna (limit, window) si hay un path-specific limit, None si no."""
        if path in self.path_limits:
            return self.path_limits[path]
        for pattern, limits in self.path_limits.items():
            if path.startswith(pattern):
                return limits
        return None
