import { buildApiUrl, request } from './http'
import type { DocumentPreview } from '../types/preview'

export function getDocumentPreview(docId: string): Promise<DocumentPreview> {
  return request<DocumentPreview>({
    method: 'GET',
    url: `/api/documents/${docId}/preview`,
  })
}

export function downloadDocumentUrl(docId: string): string {
  return buildApiUrl(`/api/documents/${docId}/download`)
}
