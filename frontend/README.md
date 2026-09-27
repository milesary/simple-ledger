# 简账 Vue 3 前端

基于 Vue 3、Vue Router 和 Vite 的简账业务前端，通过 Session Cookie 调用 FastAPI `/api` JSON 接口。

已覆盖：

- 密码登录、邮箱验证码登录和注册。
- 概览指标、年度趋势、支出分类和最近流水。
- 流水筛选、分页、新增、编辑和删除。
- 月度预算设置和历史执行情况。
- CSV 上传预览、重复检测和确认导入。
- 管理员账号查询、启停、角色切换、密码重置和删除。

## 运行

```bash
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173`。

该地址是个人用户入口，根路径会先跳转到用户登录页。

默认将 `/api` 代理到 `http://127.0.0.1:8000`。后端使用其他端口时：

```powershell
$env:VITE_BACKEND_TARGET = "http://127.0.0.1:8000"
npm run dev
```

## 构建

```bash
npm run build
npm run preview
```

生产构建会自动输出到 `frontend/dist`。FastAPI 的根路径进入独立管理员登录页 `/admin/login`，管理员登录后访问 `/admin`；普通用户路由不会作为后端地址的默认页面。
