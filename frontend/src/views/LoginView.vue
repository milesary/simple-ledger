<template>
  <section class="auth-layout">
    <div class="auth-card">
      <div class="auth-brand">
        <span class="auth-brand__mark">账</span>
        <div>
          <strong>简账</strong>
          <span>SimpleLedger</span>
        </div>
      </div>

      <div class="auth-heading">
        <p class="eyebrow">个人收支管理</p>
        <h1>欢迎回来</h1>
        <p>这是个人用户入口，请使用密码或 QQ 邮箱验证码登录。</p>
      </div>

      <div class="segmented-control" role="tablist">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          type="button"
          :class="{ active: activeMode === tab.value }"
          @click="activeMode = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>

      <form v-if="activeMode === 'password'" class="form-stack" @submit.prevent="login">
        <label class="field">
          <span>QQ 邮箱</span>
          <input
            v-model.trim="loginForm.email"
            type="email"
            autocomplete="email"
            placeholder="QQ号@qq.com"
            required
          />
        </label>

        <label class="field">
          <span>密码</span>
          <input
            v-model="loginForm.password"
            type="password"
            autocomplete="current-password"
            minlength="8"
            maxlength="20"
            placeholder="请输入密码"
            required
          />
        </label>

        <p v-if="error" class="form-message form-message--error">{{ error }}</p>
        <p v-if="successMessage" class="form-message form-message--success">
          {{ successMessage }}
        </p>

        <button class="primary-button primary-button--wide" type="submit" :disabled="loading">
          <LoaderCircle v-if="loading" class="spin" :size="18" />
          {{ loading ? '登录中...' : '登录' }}
          <ArrowRight v-if="!loading" :size="18" />
        </button>
      </form>

      <form v-else class="form-stack" @submit.prevent="sendCode">
        <label class="field">
          <span>QQ 邮箱</span>
          <input
            v-model.trim="codeEmail"
            type="email"
            autocomplete="email"
            placeholder="QQ号@qq.com"
            required
          />
          <small>验证码登录仅对已经注册的账号开放。</small>
        </label>

        <p v-if="error" class="form-message form-message--error">{{ error }}</p>

        <button class="primary-button primary-button--wide" type="submit" :disabled="loading">
          <LoaderCircle v-if="loading" class="spin" :size="18" />
          {{ loading ? '发送中...' : '发送验证码' }}
          <Mail v-if="!loading" :size="18" />
        </button>
      </form>

      <p class="auth-switch">
        还没有账号？
        <RouterLink :to="{ name: 'register' }">立即注册</RouterLink>
      </p>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowRight, LoaderCircle, Mail } from 'lucide-vue-next'
import { authApi } from '../api/auth'
import { setCurrentUser } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const activeMode = ref('password')
const loading = ref(false)
const error = ref('')
const successMessage = ref('')
const codeEmail = ref('')

const loginForm = reactive({
  email: '',
  password: '',
})

const tabs = [
  { value: 'password', label: '密码登录' },
  { value: 'code', label: '验证码登录' },
]

watch(
  () => route.query,
  (query) => {
    if (query.email) {
      loginForm.email = String(query.email)
      codeEmail.value = String(query.email)
    }
    if (query.registered) {
      successMessage.value = '注册成功，请使用新账号登录。'
    }
  },
  { immediate: true },
)

async function login() {
  error.value = ''
  successMessage.value = ''
  loading.value = true
  try {
    const result = await authApi.login(loginForm)
    if (!result.success) throw new Error(result.message || '登录失败')
    setCurrentUser(result.user)
    router.replace(
      route.query.redirect
        ? String(route.query.redirect)
        : { name: 'dashboard' },
    )
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function sendCode() {
  error.value = ''
  successMessage.value = ''
  loading.value = true
  try {
    const result = await authApi.sendCode({ email: codeEmail.value })
    if (!result.success) throw new Error(result.message || '验证码发送失败')
    sessionStorage.setItem('simple_ledger_pending_email', codeEmail.value.toLowerCase())
    router.push({
      name: 'verify',
      query: route.query.redirect ? { redirect: route.query.redirect } : {},
    })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>
