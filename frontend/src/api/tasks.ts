import { buildApiUrl, request } from './http'
import type { ListResponse } from '../types/api'
import type {
  CreateTaskPayload,
  CreateTaskResponse,
  GenerateTaskResponse,
  TaskListItem,
  TaskOutputsResponse,
  UploadedFileResponse,
} from '../types/task'
import type { ValidateTaskResponse } from '../types/validation'

export function listTasks(): Promise<ListResponse<TaskListItem>> {
  return request<ListResponse<TaskListItem>>({
    method: 'GET',
    url: '/api/tasks',
  })
}

export function createTask(payload: CreateTaskPayload): Promise<CreateTaskResponse> {
  return request<CreateTaskResponse>({
    method: 'POST',
    url: '/api/tasks',
    data: payload,
  })
}

export function uploadTaskFile(taskId: string, tableName: string, file: File): Promise<UploadedFileResponse> {
  const formData = new FormData()
  formData.append('table_name', tableName)
  formData.append('file', file)

  return request<UploadedFileResponse>({
    method: 'POST',
    url: `/api/tasks/${taskId}/upload`,
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function validateTask(taskId: string): Promise<ValidateTaskResponse> {
  return request<ValidateTaskResponse>({
    method: 'POST',
    url: `/api/tasks/${taskId}/validate`,
  })
}

export function generateTask(taskId: string): Promise<GenerateTaskResponse> {
  return request<GenerateTaskResponse>({
    method: 'POST',
    url: `/api/tasks/${taskId}/generate`,
  })
}

export function listTaskOutputs(taskId: string): Promise<TaskOutputsResponse> {
  return request<TaskOutputsResponse>({
    method: 'GET',
    url: `/api/tasks/${taskId}/outputs`,
  })
}

export function downloadTaskZipUrl(taskId: string): string {
  return buildApiUrl(`/api/tasks/${taskId}/download-zip`)
}
