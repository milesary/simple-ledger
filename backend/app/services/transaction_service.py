"""流水服务：新增、编辑、删除、筛选与分页。"""
from typing import Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.models import Category, Transaction
from app.schemas import TransactionCreate, TransactionUpdate
from app.services.account_service import AccountError, AccountService
from app.services.stats_service import month_bounds


class TransactionError(Exception):
    """流水业务异常。"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class TransactionService:
    """流水管理服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _validate_category_type(self, type_: str, category_id: int) -> Category:
        """校验分类存在且类型与收支类型匹配。"""
        category = self.db.get(Category, category_id)
        if category is None:
            raise TransactionError("分类不存在")
        if category.type != type_:
            raise TransactionError("收支类型与分类不匹配")
        return category

    def create_transaction(self, user_id: int, data: TransactionCreate) -> Transaction:
        """新增一条流水。"""
        self._validate_category_type(data.type, data.category_id)
        if data.account_id is not None:
            try:
                AccountService(self.db).require_account(user_id, data.account_id)
            except AccountError as exc:
                raise TransactionError(exc.message) from exc
        tx = Transaction(
            user_id=user_id,
            account_id=data.account_id,
            type=data.type,
            amount=data.amount,
            category_id=data.category_id,
            occurred_on=data.occurred_on,
            payment_method=data.payment_method,
            note=data.note,
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return tx

    def get_transaction(self, user_id: int, transaction_id: int) -> Optional[Transaction]:
        """获取指定流水（带归属校验）。"""
        tx = self.db.get(Transaction, transaction_id)
        if tx is None or tx.user_id != user_id:
            return None
        return tx

    def update_transaction(
        self, user_id: int, transaction_id: int, data: TransactionUpdate
    ) -> Transaction:
        """编辑流水，校验归属与分类类型。"""
        tx = self.get_transaction(user_id, transaction_id)
        if tx is None:
            raise TransactionError("流水不存在")

        # 确定最终类型：优先用传入值，否则保留原值
        final_type = data.type if data.type is not None else tx.type
        final_category_id = data.category_id if data.category_id is not None else tx.category_id
        update_data = data.model_dump(exclude_unset=True)
        final_account_id = update_data.get("account_id", tx.account_id)
        self._validate_category_type(final_type, final_category_id)
        if final_account_id is not None:
            try:
                AccountService(self.db).require_account(user_id, final_account_id)
            except AccountError as exc:
                raise TransactionError(exc.message) from exc

        for field, value in update_data.items():
            setattr(tx, field, value)

        self.db.commit()
        self.db.refresh(tx)
        return tx

    def delete_transaction(self, user_id: int, transaction_id: int) -> None:
        """删除流水，校验归属。"""
        tx = self.get_transaction(user_id, transaction_id)
        if tx is None:
            raise TransactionError("流水不存在")
        self.db.delete(tx)
        self.db.commit()

    def list_transactions(
        self,
        user_id: int,
        month: Optional[str] = None,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        type_: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Transaction], int]:
        """筛选流水列表，返回 (分页数据, 总条数)。"""
        conditions = [Transaction.user_id == user_id]

        if month:
            try:
                start, end = month_bounds(month)
            except ValueError as exc:
                raise TransactionError(str(exc)) from exc
            conditions.append(
                and_(
                    Transaction.occurred_on >= start,
                    Transaction.occurred_on < end,
                )
            )
        if category_id:
            conditions.append(Transaction.category_id == category_id)
        if account_id:
            conditions.append(Transaction.account_id == account_id)
        if type_ in ("income", "expense"):
            conditions.append(Transaction.type == type_)
        if q:
            conditions.append(Transaction.note.like(f"%{q}%"))

        where_clause = and_(*conditions)

        total = self.db.scalar(
            select(func.count()).select_from(Transaction).where(where_clause)
        )

        stmt = (
            select(Transaction)
            .where(where_clause)
            .order_by(desc(Transaction.occurred_on), desc(Transaction.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list(self.db.scalars(stmt))
        return rows, total
