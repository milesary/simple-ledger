# 简账 SimpleLedger 开发文档

> 文档版本：1.1  
> 更新时间：2026-09-26  
> 说明：本文档已按当前代码实现修订。接口字段、状态码和联调示例详见 [接口文档.md](./接口文档.md)。

## 1. 项目概述

简账是一个面向个人用户的记账 Web 应用。前端统一使用 Vue 3 单页应用，FastAPI 仅提供 JSON API、静态资源和 SPA 路由回退：

1. Vue 3 前端负责登录、注册、验证码、概览、流水、账户、转账、周期流水、预算、导入和管理员后台。
2. FastAPI JSON API 统一位于 `/api` 下，通过 Session Cookie 鉴权。

项目当前以功能闭环和简历展示为目标，强调：

- 登录与用户数据隔离。
- 流水增删改查、筛选和分页。
- 多账户、实时余额与账户间转账。
- 周期流水规则和到期自动生成。
- 月度统计、趋势、分类占比和预算使用率。
- 总预算和分类预算。
- CSV 预览、重复检测和批量导入。
- 管理员账号查询、启停、角色管理、密码重置和删除。
- 可执行的 Pytest 集成测试。

项目按前后端拆分为 `frontend/` 和 `backend/` 两个目录。`frontend/` 使用 Vue 3、Vue Router 和 Vite，生产构建产物写入 `frontend/dist/`；`backend/` 提供 FastAPI JSON API，并在运行时读取该构建产物。旧 Jinja 页面路由已移除。

## 2. 当前功能范围

| 模块 | 当前状态 |
| --- | --- |
| 账号注册 | 已实现，邮箱密码注册 |
| 密码登录 | 已实现，Session Cookie 登录态 |
| 邮箱验证码登录 | 已实现，需先注册账号 |
| 退出登录 | 已实现 |
| 管理员后台 | 已实现 Vue 页面和 JSON API |
| 流水管理 | 已实现 Vue 页面和 JSON API |
| 流水筛选分页 | 已实现 |
| 账户体系 | 已实现，支持余额聚合和归档 |
| 账户转账 | 已实现，不计入收支统计 |
| 周期流水 | 已实现，打开概览或周期页时补齐到期流水 |
| 预算管理 | 已实现 Vue 页面和 JSON API |
| 分类预算 | 已实现，按支出分类设置月度额度 |
| Dashboard 统计 | 已实现 Vue 页面和 JSON API |
| 年度趋势和分类占比 | 已实现 |
| CSV 导入模板 | 已实现 |
| CSV 预览和重复检测 | 已实现 |
| CSV 确认导入 | 已实现，待确认数据暂存在进程内存 |
| Vue 业务前端 | 已实现，覆盖认证、概览、流水、账户、转账、周期、预算、CSV 导入和管理员后台 |
| 统一 API 响应包装 | 未实现 |
| Alembic 数据库迁移 | 已实现，启动时自动升级到最新版本 |

## 3. 技术栈

| 模块 | 技术 |
| --- | --- |
| Web 框架 | FastAPI 0.136.3 |
| ASGI 服务 | Uvicorn 0.48.0 |
| 页面框架 | Vue 3.5 + Vue Router 4 |
| 页面样式与图表 | Sass、CSS 响应式布局、原生 SVG |
| ORM | SQLAlchemy 2.0.41 |
| 数据库 | MySQL 8 |
| 数据校验 | Pydantic 2 |
| 登录状态 | Starlette SessionMiddleware，签名 Cookie |
| 密码哈希 | PBKDF2-HMAC-SHA256，随机盐，310000 次迭代 |
| 验证码哈希 | HMAC-SHA256 |
| 邮件发送 | aiosmtplib |
| 测试 | Pytest、FastAPI TestClient |
| 业务前端 | Vue 3.5、Vue Router 4、Vite 6、Sass、lucide-vue-next |
| 数据库迁移 | Alembic 1.20 |
| 代码检查 | Ruff |
| Python 包管理 | pip + `backend/requirements.txt` |
| 前端包管理 | npm + package-lock.json |

当前没有使用 PostgreSQL、Redis、Celery、Docker、React 或前端状态管理框架。

## 4. 开发架构

```text
浏览器或前端应用
  -> FastAPI Router
  -> Service 业务层
  -> SQLAlchemy ORM
  -> MySQL

认证流程额外经过：
AuthService
  -> MailService
  -> QQ 邮箱 SMTP
```

