import { request } from './http'
import type { ListResponse } from '../types/api'
import type { TemplateDetail, TemplateListItem, TemplateRequirements } from '../types/template'

export interface ListTemplatesParams {
  search?: string
  active_only?: boolean
}

export function listTemplates(params: ListTemplatesParams = {}): Promise<ListResponse<TemplateListItem>> {
  return request<ListResponse<TemplateListItem>>({
    method: 'GET',
    url: '/api/templates',
    params,
  })
}

export function getTemplate(templateId: number): Promise<TemplateDetail> {
  return request<TemplateDetail>({
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
