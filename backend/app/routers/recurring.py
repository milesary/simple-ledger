"""周期流水 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_user
from app.schemas import RecurringCreate, RecurringUpdate
from app.services.recurring_service import (
    RecurringError,
    RecurringTransactionService,
)

router = APIRouter(prefix="/api/recurring", tags=["recurring"])


@router.get("")
def list_recurring(
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """生成到期流水并返回周期规则。"""
    service = RecurringTransactionService(db)
    generated_count = service.materialize_due(user.id)
    return {
        "recurring": service.list_rules(user.id, materialize=False),
        "generated_count": generated_count,
    }


@router.post("")
def create_recurring(
    payload: RecurringCreate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """创建周期流水规则。"""
    service = RecurringTransactionService(db)
    try:
        rule = service.create_rule(user.id, payload)
    except RecurringError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    category_name = rule.category.name if rule.category else ""
    account_name = rule.account.name if rule.account else None
    return {
        "success": True,
        "message": "周期规则已创建",
        "recurring": service.serialize_rule(rule, category_name, account_name),
    }


@router.put("/{rule_id}")
def update_recurring(
    rule_id: int,
    payload: RecurringUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """更新周期流水规则。"""
    service = RecurringTransactionService(db)
    try:
        rule = service.update_rule(user.id, rule_id, payload)
    except RecurringError as exc:
        status = 404 if exc.message == "周期规则不存在" else 400
        raise HTTPException(status_code=status, detail=exc.message) from exc
    category_name = rule.category.name if rule.category else ""
    account_name = rule.account.name if rule.account else None
    return {
        "success": True,
        "message": "周期规则已更新",
        "recurring": service.serialize_rule(rule, category_name, account_name),
    }


@router.post("/{rule_id}/toggle")
def toggle_recurring(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """启用或暂停周期规则。"""
    service = RecurringTransactionService(db)
    rule = service.get_rule(user.id, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="周期规则不存在")
    rule.is_active = not rule.is_active
    db.commit()
    db.refresh(rule)
    category_name = rule.category.name if rule.category else ""
    account_name = rule.account.name if rule.account else None
    return {
        "success": True,
        "message": "周期规则状态已更新",
        "recurring": service.serialize_rule(rule, category_name, account_name),
    }


@router.delete("/{rule_id}")
def delete_recurring(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """删除周期规则。"""
    try:
        RecurringTransactionService(db).delete_rule(user.id, rule_id)
    except RecurringError as exc:
        status = 404 if exc.message == "周期规则不存在" else 400
        raise HTTPException(status_code=status, detail=exc.message) from exc
    return {"success": True, "message": "周期规则已删除"}
