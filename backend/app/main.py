"""简账 SimpleLedger 应用入口：组装路由、初始化数据库与默认分类。"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    APP_ENV,
    CORS_ORIGINS,
    FRONTEND_DIST,
    SECRET_KEY,
    SESSION_HTTPS_ONLY,
    SESSION_MAX_AGE_SECONDS,
)
from app.database import SessionLocal
from app.middleware import OriginGuardMiddleware, SecurityHeadersMiddleware
from app.migrations import upgrade_database
from app.models import Category, User
from app.routers import (
    accounts,
    admin,
    auth,
    budgets,
    dashboard,
    imports,
    recurring,
    transactions,
    transfers,
)
from app.security import hash_password

# 配置日志
logging.basicConfig(level=logging.INFO if APP_ENV == "development" else logging.WARNING)
logger = logging.getLogger(__name__)


# 默认收支分类（系统预置，第一版不允许用户自定义）
DEFAULT_CATEGORIES = [
    ("工资", "income"),
    ("理财收益", "income"),
    ("兼职", "income"),
    ("餐饮", "expense"),
    ("交通", "expense"),
    ("购物", "expense"),
    ("娱乐", "expense"),
    ("居住", "expense"),
    ("医疗", "expense"),
    ("教育", "expense"),
    ("其他", "expense"),
]


def init_database() -> None:
    """执行数据库迁移并初始化默认分类。"""
    upgrade_database()

    db = SessionLocal()
    try:
        existing = {c.name for c in db.query(Category).all()}
        for name, type_ in DEFAULT_CATEGORIES:
            if name not in existing:
                db.add(Category(name=name, type=type_))

        # 初始管理员只创建一次；已有账号不会被重复重置密码。
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            admin = db.query(User).filter(User.email == ADMIN_EMAIL).one_or_none()
            if admin is None:
                db.add(
                    User(
                        email=ADMIN_EMAIL,
                        password_hash=hash_password(ADMIN_PASSWORD),
                        is_admin=True,
                        is_active=True,
                    )
                )
            else:
                admin.is_admin = True
                admin.is_active = True
                if not admin.password_hash:
                    admin.password_hash = hash_password(ADMIN_PASSWORD)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库。"""
    init_database()
    logger.info("简账 SimpleLedger 启动完成，数据库已初始化")
    yield


app = FastAPI(title="简账 SimpleLedger", lifespan=lifespan)

# CORS 中间件：允许 Vue 开发服务器跨域请求，携带 Cookie（withCredentials）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session 中间件：HttpOnly + SameSite=Lax，生产环境自动开启 Secure
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="simple_ledger_session",
    same_site="lax",
    https_only=SESSION_HTTPS_ONLY,
    max_age=SESSION_MAX_AGE_SECONDS,
)

# 安全响应头与 API 写请求来源校验
app.add_middleware(OriginGuardMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Vue 生产构建目录：所有页面和前端资源都由这里提供。
app.mount(
    "/assets",
    StaticFiles(directory=str(FRONTEND_DIST / "assets"), check_dir=False),
    name="frontend-assets",
)

# 注册路由
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(recurring.router)
app.include_router(budgets.router)
app.include_router(imports.router)


@app.get("/health", name="health")
def health_check():
    """健康检查接口。"""
    return {"status": "ok"}


@app.get("/favicon.svg", include_in_schema=False)
def frontend_favicon():
    """返回 Vue 前端图标。"""
    favicon = FRONTEND_DIST / "favicon.svg"
    if not favicon.is_file():
        return FileResponse(FRONTEND_DIST / "index.html")
    return FileResponse(favicon)


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_app(full_path: str):
    """将非 API 路径交给 Vue Router 处理。"""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")

    index_path = FRONTEND_DIST / "index.html"
    if not index_path.is_file():
        return PlainTextResponse(
            "前端尚未构建，请先在 frontend 目录执行 npm run build。",
            status_code=503,
        )
    return FileResponse(index_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
