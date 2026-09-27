import { readonly, ref } from 'vue'
import { authApi } from '../api/auth'

const user = ref(null)
const initialized = ref(false)
let initializing = null

async function loadUser() {
  try {
    const result = await authApi.me()
    user.value = result
  } catch {
    user.value = null
  } finally {
    initialized.value = true
  }
}

export function initializeAuth() {
  if (initialized.value) return Promise.resolve(user.value)
  if (!initializing) initializing = loadUser()
  return initializing
}

export function setCurrentUser(value) {
  user.value = value
  initialized.value = true
}

export function clearCurrentUser() {
  user.value = null
  initialized.value = true
}

export function useAuth() {
  return {
    user: readonly(user),
    initialized: readonly(initialized),
    initializeAuth,
    setCurrentUser,
    clearCurrentUser,
  }
}
