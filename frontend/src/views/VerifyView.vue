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
        <p class="eyebrow">邮箱验证</p>
        <h1>输入验证码</h1>
        <p>
          验证码已发送至 <strong>{{ email }}</strong>，5 分钟内有效。
        </p>
      </div>

      <form class="form-stack" @submit.prevent="verify">
        <div class="code-inputs">
          <input
            v-for="(_, index) in code"
            :key="index"
            :ref="(element) => setCodeRef(element, index)"
            v-model="code[index]"
            type="text"
            inputmode="numeric"
            maxlength="1"
            pattern="[0-9]"
            :aria-label="`验证码第 ${index + 1} 位`"
            @input="onInput(index, $event)"
            @keydown.delete="onBackspace(index, $event)"
            @paste="onPaste($event)"
          />
        </div>

        <p v-if="error" class="form-message form-message--error">{{ error }}</p>

        <button class="primary-button primary-button--wide" type="submit" :disabled="loading">
          <LoaderCircle v-if="loading" class="spin" :size="18" />
          {{ loading ? '验证中...' : '验证并登录' }}
          <ArrowRight v-if="!loading" :size="18" />
        </button>
      </form>

      <div class="auth-links">
        <button type="button" @click="goBack">换个邮箱</button>
        <span>·</span>
        <button type="button" :disabled="countdown > 0 || resending" @click="resend">
          {{ countdown > 0 ? `${countdown} 秒后重发` : '重新发送' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, LoaderCircle } from 'lucide-vue-next'
import { authApi } from '../api/auth'
import { setCurrentUser } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const email = ref(sessionStorage.getItem('simple_ledger_pending_email') || '')
const code = ref(['', '', '', '', '', ''])
const inputs = ref([])
const loading = ref(false)
const resending = ref(false)
const error = ref('')
const countdown = ref(60)
let timer = null

function setCodeRef(element, index) {
  if (element) inputs.value[index] = element
}

function startCountdown() {
  countdown.value = 60
  clearInterval(timer)
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) clearInterval(timer)
  }, 1000)
}

function onInput(index, event) {
  const value = event.target.value.replace(/\D/g, '').slice(-1)
  code.value[index] = value
  event.target.value = value
  if (value && index < inputs.value.length - 1) inputs.value[index + 1]?.focus()
}

function onBackspace(index, event) {
  if (!code.value[index] && index > 0) {
    event.preventDefault()
    inputs.value[index - 1]?.focus()
  }
}

function onPaste(event) {
  event.preventDefault()
  const value = (event.clipboardData?.getData('text') || '')
    .replace(/\D/g, '')
    .slice(0, 6)
  value.split('').forEach((char, index) => {
    code.value[index] = char
  })
  inputs.value[Math.min(value.length, 5)]?.focus()
}

function goBack() {
  router.replace({ name: 'login', query: { email: email.value } })
}

async function verify() {
  const value = code.value.join('')
  if (value.length !== 6) {
    error.value = '请输入完整的 6 位验证码'
    return
  }

  loading.value = true
  error.value = ''
  try {
    const result = await authApi.verify({ email: email.value, code: value })
    if (!result.success) throw new Error(result.message || '验证码验证失败')
    const currentUser = await authApi.me().catch(() => result.user)
    setCurrentUser(currentUser)
    sessionStorage.removeItem('simple_ledger_pending_email')
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

async function resend() {
  resending.value = true
  error.value = ''
  try {
    const result = await authApi.sendCode({ email: email.value })
    if (!result.success) throw new Error(result.message || '重新发送失败')
    startCountdown()
  } catch (err) {
    error.value = err.message
  } finally {
    resending.value = false
  }
}

onMounted(() => {
  if (!email.value) {
    router.replace({ name: 'login' })
    return
  }
  startCountdown()
  inputs.value[0]?.focus()
})

onBeforeUnmount(() => clearInterval(timer))
</script>
