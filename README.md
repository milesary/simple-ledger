# 简账 SimpleLedger

简账是一个基于 FastAPI、Vue 3 和 MySQL 8 的个人记账 Web 应用，覆盖账户、流水、转账、周期记账、预算、统计、CSV 导入和管理员后台。

## 功能

- 邮箱密码登录、邮箱验证码登录和 Session Cookie 鉴权
- 多账户余额、账户归档和账户间转账
- 流水新增、筛选、分页、编辑、删除和 CSV 批量导入
- 月度预算、分类预算、年度趋势和分类支出统计
- 周期流水规则及到期自动生成
- 管理员账号查询、启停、角色管理、密码重置和删除
- Pytest 集成测试与 GitHub Actions 前后端 CI

## 技术栈

- 后端：FastAPI、SQLAlchemy 2、Pydantic 2、Alembic、MySQL 8
- 前端：Vue 3、Vue Router、Vite、Sass
- 测试与检查：Pytest、Ruff、GitHub Actions

## 本地运行

先创建 MySQL 数据库：

```sql
CREATE DATABASE simple_ledger
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

启动后端：

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动前端开发服务器：

```powershell
Set-Location frontend
npm install
npm run dev
```

默认地址：

- 前端开发服务器：`http://127.0.0.1:5173`
- FastAPI 应用及 Swagger：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

## 检查与测试

```powershell
Set-Location backend
python -m ruff check .
python -m pytest -q
```

```powershell
Set-Location frontend
npm run build
```

## 配置

环境变量示例位于 [`backend/.env.example`](backend/.env.example)。本地配置写入 `backend/.env`，该文件不会进入版本控制。

生产环境必须替换 `SECRET_KEY`、SMTP 授权码和管理员密码，开启 HTTPS，并通过环境变量配置数据库连接。

## 文档

- [前端说明](frontend/README.md)

## 主要限制

- CSV 导入确认 token 暂存在单进程内存中，多 worker 部署前需要迁移到 Redis 或数据库。
- CSV 文件当前会整体读入内存，超大文件需要改为流式处理或异步任务。
- 当前 Origin 校验不能替代完整 CSRF Token、WAF 或生产级安全防护。