职责划分：

| 层 | 目录 | 职责 |
| --- | --- | --- |
| 应用入口 | `backend/app/main.py` | 创建 FastAPI、注册中间件和路由、初始化数据库 |
| 配置 | `backend/app/config.py` | 从环境变量读取运行配置 |
| 数据库 | `backend/app/database.py` | Engine、Session、Base 和数据库依赖 |
| 模型 | `backend/app/models.py` | 用户、账户、转账、周期规则、流水和预算表 |
| 校验模型 | `backend/app/schemas.py` | 账户、转账、周期、流水和预算校验 |
| JSON 路由 | `backend/app/routers/` | API 请求处理、鉴权和响应序列化 |
| 服务层 | `backend/app/services/` | 认证、账户、转账、周期、流水、统计和导入业务逻辑 |
| 管理后台 API | `backend/app/routers/admin.py` | 管理员账号查询与管理接口 |
| 前端构建产物 | `frontend/dist/` | Vue 页面、JavaScript、CSS 和 favicon |
| 业务前端 | `frontend/` | Vue 3 单页应用，统一调用 `/api` JSON 接口 |

## 5. 目录结构

```text
project03/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── routers/
│   │   └── services/
│   ├── migrations/
│   ├── scripts/
│   │   └── migrate_sqlite_to_mysql.py
│   ├── tests/
│   ├── .env.example
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── dist/                  # Vue 生产构建产物
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docs/
├── .github/
├── DEVELOPMENT.md
└── 接口文档.md
```

## 6. 本地开发

### 6.1 MySQL 准备

应用不会自动创建 MySQL 数据库，首次运行前需要先创建数据库：

