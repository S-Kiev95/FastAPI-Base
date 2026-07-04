"""
Security Headers Middleware
Agrega headers de seguridad HTTP para prevenir vulnerabilidades comunes.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que agrega headers de seguridad estándar.

    Headers incluidos:
    - X-Content-Type-Options: nosniff (previene MIME sniffing)
    - X-Frame-Options: DENY (previene clickjacking)
    - X-XSS-Protection: 1; mode=block (XSS protection legacy)
    - Strict-Transport-Security: HSTS para HTTPS
    - Content-Security-Policy: CSP básico
    - Referrer-Policy: control de referrer
    """

    def __init__(
        self,
        app,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 año
        enable_csp: bool = True,
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.enable_csp = enable_csp

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # X-Content-Type-Options: previene MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: previene clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy, pero no hace daño)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: no enviar referrer a orígenes externos
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (solo si HTTPS está habilitado)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            )

        # Content-Security-Policy básico
        if self.enable_csp:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Permisivo para admin Svelte
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response
