const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export class ApiError extends Error {
  constructor(message, status = 0, payload = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

function detailMessage(detail) {
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return ''

  return detail
    .map((item) => item?.msg)
    .filter(Boolean)
    .join('；')
}

async function parseResponse(response) {
  if (response.status === 204) return null

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

export async function request(path, options = {}) {
  const {
    method = 'GET',
    body,
    headers = {},
    signal,
    responseType = 'json',
  } = options

  const requestHeaders = { ...headers }
  const isFormData = body instanceof FormData

  if (body !== undefined && !isFormData && !requestHeaders['Content-Type']) {
    requestHeaders['Content-Type'] = 'application/json'
  }

  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      body,
      headers: requestHeaders,
      credentials: 'include',
      signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('网络连接失败，请检查服务是否已启动')
  }

  if (response.status === 401) {
    unauthorizedHandler?.()
  }

  if (!response.ok) {
    let payload = null
    try {
      payload = await parseResponse(response)
    } catch {
      payload = null
    }
    const message =
      detailMessage(payload?.detail) ||
      payload?.message ||
      `请求失败（${response.status}）`
    throw new ApiError(message, response.status, payload)
  }

  if (responseType === 'blob') return response.blob()
  if (responseType === 'text') return response.text()
  return parseResponse(response)
}

export const http = {
  get: (path, options) => request(path, options),
  post: (path, body, options = {}) =>
    request(path, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  put: (path, body, options = {}) =>
    request(path, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
}
