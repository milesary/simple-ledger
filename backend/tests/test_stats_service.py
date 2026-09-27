"""统计查询结果与查询次数测试。"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Budget, Category, Transaction, User
from app.services.stats_service import StatsService, month_bounds


@pytest.fixture
def stats_db():
    """构造带跨月流水和历史预算的内存数据库。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = testing_session()

    user = User(email="stats@qq.com", password_hash="unused")
    food = Category(name="餐饮", type="expense")
    salary = Category(name="工资", type="income")
    db.add_all([user, food, salary])
    db.flush()
    db.add_all(
        [
            Transaction(
                user_id=user.id,
                type="expense",
                amount=Decimal("50.00"),
                category_id=food.id,
                occurred_on=date(2026, 9, 1),
            ),
            Transaction(
                user_id=user.id,
                type="expense",
                amount=Decimal("70.00"),
                category_id=food.id,
                occurred_on=date(2026, 9, 15),
            ),
            Transaction(
                user_id=user.id,
                type="income",
                amount=Decimal("500.00"),
                category_id=salary.id,
                occurred_on=date(2026, 9, 10),
            ),
            Transaction(
                user_id=user.id,
                type="expense",
                amount=Decimal("30.00"),
                category_id=food.id,
                occurred_on=date(2026, 10, 1),
            ),
        ]
    )
    db.add_all(
        [
            Budget(user_id=user.id, month="2026-09", amount=Decimal("200.00")),
            Budget(user_id=user.id, month="2026-10", amount=Decimal("100.00")),
        ]
    )
    db.commit()

    try:
        yield db, engine, user.id
    finally:
        db.close()
        engine.dispose()


def test_month_bounds_rejects_invalid_month():
    """非法月份会抛出可转成 400 的 ValueError。"""
    with pytest.raises(ValueError, match="YYYY-MM"):
        month_bounds("2026-13")


def test_stats_results_and_monthly_trend_query_count(stats_db):
    """统计结果正确，年度趋势只执行一次聚合查询。"""
    db, engine, user_id = stats_db
    service = StatsService(db)

    summary = service.get_monthly_summary(user_id, "2026-09")
    assert summary["income"] == Decimal("500.00")
    assert summary["expense"] == Decimal("120.00")
    assert summary["balance"] == Decimal("380.00")
    assert summary["expense_count"] == 2

    category_summary = service.get_category_summary(user_id, "2026-09")
    assert category_summary == [{"name": "餐饮", "amount": 120.0}]

    statements = []

    def record_query(*args):
        statements.append(args[2])

    event.listen(engine, "before_cursor_execute", record_query)
    try:
        trend = service.get_monthly_trend(user_id, 2026)
    finally:
        event.remove(engine, "before_cursor_execute", record_query)

    assert len(statements) == 1
    assert trend[8] == {"month": "09", "income": 500.0, "expense": 120.0}
    assert trend[9] == {"month": "10", "income": 0.0, "expense": 30.0}


def test_budget_history_does_not_query_once_per_month(stats_db):
    """历史预算使用固定查询数，不随预算月份数量线性增长。"""
    db, engine, user_id = stats_db
    statements = []

    def record_query(*args):
        statements.append(args[2])

    event.listen(engine, "before_cursor_execute", record_query)
    try:
        history = StatsService(db).list_budgets(user_id)
    finally:
        event.remove(engine, "before_cursor_execute", record_query)

    assert len(statements) == 2
    assert [item["expense"] for item in history] == [
        Decimal("30.00"),
        Decimal("120.00"),
    ]
