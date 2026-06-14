import { request } from './http'
import type { TraceItem } from '../types/trace'

export function getTraceItem(traceId: string): Promise<TraceItem> {
  return request<TraceItem>({
    method: 'GET',
    url: `/api/trace/${traceId}`,
  })
}
