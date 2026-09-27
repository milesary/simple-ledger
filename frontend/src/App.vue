<template>
  <div v-if="route.meta.adminArea" class="admin-shell">
    <AdminHeader v-if="route.meta.adminOnly" />
    <main class="admin-main">
      <RouterView />
    </main>
  </div>

  <div
    v-else
    class="app-shell"
    :class="{
      'app-shell--guest': route.meta.guestOnly,
      'app-shell--authenticated': route.meta.requireAuth,
    }"
  >
    <AppHeader
      v-if="route.meta.requireAuth"
      :nav-open="navOpen"
      @toggle-nav="navOpen = !navOpen"
    />
    <AppNav v-if="route.meta.requireAuth" :open="navOpen" @close="navOpen = false" />

    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AdminHeader from './components/AdminHeader.vue'
import AppHeader from './components/AppHeader.vue'
import AppNav from './components/AppNav.vue'

const route = useRoute()
const navOpen = ref(false)

watch(
  () => route.fullPath,
  () => {
    navOpen.value = false
  },
)
</script>
