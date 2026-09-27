<template>
  <header class="admin-header">
    <div class="admin-header__inner">
      <RouterLink class="admin-brand" :to="{ name: 'admin' }">
        <span class="admin-brand__mark">
          <ShieldCheck :size="22" />
        </span>
        <span class="admin-brand__copy">
          <strong>简账管理后台</strong>
          <small>ADMIN CONSOLE</small>
        </span>
      </RouterLink>

      <nav class="admin-nav" aria-label="后台导航">
        <RouterLink class="admin-nav__link" :to="{ name: 'admin' }">
          <Users :size="17" />
          账号管理
        </RouterLink>
      </nav>

      <div class="admin-header__actions">
        <div class="admin-user">
          <span class="admin-user__avatar">{{ user?.email?.slice(0, 1).toUpperCase() }}</span>
          <span class="admin-user__email">{{ user?.email }}</span>
        </div>
        <button
          class="admin-logout"
          type="button"
          :disabled="loggingOut"
          @click="logout"
        >
          <LogOut :size="17" />
          退出
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { LogOut, ShieldCheck, Users } from 'lucide-vue-next'
import { authApi } from '../api/auth'
import { clearCurrentUser, useAuth } from '../composables/useAuth'

const router = useRouter()
const { user } = useAuth()
const loggingOut = ref(false)

async function logout() {
  loggingOut.value = true
  try {
    await authApi.logout()
  } finally {
    clearCurrentUser()
    loggingOut.value = false
    router.replace({ name: 'admin-login' })
  }
}
</script>
