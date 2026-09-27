"""统计服务：月度汇总、趋势图、分类占比与预算管理。"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.models import Budget, Category, Transaction


def month_bounds(month: str) -> tuple[date, date]:
    """将 YYYY-MM 转换为左闭右开的日期范围。"""
    try:
        start = datetime.strptime(month, "%Y-%m").date().replace(day=1)
    except (TypeError, ValueError) as exc:
        raise ValueError("month 必须是有效的 YYYY-MM 格式") from exc

    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return start, end


class StatsService:
    """统计与预算服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_monthly_summary(self, user_id: int, month: str) -> dict:
        """获取指定月份的收入、支出、结余及笔数。"""
        start, end = month_bounds(month)
        rows = self.db.execute(
            select(
                Transaction.type,
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
                func.count().label("count"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.occurred_on >= start,
                Transaction.occurred_on < end,
            )
            .group_by(Transaction.type)
        ).all()
        totals = {
            row.type: {"total": row.total or Decimal("0"), "count": row.count}
            for row in rows
        }
        income = totals.get("income", {}).get("total", Decimal("0"))
        expense = totals.get("expense", {}).get("total", Decimal("0"))

        return {
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "income_count": totals.get("income", {}).get("count", 0),
            "expense_count": totals.get("expense", {}).get("count", 0),
        }

    def get_monthly_trend(self, user_id: int, year: int) -> list[dict]:
        """获取指定年份 1-12 月的收支趋势。"""
        month_expr = extract("month", Transaction.occurred_on)
        rows = self.db.execute(
            select(
                month_expr.label("month"),
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.type == "income", Transaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("income"),
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.type == "expense", Transaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("expense"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.occurred_on >= date(year, 1, 1),
                Transaction.occurred_on < date(year + 1, 1, 1),
            )
            .group_by(month_expr)
        ).all()
        totals = {
            int(row.month): {
                "income": Decimal(row.income or 0),
                "expense": Decimal(row.expense or 0),
            }
            for row in rows
        }
        return [
            {
                "month": f"{month:02d}",
                "income": float(totals.get(month, {}).get("income", 0)),
                "expense": float(totals.get(month, {}).get("expense", 0)),
            }
            for month in range(1, 13)
        ]

    def get_category_summary(self, user_id: int, month: str) -> list[dict]:
        """获取指定月份支出分类占比。"""
        start, end = month_bounds(month)
        stmt = (
            select(Category.name, func.coalesce(func.sum(Transaction.amount), 0).label("total"))
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.occurred_on >= start,
                Transaction.occurred_on < end,
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
        rows = self.db.execute(stmt).all()
        return [{"name": r.name, "amount": float(r.total)} for r in rows]

    def get_month_expense(self, user_id: int, month: str) -> Decimal:
        """获取指定月份的支出总额（用于预算使用率）。"""
        start, end = month_bounds(month)
        expense = self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.occurred_on >= start,
                Transaction.occurred_on < end,
            )
        )
        return expense or Decimal("0")

    def get_budget(self, user_id: int, month: str) -> Optional[dict]:
        """获取指定月份预算及使用率，无预算返回 None。"""
        budget = self.db.scalar(
            select(Budget).where(
                Budget.user_id == user_id,
                Budget.month == month,
                Budget.category_id.is_(None),
            )
        )
        if budget is None:
            return None
        expense = self.get_month_expense(user_id, month)
        usage_percent = float(expense / budget.amount * 100) if budget.amount > 0 else 0.0
        return {
            "amount": budget.amount,
            "usage_percent": usage_percent,
            "remaining": budget.amount - expense,
        }

    def set_budget(self, user_id: int, month: str, amount: Decimal) -> Budget:
        """设置（新增或更新）指定月份预算。"""
        budget = self.db.scalar(
            select(Budget).where(
                Budget.user_id == user_id,
                Budget.month == month,
                Budget.category_id.is_(None),
            )
        )
        if budget is None:
            budget = Budget(user_id=user_id, month=month, amount=amount)
            self.db.add(budget)
        else:
            budget.amount = amount
        self.db.commit()
        self.db.refresh(budget)
        return budget

    def list_budgets(self, user_id: int) -> list[dict]:
        """获取所有历史预算，附带每月支出与使用率。"""
        budgets = list(
            self.db.scalars(
                select(Budget)
                .where(
                    Budget.user_id == user_id,
                    Budget.category_id.is_(None),
                )
                .order_by(Budget.month.desc())
            )
        )
        if not budgets:
            return []

        months = [budget.month for budget in budgets]
        min_start, _ = month_bounds(min(months))
        _, max_end = month_bounds(max(months))
        dialect_name = self.db.get_bind().dialect.name
        if dialect_name == "mysql":
            month_expr = func.date_format(Transaction.occurred_on, "%Y-%m")
        else:
            month_expr = func.strftime("%Y-%m", Transaction.occurred_on)
        expense_rows = self.db.execute(
            select(
                month_expr.label("month"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.occurred_on >= min_start,
                Transaction.occurred_on < max_end,
            )
            .group_by(month_expr)
        ).all()
        expenses = {
            row.month: Decimal(row.total or 0)
            for row in expense_rows
        }

        result = []
        for budget in budgets:
            expense = expenses.get(budget.month, Decimal("0"))
            usage_percent = (
                float(expense / budget.amount * 100) if budget.amount > 0 else 0.0
            )
            result.append(
                {
                    "month": budget.month,
                    "amount": budget.amount,
                    "expense": expense,
                    "usage_percent": usage_percent,
                    "remaining": budget.amount - expense,
                }
            )
        return result

    def list_category_budgets(self, user_id: int, month: str) -> list[dict]:
        """返回支出分类的预算、实际支出和使用率。"""
        start, end = month_bounds(month)
        categories = list(
            self.db.scalars(
                select(Category)
                .where(Category.type == "expense")
                .order_by(Category.id)
            )
        )
        budgets = {
            budget.category_id: budget
            for budget in self.db.scalars(
                select(Budget).where(
                    Budget.user_id == user_id,
                    Budget.month == month,
                    Budget.category_id.is_not(None),
                )
            )
        }
        expense_rows = self.db.execute(
            select(
                Transaction.category_id,
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.occurred_on >= start,
                Transaction.occurred_on < end,
            )
            .group_by(Transaction.category_id)
        ).all()
        expenses = {
            row.category_id: Decimal(row.total or 0)
            for row in expense_rows
        }

        result = []
        for category in categories:
            budget = budgets.get(category.id)
            expense = expenses.get(category.id, Decimal("0"))
            amount = budget.amount if budget else None
            usage_percent = (
                float(expense / amount * 100)
                if amount is not None and amount > 0
                else 0.0
            )
            result.append(
                {
                    "id": budget.id if budget else None,
                    "category_id": category.id,
                    "category_name": category.name,
                    "amount": amount,
                    "expense": expense,
                    "usage_percent": usage_percent,
                    "remaining": amount - expense if amount is not None else None,
                }
            )
        return result

    def set_category_budget(
        self,
        user_id: int,
        month: str,
        category_id: int,
        amount: Decimal,
    ) -> Budget:
        """新增或更新指定分类的月度预算。"""
        month_bounds(month)
        category = self.db.get(Category, category_id)
        if category is None or category.type != "expense":
            raise ValueError("分类不存在或不是支出分类")

        budget = self.db.scalar(
            select(Budget).where(
                Budget.user_id == user_id,
                Budget.month == month,
                Budget.category_id == category_id,
            )
        )
        if budget is None:
            budget = Budget(
                user_id=user_id,
                category_id=category_id,
                month=month,
                amount=amount,
            )
            self.db.add(budget)
        else:
            budget.amount = amount
        self.db.commit()
        self.db.refresh(budget)
        return budget

    def delete_category_budget(
        self,
        user_id: int,
        month: str,
        category_id: int,
    ) -> None:
        """删除分类预算。"""
        budget = self.db.scalar(
            select(Budget).where(
                Budget.user_id == user_id,
                Budget.month == month,
                Budget.category_id == category_id,
            )
        )
        if budget is None:
            raise ValueError("分类预算不存在")
        self.db.delete(budget)
        self.db.commit()
