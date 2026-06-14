import { buildApiUrl, request } from './http'
import type { ListResponse } from '../types/api'
import type {
  AIConfig,
  AIConfigTestResult,
  AIConfigUpdatePayload,
  EntitySchemaFieldRecord,
  EntitySchemaImportPreview,
  ListEntitySchemaParams,
  ListTemplateRelationsParams,
  SettingsHealth,
  TemplateFileRecord,
  TemplateRelationImportPreview,
  TemplateRelationRecord,
  UploadTemplateFilePayload,
} from '../types/settings'

export function getSettingsHealth(): Promise<SettingsHealth> {
  return request<SettingsHealth>({
    method: 'GET',
    url: '/api/settings/health',
  })
}

export function listTemplateFiles(): Promise<ListResponse<TemplateFileRecord>> {
  return request<ListResponse<TemplateFileRecord>>({
    method: 'GET',
    url: '/api/settings/template-files',
  })
}

export function uploadTemplateFile(payload: UploadTemplateFilePayload): Promise<TemplateFileRecord> {
  const formData = new FormData()
  formData.append('template_name', payload.template_name)
  formData.append('description', payload.description || '')
  formData.append('file', payload.file)

  return request<TemplateFileRecord>({
    method: 'POST',
    url: '/api/settings/template-files',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function deactivateTemplateFile(templateId: number): Promise<TemplateFileRecord> {
  return request<TemplateFileRecord>({
    method: 'DELETE',
    url: `/api/settings/template-files/${templateId}`,
  })
}

export function downloadTemplateFileUrl(templateId: number): string {
  return buildApiUrl(`/api/settings/template-files/${templateId}/download`)
}

export function listEntitySchema(params: ListEntitySchemaParams): Promise<ListResponse<EntitySchemaFieldRecord>> {
  return request<ListResponse<EntitySchemaFieldRecord>>({
    method: 'GET',
    url: '/api/settings/entity-schema',
    params,
  })
}

export function previewEntitySchemaImport(file: File): Promise<EntitySchemaImportPreview> {
  const formData = new FormData()
  formData.append('file', file)

  return request<EntitySchemaImportPreview>({
    method: 'POST',
    url: '/api/settings/entity-schema/import/preview',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function commitEntitySchemaImport(importId: string): Promise<EntitySchemaImportPreview> {
  return request<EntitySchemaImportPreview>({
    method: 'POST',
    url: '/api/settings/entity-schema/import/commit',
    data: {
      import_id: importId,
      mode: 'upsert',
    },
  })
}

export function exportEntitySchemaUrl(): string {
  return buildApiUrl('/api/settings/entity-schema/export')
}

export function listTemplateRelations(params: ListTemplateRelationsParams): Promise<ListResponse<TemplateRelationRecord>> {
  return request<ListResponse<TemplateRelationRecord>>({
    method: 'GET',
    url: '/api/settings/template-relations',
    params,
  })
}

export function previewTemplateRelationImport(file: File): Promise<TemplateRelationImportPreview> {
  const formData = new FormData()
  formData.append('file', file)

  return request<TemplateRelationImportPreview>({
    method: 'POST',
    url: '/api/settings/template-relations/import/preview',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function commitTemplateRelationImport(importId: string): Promise<TemplateRelationImportPreview> {
  return request<TemplateRelationImportPreview>({
    method: 'POST',
    url: '/api/settings/template-relations/import/commit',
    data: {
      import_id: importId,
      mode: 'upsert',
    },
  })
}

export function exportTemplateRelationsUrl(): string {
  return buildApiUrl('/api/settings/template-relations/export')
}

export function getAIConfig(): Promise<AIConfig> {
  return request<AIConfig>({
    method: 'GET',
    url: '/api/settings/ai-config',
  })
}

export function updateAIConfig(payload: AIConfigUpdatePayload): Promise<AIConfig> {
  return request<AIConfig>({
    method: 'PUT',
    url: '/api/settings/ai-config',
    data: payload,
  })
}

export function testAIConfig(): Promise<AIConfigTestResult> {
  return request<AIConfigTestResult>({
    method: 'POST',
    url: '/api/settings/ai-config/test',
  })
}
