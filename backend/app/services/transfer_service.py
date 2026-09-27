"""转账服务：账户间资金移动，不进入收入支出统计。"""
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, aliased

from app.models import Account, Transfer
from app.schemas import TransferCreate, TransferUpdate
from app.services.account_service import AccountError, AccountService


class TransferError(Exception):
    """转账业务异常。"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class TransferService:
    """转账服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_transfer(self, user_id: int, transfer_id: int) -> Optional[Transfer]:
        transfer = self.db.get(Transfer, transfer_id)
        if transfer is None or transfer.user_id != user_id:
            return None
        return transfer

    def _validate_accounts(
        self,
        user_id: int,
        from_account_id: int,
        to_account_id: int,
    ) -> tuple[Account, Account]:
        if from_account_id == to_account_id:
            raise TransferError("转出账户和转入账户不能相同")
        accounts = AccountService(self.db)
        try:
            from_account = accounts.require_account(user_id, from_account_id)
            to_account = accounts.require_account(user_id, to_account_id)
        except AccountError as exc:
            raise TransferError(exc.message) from exc
        return from_account, to_account

    def create_transfer(self, user_id: int, data: TransferCreate) -> Transfer:
        """创建转账。"""
        self._validate_accounts(user_id, data.from_account_id, data.to_account_id)
        transfer = Transfer(
            user_id=user_id,
            from_account_id=data.from_account_id,
            to_account_id=data.to_account_id,
            amount=data.amount,
            occurred_on=data.occurred_on,
            note=data.note,
        )
        self.db.add(transfer)
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def update_transfer(
        self,
        user_id: int,
        transfer_id: int,
        data: TransferUpdate,
    ) -> Transfer:
        """更新转账。"""
        transfer = self.get_transfer(user_id, transfer_id)
        if transfer is None:
            raise TransferError("转账记录不存在")

        update_data = data.model_dump(exclude_unset=True)
        final_from = update_data.get("from_account_id", transfer.from_account_id)
        final_to = update_data.get("to_account_id", transfer.to_account_id)
        self._validate_accounts(user_id, final_from, final_to)
        for field, value in update_data.items():
            setattr(transfer, field, value)
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def delete_transfer(self, user_id: int, transfer_id: int) -> None:
        """删除转账。"""
        transfer = self.get_transfer(user_id, transfer_id)
        if transfer is None:
            raise TransferError("转账记录不存在")
        self.db.delete(transfer)
        self.db.commit()

    def list_transfers(self, user_id: int) -> list[dict]:
        """返回当前用户全部转账记录。"""
        from_account = aliased(Account)
        to_account = aliased(Account)
        rows = self.db.execute(
            select(
                Transfer,
                from_account.name.label("from_account_name"),
                to_account.name.label("to_account_name"),
            )
            .join(from_account, Transfer.from_account_id == from_account.id)
            .join(to_account, Transfer.to_account_id == to_account.id)
            .where(Transfer.user_id == user_id)
            .order_by(desc(Transfer.occurred_on), desc(Transfer.id))
        ).all()
        return [
            self.serialize_transfer(transfer, from_name, to_name)
            for transfer, from_name, to_name in rows
        ]

    @staticmethod
    def serialize_transfer(
        transfer: Transfer,
        from_account_name: str,
        to_account_name: str,
    ) -> dict:
        """序列化转账。"""
        return {
            "id": transfer.id,
            "from_account_id": transfer.from_account_id,
            "from_account_name": from_account_name,
            "to_account_id": transfer.to_account_id,
            "to_account_name": to_account_name,
            "amount": float(transfer.amount),
            "occurred_on": transfer.occurred_on.isoformat(),
            "note": transfer.note,
        }
