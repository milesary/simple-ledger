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
        <p class="eyebrow">创建账号</p>
        <h1>开始记录每一笔</h1>
        <p>仅支持 QQ 邮箱，密码需为 8-20 位并包含字母和数字。</p>
      </div>

      <form class="form-stack" @submit.prevent="register">
        <label class="field">
          <span>QQ 邮箱</span>
          <input
            v-model.trim="form.email"
            type="email"
            autocomplete="email"
            placeholder="QQ号@qq.com"
            required
          />
        </label>

        <label class="field">
          <span>设置密码</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            minlength="8"
            maxlength="20"
            placeholder="8-20 位，包含字母和数字"
            required
          />
        </label>

        <label class="field">
          <span>确认密码</span>
          <input
            v-model="form.confirmPassword"
            type="password"
            autocomplete="new-password"
            minlength="8"
            maxlength="20"
            placeholder="再次输入密码"
            required
          />
        </label>

        <p v-if="error" class="form-message form-message--error">{{ error }}</p>

        <button class="primary-button primary-button--wide" type="submit" :disabled="loading">
          <LoaderCircle v-if="loading" class="spin" :size="18" />
          {{ loading ? '注册中...' : '创建账号' }}
          <ArrowRight v-if="!loading" :size="18" />
        </button>
      </form>

      <p class="auth-switch">
        已经有账号？
        <RouterLink :to="{ name: 'login' }">返回登录</RouterLink>
      </p>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, LoaderCircle } from 'lucide-vue-next'
import { authApi } from '../api/auth'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const form = reactive({
  email: '',
  password: '',
  confirmPassword: '',
})

function validate() {
  if (!/^[^@\s]+@qq\.com$/i.test(form.email)) return '仅支持 QQ 邮箱（QQ号@qq.com）'
  if (form.password.length < 8 || form.password.length > 20) {
    return '密码长度必须为 8-20 位'
  }
  if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) {
    return '密码必须同时包含字母和数字'
  }
  if (form.password !== form.confirmPassword) return '两次输入的密码不一致'
  return ''
}

async function register() {
  error.value = validate()
  if (error.value) return

  loading.value = true
  try {
    const result = await authApi.register({
      email: form.email,
      password: form.password,
    })
    if (!result.success) throw new Error(result.message || '注册失败')
    router.replace({
      name: 'login',
      query: { email: form.email.toLowerCase(), registered: '1' },
    })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>