```sql
CREATE DATABASE simple_ledger
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

然后在 `backend/.env` 中配置连接：

```text
DATABASE_URL=mysql+pymysql://用户名:密码@127.0.0.1:3306/simple_ledger?charset=utf8mb4
```

### 6.2 后端启动

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

也可以直接运行：

```powershell
python -m app.main
```

默认访问地址：

```text
应用页面: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
健康检查: http://127.0.0.1:8000/health
```

首次启动会：

1. 执行 `alembic upgrade head`，创建或升级数据库结构。
2. 初始化系统分类。
3. 如果配置了 `ADMIN_EMAIL` 和 `ADMIN_PASSWORD`，创建或补齐初始管理员。

手动执行迁移：

```powershell
python -m alembic upgrade head
```

### 6.3 Vue 业务前端启动

```powershell
Set-Location frontend
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5173
```

Vite 当前代理后端到：

```text
http://127.0.0.1:8000
```

如果后端使用其他端口，可以覆盖代理目标：

```powershell
$env:VITE_BACKEND_TARGET = "http://127.0.0.1:8000"
npm run dev
```

Vue 页面通过 `credentials: include` 携带 `simple_ledger_session` Cookie。登录、注册、验证码、流水、预算、统计和导入请求均封装在 `frontend/src/api/` 下。

## 7. 环境变量

环境变量示例位于 `backend/.env.example`，本地配置写入 `backend/.env`。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_ENV` | `development` | 日志级别和应用环境 |
| `SECRET_KEY` | `dev-secret-change-in-prod` | Session 和验证码签名密钥 |
| `DATABASE_URL` | MySQL `simple_ledger` 连接串 | 数据库连接 |
| `CORS_ORIGINS` | 两个本地 5173 地址 | 允许携带 Session Cookie 的浏览器来源 |
| `ALLOWED_EMAIL_DOMAINS` | `qq.com` | 允许注册和登录的邮箱域名，逗号分隔 |
| `CODE_EXPIRE_MINUTES` | `5` | 验证码有效期 |
| `CODE_SEND_INTERVAL_SECONDS` | `60` | 验证码发送最小间隔 |
| `CODE_MAX_ATTEMPTS` | `5` | 单个验证码最大错误次数 |
| `CODE_SEND_MAX_PER_HOUR` | `5` | 同一邮箱每小时发送上限 |
| `MAIL_HOST` | `smtp.qq.com` | SMTP 地址 |
| `MAIL_PORT` | `465` | SMTP 端口 |
| `MAIL_USERNAME` | 空 | SMTP 登录账号 |
| `MAIL_PASSWORD` | 空 | SMTP 授权码，不是 QQ 密码 |
| `MAIL_FROM` | 空 | 发件地址 |
| `MAIL_USE_TLS` | `true` | 是否使用 TLS |
| `MAIL_DEV_MODE` | `true` | 为 `true` 时验证码打印到日志 |
| `SESSION_HTTPS_ONLY` | 生产环境为 `true` | Session Cookie 是否只通过 HTTPS 发送 |
| `SESSION_MAX_AGE_SECONDS` | `1209600` | Session Cookie 有效期 |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` | CSV 服务端上传大小上限 |
| `PAGE_SIZE` | `20` | 流水分页大小 |
| `ADMIN_EMAIL` | 空 | 初始管理员邮箱 |
| `ADMIN_PASSWORD` | 空 | 初始管理员密码 |

生产环境必须替换 `SECRET_KEY`、SMTP 授权码和管理员密码，且不能提交 `.env`。
当 `APP_ENV=production` 时，默认密钥、短密钥或 `MAIL_DEV_MODE=true` 会直接阻止应用启动。

## 8. 数据模型

### 8.1 users

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| id | Integer | 主键 |
| email | String(254) | 唯一、非空、索引、小写标准化 |
| password_hash | String(255) | 可空，PBKDF2 哈希 |
| is_admin | Boolean | 非空，默认 `false` |
| is_active | Boolean | 非空，默认 `true` |
| created_at | DateTime | 非空，数据库默认当前时间 |
| last_login_at | DateTime | 可空 |

### 8.2 login_codes

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| id | Integer | 主键 |
| email | String(254) | 非空、索引 |
| code_hash | String(64) | 非空，HMAC-SHA256 |
| expires_at | DateTime | 非空 |
| attempts | Integer | 非空，默认 0 |
| consumed_at | DateTime | 可空 |
| created_at | DateTime | 非空 |

组合索引：

```text
email + created_at
```

### 8.3 categories

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| id | Integer | 主键 |
| name | String(50) | 非空 |
| type | String(10) | `income` 或 `expense` |

默认分类：

```text
income: 工资、理财收益、兼职
expense: 餐饮、交通、购物、娱乐、居住、医疗、教育、其他
```

### 8.4 transactions

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| id | Integer | 主键 |
| user_id | Integer | 外键，非空 |
| account_id | Integer | 账户外键，可空 |
| type | String(10) | `income` 或 `expense` |
| amount | Numeric(10, 2) | 非空，大于 0 |
| category_id | Integer | 外键，非空 |
| occurred_on | Date | 非空 |
| payment_method | String(20) | 可空 |
| note | String(200) | 可空 |
| import_hash | String(64) | 可空 |
| created_at | DateTime | 非空 |
| updated_at | DateTime | 非空 |

索引：

```text
user_id + occurred_on
user_id + category_id
user_id + type
user_id + import_hash
user_id + account_id
```

### 8.5 budgets

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| id | Integer | 主键 |
| user_id | Integer | 外键，非空 |
| category_id | Integer | 分类外键，可空；为空表示总预算 |
| month | String(7) | `YYYY-MM` |
| amount | Numeric(10, 2) | 非空，大于 0 |
| created_at | DateTime | 非空 |
| updated_at | DateTime | 非空 |

唯一约束：

```text
总预算：user_id + month，且 category_id 为空
分类预算：user_id + month + category_id
```

### 8.6 accounts

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| id | Integer | 主键 |
| user_id | Integer | 外键，非空 |
| name | String(50) | 同一用户下唯一 |
| type | String(20) | cash / bank / credit / investment / other |
| initial_balance | Numeric(12, 2) | 初始余额 |
| is_archived | Boolean | 归档后保留历史数据 |

账户余额 = 初始余额 + 收入 - 支出 + 转入 - 转出。

### 8.7 transfers

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| id | Integer | 主键 |
| user_id | Integer | 外键，非空 |
| from_account_id | Integer | 转出账户，不能与转入账户相同 |
| to_account_id | Integer | 转入账户 |
| amount | Numeric(12, 2) | 必须大于 0 |
| occurred_on | Date | 非空 |
| note | String(200) | 可空 |

### 8.8 recurring_transactions

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| id | Integer | 主键 |
| user_id | Integer | 外键，非空 |
| type | String(10) | income / expense |
| amount | Numeric(10, 2) | 必须大于 0 |
| category_id | Integer | 分类外键 |
| account_id | Integer | 账户外键，可空 |
| frequency | String(10) | daily / weekly / monthly / yearly |
| interval | Integer | 间隔，最小为 1 |
| start_date | Date | 首次执行日期 |
| next_run_date | Date | 下一执行日期 |
| end_date | Date | 可空 |
| is_active | Boolean | 是否启用 |

## 9. 账号与权限

### 9.1 注册

- 默认只允许 `qq.com` 邮箱。
- 邮箱去空格并转小写。
- 密码长度 8-20 位。
- 密码必须同时包含字母和数字。
- 同一邮箱只能注册一次。
- 注册后不自动登录。

### 9.2 登录

支持两类登录：

1. 邮箱密码登录。
2. 邮箱验证码登录。

两类登录成功后都会：

```python
request.session.clear()
request.session["user_id"] = user.id
```

Session Cookie 当前配置：

```text
名称: simple_ledger_session
HttpOnly: true
SameSite: Lax
Secure: 开发环境 false，生产环境 true
有效期: 默认 14 天
```

### 9.3 验证码登录

- 只允许已注册且启用的账号获取验证码。
- 新验证码生成后，旧验证码立即失效。
- 验证码只保存 HMAC-SHA256 哈希。
- 5 分钟内有效。
- 60 秒内不能重复发送。
- 1 小时内最多发送 5 次。
- 单个验证码最多尝试 5 次。
- 验证成功后立即标记为已消费。
- `MAIL_DEV_MODE=true` 时验证码写入日志，不发送真实邮件。

### 9.4 数据隔离

- 所有业务 API 通过 `require_user` 从 Session 获取用户。
- 流水查询、编辑和删除均校验 `user_id`。
- 统计和预算查询均附带 `user_id`。
- 客户端不能通过请求体指定操作对象所属用户。

### 9.5 管理员

管理员后台使用独立入口。开发服务器地址 `http://127.0.0.1:5173/` 只进入个人用户登录页；FastAPI 地址 `http://127.0.0.1:8000/` 的根路径进入 `/admin/login`，普通用户 Session 不会被视为后台登录。管理员登录后进入 `/admin`，所有数据操作调用 `/api/admin/*`，要求当前 Session 用户满足 `is_admin=true`。

