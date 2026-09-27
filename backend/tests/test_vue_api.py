"""Vue SPA 回退、JSON API 与管理员接口集成测试。"""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    Account,
    Budget,
    Category,
    LoginCode,
    RecurringTransaction,
    Transaction,
    Transfer,
    User,
)
from app.security import hash_password
from app.services import auth_service, mail_service


def test_vue_spa_and_api_flow(monkeypatch):
    """Vue 路由由 SPA 接管，业务操作全部通过 JSON API 完成。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    db.add(Category(name="餐饮", type="expense"))
    db.add(Category(name="工资", type="income"))
    db.add(
        User(
            email="admin@qq.com",
            password_hash=hash_password("Admin12345"),
            is_admin=True,
            is_active=True,
        )
    )
    db.commit()
    category = db.query(Category).filter_by(name="餐饮").one()
    db.close()

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    async def fake_send_login_code(email: str, code: str) -> None:
        return None

    monkeypatch.setattr(auth_service, "generate_login_code", lambda: "123456")
    monkeypatch.setattr(mail_service.mail_service, "send_login_code", fake_send_login_code)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            root = client.get("/")
            assert root.status_code == 200
            assert '<div id="app"></div>' in root.text

            nested_page = client.get("/transactions/42/edit")
            assert nested_page.status_code == 200
            assert '<div id="app"></div>' in nested_page.text

            protected = client.get("/api/auth/me")
            assert protected.status_code == 401
            assert protected.json()["detail"] == "未登录或登录已过期"

            rejected = client.post(
                "/api/auth/register",
                json={"email": "123456@vip.qq.com", "password": "Pass12345"},
            )
            assert rejected.status_code == 200
            assert rejected.json() == {
                "success": False,
                "message": "仅支持 QQ 邮箱（QQ号@qq.com）",
            }

            register = client.post(
                "/api/auth/register",
                json={"email": "123456@qq.com", "password": "Pass12345"},
            )
            assert register.status_code == 200
            assert register.json()["success"] is True

            duplicate = client.post(
                "/api/auth/register",
                json={"email": "123456@qq.com", "password": "Pass12345"},
            )
            assert duplicate.status_code == 200
            assert duplicate.json()["success"] is False
            assert "已注册" in duplicate.json()["message"]

            wrong_password = client.post(
                "/api/auth/login",
                json={"email": "123456@qq.com", "password": "Wrong12345"},
            )
            assert wrong_password.status_code == 200
            assert wrong_password.json()["success"] is False
            assert wrong_password.json()["message"] == "密码错误"

            password_login = client.post(
                "/api/auth/login",
                json={"email": "123456@qq.com", "password": "Pass12345"},
            )
            assert password_login.status_code == 200
            assert password_login.json()["success"] is True

            current_user = client.get("/api/auth/me")
            assert current_user.status_code == 200
            assert current_user.json()["email"] == "123456@qq.com"
            assert current_user.json()["is_admin"] is False

            categories = client.get("/api/categories")
            assert categories.status_code == 200
            assert len(categories.json()["categories"]) == 2

            create = client.post(
                "/api/transactions",
                json={
                    "type": "expense",
                    "amount": "38.50",
                    "category_id": category.id,
                    "occurred_on": "2026-09-26",
                    "payment_method": "微信",
                    "note": "测试午餐",
                },
            )
            assert create.status_code == 200
            assert create.json()["success"] is True

            transactions = client.get("/api/transactions?page=1")
            assert transactions.status_code == 200
            assert transactions.json()["total"] == 1
            assert transactions.json()["transactions"][0]["note"] == "测试午餐"

            budget = client.post(
                "/api/budgets",
                json={"month": "2026-09", "amount": "1200"},
            )
            assert budget.status_code == 200
            assert budget.json()["success"] is True

            logout = client.post("/api/auth/logout")
            assert logout.status_code == 200
            assert logout.json()["success"] is True

            send_code = client.post(
                "/api/auth/code",
                json={"email": "123456@qq.com"},
            )
            assert send_code.status_code == 200
            assert send_code.json()["success"] is True

            verify = client.post(
                "/api/auth/verify",
                json={"email": "123456@qq.com", "code": "123456"},
            )
            assert verify.status_code == 200
            assert verify.json()["success"] is True

            client.post("/api/auth/logout")
            admin_login = client.post(
                "/api/auth/login",
                json={"email": "admin@qq.com", "password": "Admin12345"},
            )
            assert admin_login.status_code == 200
            assert admin_login.json()["user"]["is_admin"] is True

            admin_users = client.get("/api/admin/users")
            assert admin_users.status_code == 200
            assert admin_users.json()["total_count"] == 2
            target = next(
                user
                for user in admin_users.json()["users"]
                if user["email"] == "123456@qq.com"
            )

            role = client.post(f"/api/admin/users/{target['id']}/role")
            assert role.status_code == 200
            assert role.json()["user"]["is_admin"] is True

            reset_password = client.post(
                f"/api/admin/users/{target['id']}/reset-password",
                json={"new_password": "NewPass12345"},
            )
            assert reset_password.status_code == 200
            assert reset_password.json()["success"] is True

            remove_role = client.post(f"/api/admin/users/{target['id']}/role")
            assert remove_role.status_code == 200
            assert remove_role.json()["user"]["is_admin"] is False

            toggle = client.post(f"/api/admin/users/{target['id']}/toggle")
            assert toggle.status_code == 200
            assert toggle.json()["user"]["is_active"] is False

            db = testing_session()
            try:
                source_account = Account(
                    user_id=target["id"],
                    name="待删除账户 A",
                    type="bank",
                )
                target_account = Account(
                    user_id=target["id"],
                    name="待删除账户 B",
                    type="cash",
                )
                db.add_all([source_account, target_account])
                db.flush()
                db.add(
                    Transfer(
                        user_id=target["id"],
                        from_account_id=source_account.id,
                        to_account_id=target_account.id,
                        amount="10.00",
                        occurred_on=date(2026, 9, 26),
                    )
                )
                db.add(
                    RecurringTransaction(
                        user_id=target["id"],
                        type="expense",
                        amount="20.00",
                        category_id=category.id,
                        account_id=source_account.id,
                        frequency="monthly",
                        interval=1,
                        start_date=date(2026, 9, 26),
                        next_run_date=date(2026, 10, 26),
                    )
                )
                db.commit()
            finally:
                db.close()

            delete_user = client.delete(f"/api/admin/users/{target['id']}")
            assert delete_user.status_code == 200
            assert delete_user.json()["success"] is True

            remaining_users = client.get("/api/admin/users").json()
            assert remaining_users["total_count"] == 1
            assert all(user["id"] != target["id"] for user in remaining_users["users"])

            db = testing_session()
            try:
                assert (
                    db.query(Transaction).filter(Transaction.user_id == target["id"]).count()
                    == 0
                )
                assert db.query(Budget).filter(Budget.user_id == target["id"]).count() == 0
                assert db.query(Account).filter(Account.user_id == target["id"]).count() == 0
                assert db.query(Transfer).filter(Transfer.user_id == target["id"]).count() == 0
                assert (
                    db.query(RecurringTransaction)
                    .filter(RecurringTransaction.user_id == target["id"])
                    .count()
                    == 0
                )
                assert (
                    db.query(LoginCode)
                    .filter(LoginCode.email == "123456@qq.com")
                    .count()
                    == 0
                )
            finally:
                db.close()
    finally:
        app.dependency_overrides.clear()
