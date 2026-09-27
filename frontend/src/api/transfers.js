import { http } from './client'

export const transfersApi = {
  list: (options = {}) => http.get('/transfers', options),

  create: (payload) => http.post('/transfers', payload),

  update: (id, payload) => http.put(`/transfers/${id}`, payload),

  remove: (id) => http.delete(`/transfers/${id}`),
}
