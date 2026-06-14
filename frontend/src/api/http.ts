import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'
import { ApiRequestError, type ApiErrorDetail, type ApiResponse } from '../types/api'

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) || ''
export const API_BASE_URL = rawBaseUrl.replace(/\/$/, '')

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

export function buildApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const response = await http.request<ApiResponse<T>>(config)
    const payload = response.data
    if (!payload.success) {
      throw new ApiRequestError(payload.error || fallbackError())
    }
    return payload.data as T
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error
    }
    if (axios.isAxiosError(error)) {
      const payload = (error as AxiosError<ApiResponse<unknown>>).response?.data
      if (payload?.error) {
        throw new ApiRequestError(payload.error)
      }
      throw new ApiRequestError({
        code: 'NETWORK_ERROR',
        message: error.message || '请求失败',
      })
    }
    throw error
  }
}

function fallbackError(): ApiErrorDetail {
  return {
    code: 'API_ERROR',
    message: '接口返回失败',
  }
}
