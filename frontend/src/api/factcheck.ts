import apiClient from './client'
import type {
  FactCheckHistoryResponse,
  FactCheckRequest,
  FactCheckResponse,
} from '@/types'

export async function createFactCheck(payload: FactCheckRequest): Promise<FactCheckResponse> {
  const { data } = await apiClient.post<FactCheckResponse>('/factcheck', payload)
  return data
}

export async function getFactCheckHistory(
  limit = 8,
  offset = 0,
): Promise<FactCheckHistoryResponse> {
  const { data } = await apiClient.get<FactCheckHistoryResponse>('/factcheck/history', {
    params: { limit, offset },
  })
  return data
}

export async function getFactCheckDetail(id: string): Promise<FactCheckResponse> {
  const { data } = await apiClient.get<FactCheckResponse>(`/factcheck/${id}`)
  return data
}