支持：

- 按邮箱或 ID 查询账号。
- 启用或禁用账号。
- 授予或取消管理员角色。
- 重置账号密码。
- 删除普通账号及其关联业务数据。

保护规则：

- 不能禁用自己。
- 不能修改自己的管理员角色。
- 不能删除自己。
- 不能直接删除管理员账号，需要先取消管理员权限。
- 系统必须保留至少一个可用管理员。
- 删除普通账号会同时清理流水、账户、转账、周期规则、预算和该邮箱的登录验证码。

## 10. 后端路由

### 10.1 JSON API

JSON API 的完整字段、示例、状态码和联调注意事项见 [接口文档.md](./接口文档.md)。

| 模块 | 主要路由 |
| --- | --- |
| 认证 | `/api/auth/register`、`/api/auth/login`、`/api/auth/code`、`/api/auth/verify`、`/api/auth/logout`、`/api/auth/me` |
| Dashboard | `/api/dashboard` |
| 统计 | `/api/stats/monthly`、`/api/stats/categories` |
| 分类 | `/api/categories` |
| 流水 | `/api/transactions`、`/api/transactions/{id}` |
| 账户 | `/api/accounts`、`/api/accounts/{id}`、`/api/accounts/{id}/archive` |
| 转账 | `/api/transfers`、`/api/transfers/{id}` |
| 周期流水 | `/api/recurring`、`/api/recurring/{id}`、`/api/recurring/{id}/toggle` |
| 预算 | `/api/budgets`、`/api/budgets/categories` |
| 导入 | `/api/imports/preview`、`/api/imports/confirm`、`/api/imports/template` |
| 管理员 | `/api/admin/users`、`/api/admin/users/{id}/toggle`、`/api/admin/users/{id}/role`、`/api/admin/users/{id}/reset-password`、`/api/admin/users/{id}` |
| 健康检查 | `/health` |

### 10.2 Vue SPA 路由

以下页面路径均由 Vue Router 处理。FastAPI 对非 `/api`、非静态资源路径返回 `frontend/dist/index.html`：

| 页面 | 路由 |
| --- | --- |
| 用户入口 | `/`，Vite 开发入口跳转 `/login?entry=frontend` |
| 登录 | `/login` |
| 注册 | `/register` |
| 验证码 | `/login/verify` |
| Dashboard | `/dashboard` |
| 流水列表 | `/transactions` |
| 账户 | `/accounts` |
| 转账 | `/transfers` |
| 周期流水 | `/recurring` |
| 新增流水 | `/transactions/new` |
| 编辑流水 | `/transactions/{id}/edit` |
| 预算 | `/budgets` |
| 导入 | `/imports` |
| 管理员登录 | `/admin/login` |
| 管理后台 | `/admin` |

