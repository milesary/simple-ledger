"""认证路由：JSON API 形式的登录验证码发送、校验与退出。"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_user
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SendCodeRequest(BaseModel):
    """发送验证码请求体。"""
    email: str


class VerifyCodeRequest(BaseModel):
    """校验验证码请求体。"""
    email: str
    code: str


class RegisterRequest(BaseModel):
    """注册请求体。"""

    email: str
    password: str


class PasswordLoginRequest(BaseModel):
    """密码登录请求体。"""

    email: str
    password: str


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """注册账号，注册成功后仍需主动登录。"""
    service = AuthService(db)
    try:
        service.register(payload.email, payload.password)
    except AuthError as exc:
        return {"success": False, "message": exc.message}
    return {"success": True, "message": "注册成功，请登录"}


@router.post("/login")
def login_with_password(
    payload: PasswordLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """使用邮箱和密码登录。"""
    service = AuthService(db)
    try:
        user = service.login_with_password(payload.email, payload.password)
    except AuthError as exc:
        return {"success": False, "message": exc.message}

    request.session.clear()
    request.session["user_id"] = user.id
    return {
        "success": True,
        "message": "登录成功",
        "user": {
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
        },
    }


@router.post("/code")
def send_code(payload: SendCodeRequest, request: Request, db: Session = Depends(get_db)):
    """发送登录验证码。"""
    service = AuthService(db)
    try:
        service.request_login_code(payload.email)
    except AuthError as exc:
        return {"success": False, "message": exc.message}

    # 待验证邮箱存入 session，前端无需再传
    request.session["pending_login_email"] = payload.email.strip().lower()
    return {"success": True, "message": "验证码已发送"}


@router.post("/verify")
def verify_code(payload: VerifyCodeRequest, request: Request, db: Session = Depends(get_db)):
    """校验验证码，成功后写入 session。"""
    email = request.session.get("pending_login_email", "")
    if not email:
        return {"success": False, "message": "请先获取验证码"}

    service = AuthService(db)
    try:
        user = service.verify_login_code(email, payload.code)
    except AuthError as exc:
        return {"success": False, "message": exc.message}

    request.session.clear()
    request.session["user_id"] = user.id
    return {
        "success": True,
        "message": "登录成功",
        "user": {"id": user.id, "email": user.email},
    }


@router.post("/logout")
def logout(request: Request):
    """退出登录：清空 session。"""
    request.session.clear()
    return {"success": True, "message": "已退出登录"}


@router.get("/me")
def get_me(user=Depends(require_user)):
    """获取当前登录用户信息。"""
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin}
