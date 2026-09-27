"""流水路由：JSON CRUD API，支持筛选、分页与分类查询。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import PAGE_SIZE
from app.database import get_db
from app.dependencies import require_user
from app.models import Account, Category, Transaction
from app.schemas import TransactionCreate, TransactionUpdate
from app.services.transaction_service import TransactionError, TransactionService

router = APIRouter(prefix="/api", tags=["transactions"])


def _load_categories(db: Session) -> list[dict]:
    """加载全部分类列表。"""
    rows = db.scalars(select(Category).order_by(Category.type, Category.id)).all()
    return [{"id": c.id, "name": c.name, "type": c.type} for c in rows]


def _load_accounts(db: Session, user_id: int) -> list[dict]:
    """加载当前用户可见账户的名称映射。"""
    rows = db.scalars(
        select(Account)
        .where(Account.user_id == user_id)
        .order_by(Account.is_archived, Account.id)
    ).all()
    return [
        {"id": account.id, "name": account.name, "is_archived": account.is_archived}
        for account in rows
    ]


def _serialize_transaction(
    tx: Transaction,
    categories_map: dict[int, str],
    accounts_map: dict[int, str],
) -> dict:
    """将流水对象序列化为 JSON 友好的字典。"""
    return {
        "id": tx.id,
        "type": tx.type,
        "amount": float(tx.amount),
        "category_id": tx.category_id,
        "category_name": categories_map.get(tx.category_id, ""),
        "account_id": tx.account_id,
        "account_name": accounts_map.get(tx.account_id, "") if tx.account_id else "",
        "occurred_on": tx.occurred_on.isoformat(),
        "payment_method": tx.payment_method,
        "note": tx.note,
    }


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), user=Depends(require_user)):
    """获取全部分类列表（系统预置）。"""
    return {"categories": _load_categories(db)}


@router.get("/transactions")
def list_transactions(
    month: str = "",
    account: int | None = None,
    category: int | None = None,
    type: str = "",
    q: str = "",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """流水列表，支持按月、分类、类型、关键词筛选与分页。"""
    service = TransactionService(db)
    try:
        rows, total = service.list_transactions(
            user_id=user.id,
            month=month or None,
            account_id=account,
            category_id=category,
            type_=type or None,
            q=q or None,
            page=page,
            page_size=PAGE_SIZE,
        )
    except TransactionError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    categories_map = {c["id"]: c["name"] for c in _load_categories(db)}
    accounts_map = {
        item["id"]: item["name"] for item in _load_accounts(db, user.id)
    }
    transactions = [
        _serialize_transaction(tx, categories_map, accounts_map) for tx in rows
    ]

    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return {
        "transactions": transactions,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """获取单条流水详情。"""
    service = TransactionService(db)
    tx = service.get_transaction(user.id, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="流水不存在")
    categories_map = {c["id"]: c["name"] for c in _load_categories(db)}
    accounts_map = {
        item["id"]: item["name"] for item in _load_accounts(db, user.id)
    }
    return {
        "transaction": _serialize_transaction(tx, categories_map, accounts_map)
    }


@router.post("/transactions")
def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """新增一条流水。"""
    service = TransactionService(db)
    try:
        tx = service.create_transaction(user.id, data)
    except TransactionError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    categories_map = {c["id"]: c["name"] for c in _load_categories(db)}
    accounts_map = {
        item["id"]: item["name"] for item in _load_accounts(db, user.id)
    }
    return {
        "success": True,
        "transaction": _serialize_transaction(tx, categories_map, accounts_map),
    }


@router.put("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """更新一条流水。"""
    service = TransactionService(db)
    try:
        tx = service.update_transaction(user.id, transaction_id, data)
    except TransactionError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    categories_map = {c["id"]: c["name"] for c in _load_categories(db)}
    accounts_map = {
        item["id"]: item["name"] for item in _load_accounts(db, user.id)
    }
    return {
        "success": True,
        "transaction": _serialize_transaction(tx, categories_map, accounts_map),
    }


@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """删除一条流水。"""
    service = TransactionService(db)
    try:
        service.delete_transaction(user.id, transaction_id)
    except TransactionError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    return {"success": True, "message": "流水已删除"}
