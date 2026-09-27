"""Pydantic 数据校验模型。"""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TransactionType = Literal["income", "expense"]
AccountType = Literal["cash", "bank", "credit", "investment", "other"]
RecurringFrequency = Literal["daily", "weekly", "monthly", "yearly"]


class TransactionCreate(BaseModel):
    """新增流水校验模型。"""
    type: TransactionType
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    category_id: int = Field(..., gt=0)
    account_id: int | None = Field(None, gt=0)
    occurred_on: date
    payment_method: str | None = Field(None, max_length=20)
    note: str | None = Field(None, max_length=200)


class TransactionUpdate(BaseModel):
    """编辑流水校验模型，所有字段可选。"""
    type: TransactionType | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    category_id: int | None = Field(None, gt=0)
    account_id: int | None = Field(None, gt=0)
    occurred_on: date | None = None
    payment_method: str | None = Field(None, max_length=20)
    note: str | None = Field(None, max_length=200)


class BudgetCreate(BaseModel):
    """预算设置校验模型。"""
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)


class AccountCreate(BaseModel):
    """创建资金账户。"""
    name: str = Field(..., min_length=1, max_length=50)
    type: AccountType = "bank"
    initial_balance: Decimal = Field(
       Decimal("0.00"), max_digits=12, decimal_places=2
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("账户名称不能为空")
        return name


class AccountUpdate(BaseModel):
    """编辑资金账户。"""
    name: str | None = Field(None, min_length=1, max_length=50)
    type: AccountType | None = None
    initial_balance: Decimal | None = Field(
        None, max_digits=12, decimal_places=2
    )

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name:
            raise ValueError("账户名称不能为空")
        return name


class TransferCreate(BaseModel):
    """创建账户间转账。"""
    from_account_id: int = Field(..., gt=0)
    to_account_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    occurred_on: date
    note: str | None = Field(None, max_length=200)

    @field_validator("to_account_id")
    @classmethod
    def validate_distinct_accounts(cls, value: int, info):
        if info.data.get("from_account_id") == value:
            raise ValueError("转出账户和转入账户不能相同")
        return value


class TransferUpdate(BaseModel):
    """编辑账户间转账。"""
    from_account_id: int | None = Field(None, gt=0)
    to_account_id: int | None = Field(None, gt=0)
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    occurred_on: date | None = None
    note: str | None = Field(None, max_length=200)


class RecurringCreate(BaseModel):
    """创建周期流水规则。"""
    type: TransactionType
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    category_id: int = Field(..., gt=0)
    account_id: int | None = Field(None, gt=0)
    frequency: RecurringFrequency
    interval: int = Field(1, ge=1, le=365)
    start_date: date
    end_date: date | None = None
    payment_method: str | None = Field(None, max_length=20)
    note: str | None = Field(None, max_length=200)

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, value: date | None, info):
        start_date = info.data.get("start_date")
        if value is not None and start_date is not None and value < start_date:
            raise ValueError("结束日期不能早于开始日期")
        return value


class RecurringUpdate(BaseModel):
    """编辑周期流水规则。"""
    type: TransactionType | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    category_id: int | None = Field(None, gt=0)
    account_id: int | None = Field(None, gt=0)
    frequency: RecurringFrequency | None = None
    interval: int | None = Field(None, ge=1, le=365)
    start_date: date | None = None
    end_date: date | None = None
    payment_method: str | None = Field(None, max_length=20)
    note: str | None = Field(None, max_length=200)
    is_active: bool | None = None


class CategoryBudgetSetRequest(BaseModel):
    """设置分类月度预算。"""
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    category_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
