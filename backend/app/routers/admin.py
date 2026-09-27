"""管理员 API：账号查询、启停、角色、密码重置和删除。"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import (
    Account,
    Budget,
    LoginCode,
    RecurringTransaction,
    Transaction,
    Transfer,
    User,
)
from app.security import hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ResetPasswordRequest(BaseModel):
    """管理员重置密码请求体。"""

    new_password: str


def _iso(value: Optional[datetime]) -> Optional[str]:
    """将数据库时间统一序列化为 ISO 字符串。"""
    return value.isoformat() if value else None


def _serialize_user(user: User) -> dict:
    """序列化管理员列表中的账号字段。"""
    return {
        "id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": _iso(user.created_at),
        "last_login_at": _iso(user.last_login_at),
    }


def _active_admin_count(db: Session) -> int:
    """返回可用管理员数量。"""
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.is_admin.is_(True), User.is_active.is_(True))
        )
        or 0
    )


def _validate_password(password: str) -> Optional[str]:
    """校验管理员重置的新密码。"""
    if len(password) < 8 or len(password) > 20:
        return "密码长度必须为 8-20 位"
    if not any(char.isdigit() for char in password):
        return "密码必须包含数字"
    if not any(char.isalpha() for char in password):
        return "密码必须包含字母"
    return None


def _get_user_or_404(db: Session, user_id: int) -> User:
    """读取目标账号，不存在时返回 404。"""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    return user


@router.get("/users")
def list_users(
    q: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """查询账号列表并返回当前筛选范围的统计。"""
    stmt = select(User).order_by(User.created_at.desc(), User.id.desc())
    keyword = q.strip()
    if keyword:
        stmt = stmt.where(
            or_(
                User.email.ilike(f"%{keyword}%"),
                User.id == int(keyword) if keyword.isdigit() else False,
            )
        )
    users = list(db.scalars(stmt))
    return {
        "users": [_serialize_user(user) for user in users],
        "total_count": len(users),
        "active_count": sum(1 for user in users if user.is_active),
        "admin_count": sum(1 for user in users if user.is_admin),
        "current_user_id": current_user.id,
    }


@router.post("/users/{user_id}/toggle")
def toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """启用或禁用账号。"""
    user = _get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能禁用自己的账号")
    if user.is_admin and user.is_active and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="系统至少需要保留一个可用管理员")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "账号状态已更新", "user": _serialize_user(user)}


@router.post("/users/{user_id}/role")
def toggle_role(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """授予或取消管理员角色。"""
    user = _get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的管理员角色")
    if user.is_admin and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="系统至少需要保留一个管理员")

    user.is_admin = not user.is_admin
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "管理员权限已更新", "user": _serialize_user(user)}


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """管理员重置指定账号密码。"""
    del current_user
    user = _get_user_or_404(db, user_id)
    error = _validate_password(payload.new_password)
    if error:
        raise HTTPException(status_code=400, detail=error)

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"success": True, "message": f"{user.email} 的密码已重置"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """删除普通账号及其全部业务数据。"""
    user = _get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="请先取消管理员权限，再删除账号")

    try:
        # 按外键依赖顺序清理账号业务数据，避免 MySQL 外键阻止删除。
        db.execute(delete(Transaction).where(Transaction.user_id == user.id))
        db.execute(delete(Transfer).where(Transfer.user_id == user.id))
        db.execute(
            delete(RecurringTransaction).where(
                RecurringTransaction.user_id == user.id
            )
        )
        db.execute(delete(Budget).where(Budget.user_id == user.id))
        db.execute(delete(Account).where(Account.user_id == user.id))
        db.execute(delete(LoginCode).where(LoginCode.email == user.email))
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"success": True, "message": "账号及关联数据已删除"}
