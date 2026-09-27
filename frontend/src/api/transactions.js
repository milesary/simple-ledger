import { http } from './client'

function queryString(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      search.set(key, String(value))
    }
  })
  const value = search.toString()
  return value ? `?${value}` : ''
}

export const transactionsApi = {
  list: (params, options = {}) =>
    http.get(`/transactions${queryString(params)}`, options),

  get: (id, options = {}) => http.get(`/transactions/${id}`, options),

  create: (payload) => http.post('/transactions', payload),

  update: (id, payload) => http.put(`/transactions/${id}`, payload),

  remove: (id) => http.delete(`/transactions/${id}`),

  categories: (options = {}) => http.get('/categories', options),
}
