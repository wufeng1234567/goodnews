import axios, { type AxiosError } from 'axios'

interface ErrorDetail {
  code?: string
  message?: string
}

export class ApiError extends Error {
  readonly status: number | null
  readonly code: string | null

  constructor(message: string, status: number | null = null, code: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function readDetail(data: unknown): ErrorDetail | null {
  if (!isRecord(data)) {
    return null
  }
  const detail = data.detail
  if (typeof detail === 'string') {
    return { message: detail }
  }
  if (isRecord(detail)) {
    return {
      code: typeof detail.code === 'string' ? detail.code : undefined,
      message: typeof detail.message === 'string' ? detail.message : undefined,
    }
  }
  return null
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<unknown>
    const detail = readDetail(axiosError.response?.data)
    const fallback =
      axiosError.code === 'ECONNABORTED'
        ? '请求超时，核查可能需要更长时间，请稍后重试'
        : '网络请求失败，请确认后端服务已启动'
    return new ApiError(
      detail?.message || fallback,
      axiosError.response?.status ?? null,
      detail?.code ?? null,
    )
  }
  return new ApiError(error instanceof Error ? error.message : '未知错误')
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 240_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(toApiError(error)),
)

export default apiClient
