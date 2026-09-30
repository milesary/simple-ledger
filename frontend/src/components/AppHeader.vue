<template>
  <header class="app-header">
    <div class="app-header__inner">
      <div class="app-header__brand-group">
        <button
          class="menu-button"
          type="button"
          :aria-expanded="navOpen"
          aria-label="打开导航菜单"
          @click="emit('toggle-nav')"
        >
          <Menu :size="20" />
        </button>

        <RouterLink class="brand" :to="{ name: 'dashboard' }">
          <span class="brand__mark">账</span>
          <span class="brand__copy">
            <strong>简账</strong>
            <small>SimpleLedger</small>
          </span>
        </RouterLink>
      </div>

      <div></div>

      <div class="header-actions">
        <RouterLink class="header-action" :to="{ name: 'transaction-new' }">
          <Plus :size="17" />
          记一笔
        </RouterLink>

        <div v-if="user" class="user-chip" :title="user.email">
          <span class="user-chip__avatar">{{ user.email?.slice(0, 1).toUpperCase() }}</span>
          <span class="user-chip__email">{{ user.email }}</span>
        </div>

        <button
          class="icon-button"
          type="button"
          :aria-label="logoutError || '退出登录'"
          :title="logoutError || '退出登录'"
          :disabled="loggingOut"
          @click="logout"
        >
          <LogOut :size="18" />
        </button>
      </div>
    </div>

    <p v-if="logoutError" class="app-header__error" role="alert">{{ logoutError }}</p>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { LogOut, Menu, Plus } from 'lucide-vue-next'
import { authApi } from '../api/auth'
import { clearCurrentUser, useAuth } from '../composables/useAuth'

defineProps({
  navOpen: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toggle-nav'])
const router = useRouter()
const { user } = useAuth()
const loggingOut = ref(false)
const logoutError = ref('')

async function logout() {
  loggingOut.value = true
  logoutError.value = ''
  try {
    await authApi.logout()
  } catch (err) {
    // 登出请求失败时服务端 Session 仍然有效，绝不能假装已退出，
    // 否则共享终端上的下一位使用者刷新页面就会回到登录态。
    logoutError.value = err?.message
      ? `退出失败：${err.message}`
      : '退出失败，请检查网络后重试'
    loggingOut.value = false
    return
  }
  clearCurrentUser()
  loggingOut.value = false
  router.replace({ name: 'login' })
}
</script>