HTML 路由只负责返回 Vue 入口，不执行服务端登录跳转。页面入口和登录守卫由 Vue Router 完成，最终数据权限仍由 `/api` 的 Session 校验决定。Vite 开发地址不能被当作管理员入口，管理员入口使用 FastAPI 托管的生产构建地址。

### 10.3 API 响应现状

当前没有统一响应包装。实际响应包括：

```json
{"success": true, "message": "..."}
```

```json
{"detail": "..."}
```

以及直接返回业务对象的响应。认证接口的业务失败仍返回 HTTP `200`，前端必须检查 `success` 字段。

## 11. 业务规则

### 11.1 流水

- 金额必须大于 0。
- 金额以 `Decimal` 接收，数据库使用 `Numeric(10, 2)`。
- 收入只能选择收入分类。
- 支出只能选择支出分类。
- 编辑和删除必须校验流水归属。
- 更新接口使用 PUT，但实际支持只提交部分字段。
- 列表按日期和 ID 倒序。
- `q` 只搜索备注，不搜索支付方式或分类名称。

### 11.2 统计

- 月度收入为当月收入合计。
- 月度支出为当月支出合计。
- 月结余为收入减支出。
- 趋势固定返回 1-12 月。
- 分类统计只包含支出。
- 预算使用率为 `当月支出 / 月预算 * 100`。
- 预算剩余为 `月预算 - 当月支出`，可以为负数。
- 没有预算时预算对象为 `null`。

### 11.3 CSV 导入

固定表头：

```text
date,type,amount,category,payment_method,note
```

处理规则：

1. 解码 UTF-8 或 UTF-8 BOM。
2. 校验必要表头。
3. 标准化日期、类型、金额、分类、支付方式和备注。
4. 计算 SHA-256 `import_hash`。
5. 检测文件内部重复和当前用户数据库重复。
6. 预览返回成功、重复和错误数量。
7. 使用内存 token 暂存可导入行。
8. 用户确认后批量写入数据库。

重要现状：

- 错误行不会导致整批导入失败。
- 确认导入只写入 `success` 行。
- 重复行默认跳过。
- 重复检测只适用于带 `import_hash` 的 CSV 导入数据。
- token 存在单进程内存中，服务重启或多 worker 部署后不可用。

## 12. 核心服务

### 12.1 AuthService

```python
register(email: str, password: str) -> User
login_with_password(email: str, password: str) -> User
request_login_code(email: str) -> None
verify_login_code(email: str, code: str) -> User
get_current_user(user_id: int) -> Optional[User]
```

### 12.2 MailService

```python
send_login_code(email: str, code: str) -> None
```

### 12.3 TransactionService

```python
create_transaction(user_id: int, data: TransactionCreate) -> Transaction
get_transaction(user_id: int, transaction_id: int) -> Optional[Transaction]
update_transaction(user_id: int, transaction_id: int, data: TransactionUpdate) -> Transaction
delete_transaction(user_id: int, transaction_id: int) -> None
list_transactions(...) -> tuple[list[Transaction], int]
```

### 12.4 StatsService

```python
get_monthly_summary(user_id: int, month: str) -> dict
get_monthly_trend(user_id: int, year: int) -> list[dict]
get_category_summary(user_id: int, month: str) -> list[dict]
get_month_expense(user_id: int, month: str) -> Decimal
get_budget(user_id: int, month: str) -> Optional[dict]
set_budget(user_id: int, month: str, amount: Decimal) -> Budget
list_budgets(user_id: int) -> list[dict]
```

### 12.5 ImportService

```python
preview_import(user_id: int, content: bytes) -> dict
confirm_import(user_id: int, token: str) -> dict
```

### 12.6 AccountService

```python
create_account(user_id: int, data: AccountCreate) -> Account
update_account(user_id: int, account_id: int, data: AccountUpdate) -> Account
archive_account(user_id: int, account_id: int) -> Account
list_accounts(user_id: int) -> list[dict]
```

### 12.7 TransferService

