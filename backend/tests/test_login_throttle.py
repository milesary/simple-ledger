"""密码登录限流测试：失败计数、锁定、重置与解除。"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import LOGIN_LOCKOUT_MINUTES, LOGIN_MAX_ATTEMPTS
from app.database import Base, get_db
from app.main import app
from app.models import LoginAttempt, User
from app.security import hash_password
from app.utils import utc_now


@pytest.fixture
def login_env():
    """构造内存数据库、两个账号与共享的会话工厂。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = session_factory()
    db.add(
        User(
            email="admin@qq.com",
            password_hash=hash_password("Admin12345"),
            is_admin=True,
            is_active=True,
        )
    )
    db.add(
        User(
            email="target@qq.com",
            password_hash=hash_password("Correct12345"),
            is_admin=False,
            is_active=True,
        )
    )
    db.commit()
    db.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session_factory
    finally:
        app.dependency_overrides.clear()


def _login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _attempt_row(session_factory, email):
    db = session_factory()
    try:
        return db.query(LoginAttempt).filter(LoginAttempt.email == email).one_or_none()
    finally:
        db.close()


def test_wrong_password_reports_remaining_attempts(login_env):
    """未达上限时保持原有提示，不泄露锁定状态。"""
    with TestClient(app) as client:
        response = _login(client, "target@qq.com", "Wrong12345")
        assert response.status_code == 200
        assert response.json()["success"] is False
        assert response.json()["message"] == "密码错误"

    attempt = _attempt_row(login_env, "target@qq.com")
    assert attempt is not None
    assert attempt.failed_count == 1
    assert attempt.locked_until is None


def test_lockout_after_max_attempts_blocks_even_correct_password(login_env):
    """连续失败达到上限后锁定，正确密码同样被拒绝。"""
    with TestClient(app) as client:
        for index in range(LOGIN_MAX_ATTEMPTS):
            response = _login(client, "target@qq.com", "Wrong12345")
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is False
            if index < LOGIN_MAX_ATTEMPTS - 1:
                assert body["message"] == "密码错误"
            else:
                assert "账号已锁定" in body["message"]

        # 锁定期间即使密码正确也不能登录。
        blocked = _login(client, "target@qq.com", "Correct12345")
        assert blocked.status_code == 200
        assert blocked.json()["success"] is False
        assert "账号已锁定" in blocked.json()["message"]

        # 未登录状态，Session 不应被写入。
        assert client.get("/api/auth/me").status_code == 401

    attempt = _attempt_row(login_env, "target@qq.com")
    assert attempt is not None
    assert attempt.failed_count == LOGIN_MAX_ATTEMPTS
    assert attempt.locked_until is not None
    # 锁定到期时间应落在配置的锁定时长窗口内。
    assert attempt.locked_until > utc_now()
    assert attempt.locked_until <= utc_now() + timedelta(
        minutes=LOGIN_LOCKOUT_MINUTES, seconds=5
    )


def test_lock_expires_and_allows_login_again(login_env):
    """锁定到期后自动解除，计数清零。"""
    with TestClient(app) as client:
        for _ in range(LOGIN_MAX_ATTEMPTS):
            _login(client, "target@qq.com", "Wrong12345")
        assert _login(client, "target@qq.com", "Correct12345").json()["success"] is False

    # 把锁定时间拨到过去，模拟等待期满。
    db = login_env()
    try:
        attempt = (
            db.query(LoginAttempt).filter(LoginAttempt.email == "target@qq.com").one()
        )
        attempt.locked_until = utc_now() - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        recovered = _login(client, "target@qq.com", "Correct12345")
        assert recovered.status_code == 200
        assert recovered.json()["success"] is True

    assert _attempt_row(login_env, "target@qq.com") is None


def test_successful_login_clears_failure_counter(login_env):
    """登录成功后失败计数被清除。"""
    with TestClient(app) as client:
        _login(client, "target@qq.com", "Wrong12345")
        _login(client, "target@qq.com", "Wrong12345")
        assert _attempt_row(login_env, "target@qq.com").failed_count == 2

        ok = _login(client, "target@qq.com", "Correct12345")
        assert ok.json()["success"] is True

    assert _attempt_row(login_env, "target@qq.com") is None


def test_admin_password_reset_unlocks_account(login_env):
    """管理员重置密码后锁定被解除，新密码可以立即登录。"""
    with TestClient(app) as client:
        for _ in range(LOGIN_MAX_ATTEMPTS):
            _login(client, "target@qq.com", "Wrong12345")
        assert "账号已锁定" in _login(client, "target@qq.com", "Correct12345").json()[
            "message"
        ]

        admin_login = _login(client, "admin@qq.com", "Admin12345")
        assert admin_login.json()["success"] is True

        db = login_env()
        try:
            target_id = (
                db.query(User).filter(User.email == "target@qq.com").one().id
            )
        finally:
            db.close()

        reset = client.post(
            f"/api/admin/users/{target_id}/reset-password",
            json={"new_password": "Reset12345"},
        )
        assert reset.status_code == 200
        assert reset.json()["success"] is True

    # 锁定记录已清除。
    assert _attempt_row(login_env, "target@qq.com") is None

    with TestClient(app) as client:
        fresh = _login(client, "target@qq.com", "Reset12345")
        assert fresh.status_code == 200
        assert fresh.json()["success"] is True


def test_lock_message_reports_configured_minutes(login_env):
    """刚锁定时提示的剩余分钟数应与配置一致，不能多算一分钟。"""
    with TestClient(app) as client:
        for _ in range(LOGIN_MAX_ATTEMPTS):
            _login(client, "target@qq.com", "Wrong12345")

        # 首次锁定后的拒绝提示应恰好等于配置的锁定时长。
        blocked = _login(client, "target@qq.com", "Correct12345")
        assert (
            blocked.json()["message"]
            == f"密码错误次数过多，账号已锁定，请在 {LOGIN_LOCKOUT_MINUTES} 分钟后重试"
        )


def test_locked_until_is_stored_at_whole_second_precision(login_env):
    """锁定时长必须归整到整秒，否则 MySQL 丢弃微秒后会多报一分钟。

    MySQL 的 DATETIME 不保存微秒，因此写入带微秒的 locked_until 再读回时，
    剩余时长会比配置值略大，向上取整就会从 15 变成 16。
    """
    before = utc_now()
    with TestClient(app) as client:
        for _ in range(LOGIN_MAX_ATTEMPTS):
            _login(client, "target@qq.com", "Wrong12345")
    after = utc_now()

    attempt = _attempt_row(login_env, "target@qq.com")
    assert attempt is not None
    assert attempt.locked_until is not None
    # 微秒必须为 0，否则 MySQL 截断后会多报一分钟。
    assert attempt.locked_until.microsecond == 0

    expected = {
        (before + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).replace(microsecond=0),
        (after + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).replace(microsecond=0),
    }
    assert attempt.locked_until in expected


def test_unknown_email_is_throttled_without_changing_message(login_env):
    """不存在的账号同样计入限流，但提示文案保持不变。"""
    with TestClient(app) as client:
        response = _login(client, "nobody@qq.com", "Any12345")
        assert response.status_code == 200
        assert response.json()["success"] is False
        assert response.json()["message"] == "该账号不存在，请先注册"

    attempt = _attempt_row(login_env, "nobody@qq.com")
    assert attempt is not None
    assert attempt.failed_count == 1
