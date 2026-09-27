"""安全中间件：统一响应头，并阻止跨站页面发起写请求。"""
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import CORS_ORIGINS

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有响应补充基础安全响应头。"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
                "object-src 'none'; img-src 'self' data:; "
                "style-src 'self' 'unsafe-inline'; script-src 'self'; "
                "connect-src 'self'",
            )
        return response


class OriginGuardMiddleware(BaseHTTPMiddleware):
    """拒绝来自非白名单来源的 API 写请求，补充 SameSite Cookie 防护。"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method in UNSAFE_METHODS and request.url.path.startswith("/api"):
            fetch_site = request.headers.get("sec-fetch-site", "").lower()
            origin = request.headers.get("origin")
            request_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
            allowed_origins = {*CORS_ORIGINS, request_origin}

            if fetch_site == "cross-site" or (origin and origin not in allowed_origins):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "请求来源不被允许"},
                )

        return await call_next(request)
