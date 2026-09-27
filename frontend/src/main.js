import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './api/client'
import { clearCurrentUser } from './composables/useAuth'
import './styles/main.scss'

const app = createApp(App)

setUnauthorizedHandler(() => {
  clearCurrentUser()
  if (router.currentRoute.value.meta.adminArea) {
    router.replace({
      name: 'admin-login',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  } else if (router.currentRoute.value.meta.requireAuth) {
    router.replace({
      name: 'login',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  }
})

app.use(router)
app.mount('#app')
