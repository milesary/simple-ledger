import { http } from './client'

export const recurringApi = {
  list: (options = {}) => http.get('/recurring', options),

  create: (payload) => http.post('/recurring', payload),

  update: (id, payload) => http.put(`/recurring/${id}`, payload),

  toggle: (id) => http.post(`/recurring/${id}/toggle`),

  remove: (id) => http.delete(`/recurring/${id}`),
}
