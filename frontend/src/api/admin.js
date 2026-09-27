import { http } from './client'

export const adminApi = {
  users: ({ q = '', signal } = {}) => {
    const query = q ? `?q=${encodeURIComponent(q)}` : ''
    return http.get(`/admin/users${query}`, { signal })
  },
  toggleUser: (id) => http.post(`/admin/users/${id}/toggle`),
  toggleRole: (id) => http.post(`/admin/users/${id}/role`),
  resetPassword: (id, newPassword) =>
    http.post(`/admin/users/${id}/reset-password`, {
      new_password: newPassword,
    }),
  removeUser: (id) => http.delete(`/admin/users/${id}`),
}
