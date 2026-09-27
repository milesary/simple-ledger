"""Dashboard 路由：JSON API 形式的月度汇总、趋势、分类占比、预算与最近流水。"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_user
from app.models import Account, Category, Transaction
from app.services.account_service import AccountService
from app.services.recurring_service import RecurringTransactionService
from app.services.stats_service import StatsService

router = APIRouter(prefix="/api", tags=["dashboard"])


def _current_month() -> str:
    """返回当前月份字符串 YYYY-MM。"""
    today = date.today()
    return f"{today.year}-{today.month:02d}"


@router.get("/dashboard")
def dashboard(
    year: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """概览数据：月度汇总、年度趋势、当月分类占比、预算、最近 5 条流水。"""
    today = date.today()
    current_year = year or today.year
    current_month = _current_month()

    RecurringTransactionService(db).materialize_due(user.id)
    stats = StatsService(db)
    summary = stats.get_monthly_summary(user.id, current_month)
    trend = stats.get_monthly_trend(user.id, current_year)
    categories = stats.get_category_summary(user.id, current_month)
    budget = stats.get_budget(user.id, current_month)

    # 最近 5 条流水（含分类名称）
    recent = db.execute(
        select(Transaction, Category.name, Account.name)
        .join(Category, Transaction.category_id == Category.id)
        .outerjoin(Account, Transaction.account_id == Account.id)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.occurred_on), desc(Transaction.id))
        .limit(5)
    ).all()
    recent_transactions = []
    for transaction, category_name, account_name in recent:
        recent_transactions.append(
            {
                "id": transaction.id,
                "type": transaction.type,
                "amount": float(transaction.amount),
                "category_name": category_name,
                "account_id": transaction.account_id,
                "account_name": account_name or "",
                "occurred_on": transaction.occurred_on.isoformat(),
                "payment_method": transaction.payment_method,
                "note": transaction.note,
            }
        )

    accounts = AccountService(db).list_accounts(user.id)
    return {
        "current_month": current_month,
        "current_year": current_year,
        "summary": {
            "income": float(summary["income"]),
            "expense": float(summary["expense"]),
            "balance": float(summary["balance"]),
            "income_count": summary["income_count"],
            "expense_count": summary["expense_count"],
        },
        "trend": trend,
        "categories": categories,
        "budget": budget,
        "account_summary": {
            "count": len(accounts),
            "total_balance": sum(account["balance"] for account in accounts),
        },
        "accounts": accounts,
        "recent_transactions": recent_transactions,
    }


@router.get("/stats/monthly")
def api_monthly(
    year: int = Query(..., ge=1900, le=9999),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """返回指定年份各月收支趋势。"""
    stats = StatsService(db)
    trend = stats.get_monthly_trend(user.id, year)
    return {"year": year, "trend": trend}


@router.get("/stats/categories")
def api_categories(
    month: str,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """返回指定月份支出分类占比。"""
    stats = StatsService(db)
    try:
        categories = stats.get_category_summary(user.id, month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"month": month, "categories": categories}
