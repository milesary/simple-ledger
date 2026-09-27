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
          aria-label="退出登录"
          title="退出登录"
          :disabled="loggingOut"
          @click="logout"
        >
          <LogOut :size="18" />
        </button>
      </div>
    </div>
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

async function logout() {
  loggingOut.value = true
  try {
    await authApi.logout()
  } finally {
    clearCurrentUser()
    loggingOut.value = false
    router.replace({ name: 'login' })
  }
}
</script>
