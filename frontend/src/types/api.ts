export interface ApiErrorDetail {
  code: string
  message: string
  detail?: unknown
  details?: Record<string, unknown>
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: ApiErrorDetail
  request_id: string
  timestamp: string
}

export interface ListResponse<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

export class ApiRequestError extends Error {
  code: string
  details?: unknown

  constructor(error: ApiErrorDetail) {
    super(error.message)
    this.name = 'ApiRequestError'
    this.code = error.code
    this.details = error.detail ?? error.details
  }
}
