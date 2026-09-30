"""FastAPI 依赖项：数据库会话和当前登录用户。"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def get_current_user_id(request: Request) -> Optional[int]:
    """从 session 读取当前登录用户 ID，未登录返回 None。"""
    return request.session.get("user_id")


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """认证依赖：未登录返回 401 JSON（SPA 前端自行跳转登录页）。"""
    user_id = get_current_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期")
    user = db.get(User, user_id)
    if user is None:
        # session 中的用户不存在，清空 session
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在，请重新登录")
    if not user.is_active:
        # 管理员禁用账号后，已存在的 Session 必须立即失效，
        # 否则被禁用用户仍可继续访问业务接口直到 Cookie 过期。
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号已被禁用")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    """管理员依赖：普通用户返回 403。"""
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无管理员权限")
    return user
