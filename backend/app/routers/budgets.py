"""预算路由：JSON API 形式的预算查询与设置。"""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_user
from app.schemas import CategoryBudgetSetRequest
from app.services.stats_service import StatsService, month_bounds

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


class BudgetSetRequest(BaseModel):
    """预算设置请求体。"""
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        """校验月份不仅格式匹配，而且月份值真实存在。"""
        month_bounds(value)
        return value


def _current_month() -> str:
    """返回当前月份字符串 YYYY-MM。"""
    today = date.today()
    return f"{today.year}-{today.month:02d}"


@router.get("")
def budgets_index(
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """预算页数据：当月预算、当月支出、历史预算列表。"""
    current_month = _current_month()
    stats = StatsService(db)
    current_budget = stats.get_budget(user.id, current_month)
    current_expense = stats.get_month_expense(user.id, current_month)
    history = stats.list_budgets(user.id)
    category_budgets = stats.list_category_budgets(user.id, current_month)

    return {
        "current_month": current_month,
        "current_budget": current_budget,
        "current_expense": float(current_expense),
        "category_budgets": [
            {
                **item,
                "amount": float(item["amount"]) if item["amount"] is not None else None,
                "expense": float(item["expense"]),
                "remaining": (
                    float(item["remaining"])
                    if item["remaining"] is not None
                    else None
                ),
            }
            for item in category_budgets
        ],
        "history": [
            {
                "month": h["month"],
                "amount": float(h["amount"]),
                "expense": float(h["expense"]),
                "usage_percent": h["usage_percent"],
                "remaining": float(h["remaining"]),
            }
            for h in history
        ],
    }


@router.post("")
def create_budget(
    payload: BudgetSetRequest,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """设置（新增或更新）指定月份预算。"""
    stats = StatsService(db)
    budget = stats.set_budget(user.id, payload.month, payload.amount.quantize(Decimal("0.01")))
    return {
        "success": True,
        "message": "预算已保存",
        "budget": {"month": budget.month, "amount": float(budget.amount)},
    }


@router.post("/categories")
def set_category_budget(
    payload: CategoryBudgetSetRequest,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """设置或更新指定分类的月度预算。"""
    try:
        budget = StatsService(db).set_category_budget(
            user.id,
            payload.month,
            payload.category_id,
            payload.amount.quantize(Decimal("0.01")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "success": True,
        "message": "分类预算已保存",
        "budget": {
            "month": budget.month,
            "category_id": budget.category_id,
            "amount": float(budget.amount),
        },
    }


@router.delete("/categories")
def delete_category_budget(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    category_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """删除指定分类的月度预算。"""
    try:
        month_bounds(month)
        StatsService(db).delete_category_budget(user.id, month, category_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "message": "分类预算已删除"}
