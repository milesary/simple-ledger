import { http } from './client'

export const importsApi = {
  preview: (file) => {
    const body = new FormData()
    body.append('file', file)
    return http.post('/imports/preview', body)
  },
  confirm: (importToken) =>
    http.post('/imports/confirm', { import_token: importToken }),
}
