"""周期流水服务：规则管理和到期流水生成。"""
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, RecurringTransaction, Transaction
from app.schemas import RecurringCreate, RecurringUpdate
from app.services.account_service import AccountError, AccountService

MAX_GENERATED_PER_CALL = 500


class RecurringError(Exception):
    """周期流水业务异常。"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def next_occurrence(
    current: date,
    frequency: str,
    interval: int,
    anchor_day: int,
) -> date:
    """计算下一次执行日期。"""
    if frequency == "daily":
        return current + timedelta(days=interval)
    if frequency == "weekly":
        return current + timedelta(weeks=interval)
    if frequency == "monthly":
        month_index = current.year * 12 + current.month - 1 + interval
        year, zero_based_month = divmod(month_index, 12)
        month = zero_based_month + 1
        day = min(anchor_day, monthrange(year, month)[1])
        return date(year, month, day)
    if frequency == "yearly":
        year = current.year + interval
        day = min(anchor_day, monthrange(year, current.month)[1])
        return date(year, current.month, day)
    raise RecurringError("不支持的周期频率")


class RecurringTransactionService:
    """周期流水规则服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _validate_category(self, type_: str, category_id: int) -> Category:
        category = self.db.get(Category, category_id)
        if category is None or category.type != type_:
            raise RecurringError("分类不存在或与收支类型不匹配")
        return category

    def _validate_account(self, user_id: int, account_id: int | None) -> None:
        if account_id is None:
            return
        try:
            AccountService(self.db).require_account(user_id, account_id)
        except AccountError as exc:
            raise RecurringError(exc.message) from exc

    def _validate_dates(
        self,
        start_date: date,
        end_date: date | None,
    ) -> None:
        if end_date is not None and end_date < start_date:
            raise RecurringError("结束日期不能早于开始日期")

    def get_rule(
        self,
        user_id: int,
        rule_id: int,
    ) -> Optional[RecurringTransaction]:
        rule = self.db.get(RecurringTransaction, rule_id)
        if rule is None or rule.user_id != user_id:
            return None
        return rule

    def create_rule(
        self,
        user_id: int,
        data: RecurringCreate,
    ) -> RecurringTransaction:
        """创建周期规则。"""
        self._validate_category(data.type, data.category_id)
        self._validate_account(user_id, data.account_id)
        self._validate_dates(data.start_date, data.end_date)
        rule = RecurringTransaction(
            user_id=user_id,
            type=data.type,
            amount=data.amount,
            category_id=data.category_id,
            account_id=data.account_id,
            frequency=data.frequency,
            interval=data.interval,
            start_date=data.start_date,
            next_run_date=data.start_date,
            end_date=data.end_date,
            payment_method=data.payment_method,
            note=data.note,
            is_active=True,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_rule(
        self,
        user_id: int,
        rule_id: int,
        data: RecurringUpdate,
    ) -> RecurringTransaction:
        """更新周期规则。"""
        rule = self.get_rule(user_id, rule_id)
        if rule is None:
            raise RecurringError("周期规则不存在")

        update_data = data.model_dump(exclude_unset=True)
        final_type = update_data.get("type", rule.type)
        final_category_id = update_data.get("category_id", rule.category_id)
        final_account_id = update_data.get("account_id", rule.account_id)
        final_start = update_data.get("start_date", rule.start_date)
        final_end = update_data.get("end_date", rule.end_date)
        self._validate_category(final_type, final_category_id)
        self._validate_account(user_id, final_account_id)
        self._validate_dates(final_start, final_end)

        if "start_date" in update_data:
            update_data["next_run_date"] = final_start
        for field, value in update_data.items():
            setattr(rule, field, value)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, user_id: int, rule_id: int) -> None:
        """删除周期规则，已生成流水不受影响。"""
        rule = self.get_rule(user_id, rule_id)
        if rule is None:
            raise RecurringError("周期规则不存在")
        self.db.delete(rule)
        self.db.commit()

    def materialize_due(self, user_id: int, through: date | None = None) -> int:
        """生成截至指定日期尚未落库的流水，返回生成数量。"""
        through = through or date.today()
        rules = list(
            self.db.scalars(
                select(RecurringTransaction)
                .where(
                    RecurringTransaction.user_id == user_id,
                    RecurringTransaction.is_active.is_(True),
                    RecurringTransaction.next_run_date <= through,
                )
                .order_by(RecurringTransaction.next_run_date)
            )
        )
        if not rules:
            return 0

        generated = 0
        changed = False
        for rule in rules:
            while (
                rule.is_active
                and rule.next_run_date <= through
                and generated < MAX_GENERATED_PER_CALL
            ):
                if rule.end_date is not None and rule.next_run_date > rule.end_date:
                    rule.is_active = False
                    changed = True
                    break

                self.db.add(
                    Transaction(
                        user_id=user_id,
                        account_id=rule.account_id,
                        type=rule.type,
                        amount=rule.amount,
                        category_id=rule.category_id,
                        occurred_on=rule.next_run_date,
                        payment_method=rule.payment_method,
                        note=rule.note,
                    )
                )
                rule.next_run_date = next_occurrence(
                    rule.next_run_date,
                    rule.frequency,
                    rule.interval,
                    rule.start_date.day,
                )
                generated += 1
                changed = True

                if rule.end_date is not None and rule.next_run_date > rule.end_date:
                    rule.is_active = False
                    break

        if changed:
            self.db.commit()
        return generated

    def list_rules(
        self,
        user_id: int,
        *,
        materialize: bool = True,
    ) -> list[dict]:
        """返回规则列表，可选择先生成到期流水。"""
        if materialize:
            self.materialize_due(user_id)
        rules = list(
            self.db.scalars(
                select(RecurringTransaction)
                .where(RecurringTransaction.user_id == user_id)
                .order_by(
                    RecurringTransaction.is_active.desc(),
                    RecurringTransaction.next_run_date,
                )
            )
        )
        categories = {
            category.id: category.name
            for category in self.db.scalars(select(Category)).all()
        }
        accounts = {
            account["id"]: account["name"]
            for account in AccountService(self.db).list_accounts(user_id)
        }
        return [
            self.serialize_rule(
                rule,
                categories.get(rule.category_id, ""),
                accounts.get(rule.account_id) if rule.account_id else None,
            )
            for rule in rules
        ]

    @staticmethod
    def serialize_rule(
        rule: RecurringTransaction,
        category_name: str,
        account_name: str | None,
    ) -> dict:
        """序列化周期规则。"""
        return {
            "id": rule.id,
            "type": rule.type,
            "amount": float(rule.amount),
            "category_id": rule.category_id,
            "category_name": category_name,
            "account_id": rule.account_id,
            "account_name": account_name,
            "frequency": rule.frequency,
            "interval": rule.interval,
            "start_date": rule.start_date.isoformat(),
            "next_run_date": rule.next_run_date.isoformat(),
            "end_date": rule.end_date.isoformat() if rule.end_date else None,
            "payment_method": rule.payment_method,
            "note": rule.note,
            "is_active": rule.is_active,
        }
