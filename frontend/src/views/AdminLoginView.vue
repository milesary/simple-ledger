<template>
  <section class="admin-login-layout">
    <div class="admin-login-card">
      <div class="admin-login-brand">
        <span class="admin-login-brand__mark">
          <ShieldCheck :size="28" />
        </span>
        <div>
          <strong>简账管理后台</strong>
          <span>ADMIN CONSOLE</span>
        </div>
      </div>

      <div class="admin-login-heading">
        <p class="eyebrow">管理员入口</p>
        <h1>后台登录</h1>
        <p>此入口仅用于账号管理，不提供个人记账功能。</p>
      </div>

      <form class="form-stack" @submit.prevent="login">
        <label class="field">
          <span>管理员邮箱</span>
          <input
            v-model.trim="form.email"
            type="email"
            autocomplete="username"
            placeholder="管理员邮箱地址"
            required
          />
        </label>

        <label class="field">
          <span>密码</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            minlength="8"
            maxlength="20"
            placeholder="请输入管理员密码"
            required
          />
        </label>

        <p v-if="error" class="form-message form-message--error">{{ error }}</p>

        <button class="admin-login-button" type="submit" :disabled="loading">
          <LoaderCircle v-if="loading" class="spin" :size="18" />
          {{ loading ? '验证中...' : '进入管理后台' }}
          <ArrowRight v-if="!loading" :size="18" />
        </button>
      </form>

      <p class="admin-login-note">
        仅限已授予管理员权限的账号登录。
      </p>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, LoaderCircle, ShieldCheck } from 'lucide-vue-next'
import { authApi } from '../api/auth'
import { clearCurrentUser, setCurrentUser } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref(route.query.forbidden ? '当前账号没有管理员权限' : '')
const form = reactive({
  email: '',
  password: '',
})

async function login() {
  loading.value = true
  error.value = ''

  try {
    const result = await authApi.login(form)
    if (!result.success) throw new Error(result.message || '登录失败')

    if (!result.user?.is_admin) {
      await authApi.logout().catch(() => null)
      clearCurrentUser()
      throw new Error('该账号没有管理员权限')
    }

    setCurrentUser(result.user)
    const redirect =
      typeof route.query.redirect === 'string' &&
      route.query.redirect.startsWith('/admin')
        ? route.query.redirect
        : { name: 'admin' }
    router.replace(redirect)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>
