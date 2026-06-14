import { request } from './http'
import type { TraceDetail } from '../types/trace'

export function getTraceItem(traceId: string): Promise<TraceDetail> {
  return request<TraceDetail>({
    method: 'GET',
    url: `/api/trace/${traceId}`,
  })
}
