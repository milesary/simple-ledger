"""账户 API：账户管理、余额和归档。"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_user
from app.schemas import AccountCreate, AccountUpdate
from app.services.account_service import AccountError, AccountService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("")
def list_accounts(
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """返回账户列表、实时余额和总余额。"""
    accounts = AccountService(db).list_accounts(user.id)
    return {
        "accounts": accounts,
        "total_balance": float(
            sum(
                (Decimal(str(account["balance"])) for account in accounts),
                Decimal("0"),
            )
        ),
    }


@router.post("")
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """创建资金账户。"""
    service = AccountService(db)
    try:
        account = service.create_account(user.id, payload)
    except AccountError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    return {
        "success": True,
        "message": "账户已创建",
        "account": service.serialize_account(account),
    }


@router.put("/{account_id}")
def update_account(
    account_id: int,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """更新账户。"""
    service = AccountService(db)
    try:
        account = service.update_account(user.id, account_id, payload)
    except AccountError as exc:
        status = 404 if exc.message == "账户不存在" else 400
        raise HTTPException(status_code=status, detail=exc.message) from exc
    return {
        "success": True,
        "message": "账户已更新",
        "account": service.serialize_account(account),
    }


@router.post("/{account_id}/archive")
def archive_account(
    account_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """归档账户，不删除历史流水。"""
    service = AccountService(db)
    try:
        account = service.archive_account(user.id, account_id)
    except AccountError as exc:
        status = 404 if exc.message == "账户不存在" else 400
        raise HTTPException(status_code=status, detail=exc.message) from exc
    return {
        "success": True,
        "message": "账户已归档",
        "account": service.serialize_account(account),
    }
