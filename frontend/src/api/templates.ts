import { request } from './http'
import type { ListResponse } from '../types/api'
import type { TemplateInfo, TemplateRequirements } from '../types/template'

export function listTemplates(): Promise<ListResponse<TemplateInfo>> {
  return request<ListResponse<TemplateInfo>>({
    method: 'GET',
    url: '/api/templates',
  })
}

export function getTemplate(templateId: number): Promise<TemplateInfo> {
  return request<TemplateInfo>({
    method: 'GET',
    url: `/api/templates/${templateId}`,
  })
}

export function getTemplateRequirements(templateId: number): Promise<TemplateRequirements> {
  return request<TemplateRequirements>({
    method: 'GET',
    url: `/api/templates/${templateId}/requirements`,
  })
}