```python
create_transfer(user_id: int, data: TransferCreate) -> Transfer
update_transfer(user_id: int, transfer_id: int, data: TransferUpdate) -> Transfer
delete_transfer(user_id: int, transfer_id: int) -> None
list_transfers(user_id: int) -> list[dict]
```

### 12.8 RecurringTransactionService

```python
create_rule(user_id: int, data: RecurringCreate) -> RecurringTransaction
update_rule(user_id: int, rule_id: int, data: RecurringUpdate) -> RecurringTransaction
delete_rule(user_id: int, rule_id: int) -> None
materialize_due(user_id: int, through: date | None = None) -> int
list_rules(user_id: int) -> list[dict]
```

## 13. 测试

运行测试：

```powershell
Set-Location backend
python -m ruff check .
python -m pytest -q
```

当前测试覆盖：

- Vue SPA 根路径和嵌套路由可访问。
- 未登录访问受保护 API 返回 `401`。
- 非允许邮箱域名被拒绝。
- 注册、重复注册、错误密码和正确密码登录。
- 验证码发送和验证码登录。
- 当前用户、分类、流水和预算接口。
- 管理员账号查询、启停、角色切换和密码重置。
- 生产环境拒绝默认密钥和开发邮件模式。
- 安全响应头、跨站写请求拦截和 Origin 校验。
- Alembic 在空数据库上创建完整表结构。
- 统计结果、年度趋势查询次数和历史预算固定查询数。
- 账户余额、转账、周期流水生成和分类预算完整 API 流程。

## 14. 已知问题与后续计划

### 14.1 必须优先处理

1. 导入 token 仍存储在进程内存中，多 worker 部署会随机失效。
2. Origin 校验不能替代 WAF 和完整 CSRF Token；高安全场景应继续增加显式 Token。
3. CSV 文件仍会整体读入内存，超大文件需要改成流式或异步任务。

### 14.2 接口规范化

1. 决定是否引入统一的 `{code, msg, data}` 响应结构。
2. 认证业务失败改为合适的 HTTP 状态码，而不是统一返回 `200`。
3. 为金额、月份、收支类型和分页补充统一参数校验。
4. 为接口增加明确的响应模型，提升 OpenAPI 文档质量。
5. 统一“资源不存在”和“无权限访问”的状态码。

### 14.3 工程化

1. 拆分 API 测试、服务测试和管理员测试。
2. 将导入 token 迁移到 Redis 或数据库临时表。
3. 增加日志脱敏、请求 ID 和异常追踪。
4. 增加前端 ESLint 和组件测试。

### 14.4 文档整理

`docs/frontend/` 已清理为当前 Vue 业务前端的目录、请求和开发约定。

## 15. 部署注意事项

- 使用随机且足够长的 `SECRET_KEY`。
- 使用生产环境管理员密码和 SMTP 授权码。
- 确认生产环境 `APP_ENV=production`，使 Session Cookie 自动启用 `Secure`。
- 使用 HTTPS。
- MySQL 数据库使用持久化磁盘，并确保 `utf8mb4` 字符集。
- 定期备份 MySQL 数据库。
- 不提交 `.env`。
- 日志中不得输出密码、验证码、SMTP 授权码或 Session 内容。
- 如果使用多个 worker，必须先把导入 token 改为共享存储。
- 使用 Nginx 或 Caddy 时，确认 `/api`、静态资源和页面路由转发规则一致。

## 16. 当前验收标准

当前代码应满足：

- 可以注册 QQ 邮箱账号并使用密码或验证码登录。
- 禁用账号不能登录。
- 登录用户只能访问自己的流水、预算和统计数据。
- 可以新增、查询、更新、删除和筛选流水。
- 可以查看月度汇总、年度趋势、分类占比和预算使用率。
- 可以上传 CSV、查看预览并确认导入有效行。
- 管理员可以查询、启停、授权和重置账号。
- `python -m pytest -q` 通过。
- `.env`、QQ 邮箱授权码、管理员密码和真实 Session 密钥不进入版本控制。

## 17. 简历描述

> 开发基于 FastAPI、SQLAlchemy 和 MySQL 8 的个人记账 Web 应用，提供密码登录、邮箱验证码登录、Session 鉴权、流水管理、预算统计和 CSV 导入能力。

> 设计 HMAC-SHA256 验证码哈希、过期时间、发送频率和错误次数限制，避免验证码明文存储和重复使用。

> 为流水、预算和统计查询增加用户级数据隔离，并使用 Pytest 覆盖注册登录、页面保护、流水写入和管理员访问等核心流程。
