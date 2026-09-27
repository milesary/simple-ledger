import { http } from './client'

export const dashboardApi = {
  get: ({ year, signal } = {}) => {
    const query = year ? `?year=${encodeURIComponent(year)}` : ''
    return http.get(`/dashboard${query}`, { signal })
  },
}
