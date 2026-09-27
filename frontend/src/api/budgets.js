import { http } from './client'

export const budgetsApi = {
  get: (options = {}) => http.get('/budgets', options),
  save: (payload) => http.post('/budgets', payload),
  saveCategory: (payload) => http.post('/budgets/categories', payload),
  removeCategory: ({ month, categoryId }) =>
    http.delete(
      `/budgets/categories?month=${encodeURIComponent(month)}&category_id=${encodeURIComponent(categoryId)}`,
    ),
}
