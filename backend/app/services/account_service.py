"""账户服务：账户管理、归属校验和实时余额计算。"""
from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Account, Transaction, Transfer
from app.schemas import AccountCreate, AccountUpdate


class AccountError(Exception):
    """账户业务异常。"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AccountService:
    """账户服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_account(self, user_id: int, account_id: int) -> Optional[Account]:
        """读取当前用户账户。"""
        account = self.db.get(Account, account_id)
        if account is None or account.user_id != user_id:
            return None
        return account

    def require_account(
        self,
        user_id: int,
        account_id: int,
        *,
        require_active: bool = True,
    ) -> Account:
        """读取账户并校验归属与可用状态。"""
        account = self.get_account(user_id, account_id)
        if account is None:
            raise AccountError("账户不存在")
        if require_active and account.is_archived:
            raise AccountError("账户已归档，不能继续记账")
        return account

    def _ensure_unique_name(
        self,
        user_id: int,
        name: str,
        *,
        exclude_account_id: int | None = None,
    ) -> None:
        stmt = select(Account).where(Account.user_id == user_id, Account.name == name)
        if exclude_account_id is not None:
            stmt = stmt.where(Account.id != exclude_account_id)
        if self.db.scalar(stmt) is not None:
            raise AccountError("账户名称已存在")

    def create_account(self, user_id: int, data: AccountCreate) -> Account:
        """创建账户。"""
        self._ensure_unique_name(user_id, data.name)
        account = Account(
            user_id=user_id,
            name=data.name,
            type=data.type,
            initial_balance=data.initial_balance,
            is_archived=False,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update_account(
        self,
        user_id: int,
        account_id: int,
        data: AccountUpdate,
    ) -> Account:
        """更新账户基础信息。"""
        account = self.require_account(user_id, account_id, require_active=False)
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            self._ensure_unique_name(
                user_id,
                update_data["name"],
                exclude_account_id=account.id,
            )
        for field, value in update_data.items():
            setattr(account, field, value)
        self.db.commit()
        self.db.refresh(account)
        return account

    def archive_account(self, user_id: int, account_id: int) -> Account:
        """归档账户，保留历史流水和转账。"""
        account = self.require_account(user_id, account_id, require_active=False)
        account.is_archived = True
        self.db.commit()
        self.db.refresh(account)
        return account

    def list_accounts(
        self,
        user_id: int,
        *,
        include_archived: bool = True,
    ) -> list[dict]:
        """返回账户及实时余额。"""
        stmt = select(Account).where(Account.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(Account.is_archived.is_(False))
        accounts = list(
            self.db.scalars(stmt.order_by(Account.is_archived, Account.id))
        )
        if not accounts:
            return []

        transaction_rows = self.db.execute(
            select(
                Transaction.account_id,
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.type == "income",
                                Transaction.amount,
                            ),
                            else_=-Transaction.amount,
                        )
                    ),
                    0,
                ).label("balance_delta"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.account_id.is_not(None),
            )
            .group_by(Transaction.account_id)
        ).all()
        transfer_out_rows = self.db.execute(
            select(
                Transfer.from_account_id,
                func.coalesce(func.sum(Transfer.amount), 0).label("total"),
            )
            .where(Transfer.user_id == user_id)
            .group_by(Transfer.from_account_id)
        ).all()
        transfer_in_rows = self.db.execute(
            select(
                Transfer.to_account_id,
                func.coalesce(func.sum(Transfer.amount), 0).label("total"),
            )
            .where(Transfer.user_id == user_id)
            .group_by(Transfer.to_account_id)
        ).all()

        transaction_delta = {
            row.account_id: Decimal(row.balance_delta or 0)
            for row in transaction_rows
        }
        transfer_out = {
            row.from_account_id: Decimal(row.total or 0)
            for row in transfer_out_rows
        }
        transfer_in = {
            row.to_account_id: Decimal(row.total or 0)
            for row in transfer_in_rows
        }

        return [
            self.serialize_account(
                account,
                balance=(
                    account.initial_balance
                    + transaction_delta.get(account.id, Decimal("0"))
                    - transfer_out.get(account.id, Decimal("0"))
                    + transfer_in.get(account.id, Decimal("0"))
                ),
            )
            for account in accounts
        ]

    @staticmethod
    def serialize_account(account: Account, *, balance: Decimal | None = None) -> dict:
        """序列化账户。"""
        return {
            "id": account.id,
            "name": account.name,
            "type": account.type,
            "initial_balance": float(account.initial_balance),
            "balance": float(balance if balance is not None else account.initial_balance),
            "is_archived": account.is_archived,
        }
