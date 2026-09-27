import { http } from './client'

export const authApi = {
  register: (payload) => http.post('/auth/register', payload),
  login: (payload) => http.post('/auth/login', payload),
  sendCode: (payload) => http.post('/auth/code', payload),
  verify: (payload) => http.post('/auth/verify', payload),
  logout: () => http.post('/auth/logout'),
  me: (options) => http.get('/auth/me', options),
}
