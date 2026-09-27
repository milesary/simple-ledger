import { http } from './client'

export const accountsApi = {
  list: (options = {}) => http.get('/accounts', options),

  create: (payload) => http.post('/accounts', payload),

  update: (id, payload) => http.put(`/accounts/${id}`, payload),

  archive: (id) => http.post(`/accounts/${id}/archive`),
}
