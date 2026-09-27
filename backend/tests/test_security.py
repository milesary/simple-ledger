"""安全配置、响应头与来源校验测试。"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import validate_settings
from app.middleware import OriginGuardMiddleware, SecurityHeadersMiddleware


def test_production_settings_reject_unsafe_defaults():
    """生产环境不能使用开发密钥或开发邮件模式。"""
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_settings("production", "dev-secret-change-in-prod", False)

    with pytest.raises(RuntimeError, match="MAIL_DEV_MODE"):
        validate_settings("production", "x" * 32, True)


def test_security_headers_and_origin_guard():
    """安全头会补到响应上，跨站 API 写请求会在进入路由前被拒绝。"""
    test_app = FastAPI()
    test_app.add_middleware(OriginGuardMiddleware)
    test_app.add_middleware(SecurityHeadersMiddleware)

    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    @test_app.post("/api/example")
    def write_example():
        return {"success": True}

    with TestClient(test_app) as client:
        health_response = client.get("/health")
        assert health_response.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in health_response.headers[
            "content-security-policy"
        ]

        rejected = client.post(
            "/api/example",
            headers={
                "Origin": "https://evil.example",
                "Sec-Fetch-Site": "cross-site",
            },
        )
        assert rejected.status_code == 403
        assert rejected.json()["detail"] == "请求来源不被允许"
