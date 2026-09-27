import { createRouter, createWebHistory } from 'vue-router'
import { initializeAuth, useAuth } from '../composables/useAuth'

// Vite 开发入口用于个人用户；FastAPI 托管的构建入口用于管理员后台。
const isBackendSurface = !import.meta.env.DEV

const routes = [
  {
    path: '/',
    name: 'root',
    redirect: () =>
      isBackendSurface
        ? { name: 'admin' }
        : { name: 'login', query: { entry: 'frontend' } },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { guestOnly: true, title: '登录' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/RegisterView.vue'),
    meta: { guestOnly: true, title: '注册' },
  },
  {
    path: '/login/verify',
    name: 'verify',
    component: () => import('../views/VerifyView.vue'),
    meta: { guestOnly: true, title: '验证邮箱' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requireAuth: true, title: '概览' },
  },
  {
    path: '/transactions',
    name: 'transactions',
    component: () => import('../views/TransactionsView.vue'),
    meta: { requireAuth: true, title: '流水' },
  },
  {
    path: '/transactions/new',
    name: 'transaction-new',
    component: () => import('../views/TransactionFormView.vue'),
    meta: { requireAuth: true, title: '新增流水' },
  },
  {
    path: '/transactions/:id/edit',
    name: 'transaction-edit',
    component: () => import('../views/TransactionFormView.vue'),
    meta: { requireAuth: true, title: '编辑流水' },
  },
  {
    path: '/budgets',
    name: 'budgets',
    component: () => import('../views/BudgetsView.vue'),
    meta: { requireAuth: true, title: '预算' },
  },
  {
    path: '/accounts',
    name: 'accounts',
    component: () => import('../views/AccountsView.vue'),
    meta: { requireAuth: true, title: '账户' },
  },
  {
    path: '/transfers',
    name: 'transfers',
    component: () => import('../views/TransfersView.vue'),
    meta: { requireAuth: true, title: '转账' },
  },
  {
    path: '/recurring',
    name: 'recurring',
    component: () => import('../views/RecurringView.vue'),
    meta: { requireAuth: true, title: '周期流水' },
  },
  {
    path: '/imports',
    name: 'imports',
    component: () => import('../views/ImportsView.vue'),
    meta: { requireAuth: true, title: 'CSV 导入' },
  },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('../views/AdminLoginView.vue'),
    meta: { adminArea: true, adminGuestOnly: true, title: '后台登录' },
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/AdminView.vue'),
    meta: { adminArea: true, adminOnly: true, title: '后台管理' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const { user } = useAuth()
  await initializeAuth()

  if (to.meta.adminArea && !isBackendSurface) {
    return {
      name: 'login',
      query: { entry: 'frontend' },
    }
  }

  if (to.meta.adminOnly) {
    if (!user.value) {
      return {
        name: 'admin-login',
        query: { redirect: to.fullPath },
      }
    }
    if (!user.value.is_admin) {
      return {
        name: 'admin-login',
        query: { forbidden: '1' },
      }
    }
  }

  if (to.meta.adminGuestOnly && user.value?.is_admin) {
    return { name: 'admin' }
  }

  if (to.meta.requireAuth && !user.value) {
    return {
      name: 'login',
      query: to.fullPath === '/' ? {} : { redirect: to.fullPath },
    }
  }

  if (to.meta.guestOnly && user.value && to.query.entry !== 'frontend') {
    return { name: 'dashboard' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · 简账`
    : '简账 SimpleLedger'
})

export default router
