"""账户、转账、周期流水和分类预算集成测试。"""
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Category


def test_account_transfer_recurring_and_category_budget_flow():
    """核心扩展功能可以通过 API 形成完整闭环。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    db.add_all(
        [
            Category(name="餐饮", type="expense"),
            Category(name="工资", type="income"),
        ]
    )
    db.commit()
    expense_category = db.query(Category).filter_by(name="餐饮").one()
    income_category = db.query(Category).filter_by(name="工资").one()
    expense_category_id = expense_category.id
    income_category_id = income_category.id
    db.close()

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            register = client.post(
                "/api/auth/register",
                json={"email": "features@qq.com", "password": "Pass12345"},
            )
            assert register.json()["success"] is True
            login = client.post(
                "/api/auth/login",
                json={"email": "features@qq.com", "password": "Pass12345"},
            )
            assert login.json()["success"] is True

            account_a = client.post(
                "/api/accounts",
                json={
                    "name": "工资卡",
                    "type": "bank",
                    "initial_balance": "1000.00",
                },
            ).json()["account"]
            account_b = client.post(
                "/api/accounts",
                json={
                    "name": "零钱",
                    "type": "cash",
                    "initial_balance": "100.00",
                },
            ).json()["account"]

            expense = client.post(
                "/api/transactions",
                json={
                    "type": "expense",
                    "amount": "200.00",
                    "category_id": expense_category_id,
                    "account_id": account_a["id"],
                    "occurred_on": "2026-09-20",
                    "note": "聚餐",
                },
            )
            assert expense.status_code == 200

            income = client.post(
                "/api/transactions",
                json={
                    "type": "income",
                    "amount": "500.00",
                    "category_id": income_category_id,
                    "account_id": account_b["id"],
                    "occurred_on": "2026-09-21",
                    "note": "兼职",
                },
            )
            assert income.status_code == 200

            transfer = client.post(
                "/api/transfers",
                json={
                    "from_account_id": account_a["id"],
                    "to_account_id": account_b["id"],
                    "amount": "300.00",
                    "occurred_on": "2026-09-22",
                    "note": "补充零钱",
                },
            )
            assert transfer.status_code == 200

            accounts = client.get("/api/accounts").json()
            balances = {
                item["name"]: item["balance"] for item in accounts["accounts"]
            }
            assert balances == {"工资卡": 500.0, "零钱": 900.0}
            assert accounts["total_balance"] == 1400.0

            category_budget = client.post(
                "/api/budgets/categories",
                json={
                    "month": "2026-09",
                    "category_id": expense_category_id,
                    "amount": "300.00",
                },
            )
            assert category_budget.status_code == 200
            budget_data = client.get("/api/budgets").json()
            food_budget = next(
                item
                for item in budget_data["category_budgets"]
                if item["category_id"] == expense_category_id
            )
            assert food_budget["expense"] == 200.0
            assert food_budget["remaining"] == 100.0
            assert round(food_budget["usage_percent"], 1) == 66.7

            start_date = date.today() - timedelta(days=1)
            recurring = client.post(
                "/api/recurring",
                json={
                    "type": "expense",
                    "amount": "80.00",
                    "category_id": expense_category_id,
                    "account_id": account_a["id"],
                    "frequency": "monthly",
                    "interval": 1,
                    "start_date": start_date.isoformat(),
                    "note": "周期房租",
                },
            )
            assert recurring.status_code == 200

            recurring_list = client.get("/api/recurring").json()
            assert recurring_list["generated_count"] == 1
            assert recurring_list["recurring"][0]["next_run_date"] > start_date.isoformat()

            generated = client.get("/api/transactions?q=周期房租").json()
            assert generated["total"] == 1

            transactions = client.get(
                f"/api/transactions?account={account_a['id']}"
            ).json()
            assert transactions["total"] == 2
    finally:
        app.dependency_overrides.clear()
