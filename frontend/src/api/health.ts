import apiClient from './client'
import type { GraphStats, HealthResponse } from '@/types'

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health')
  return data
}

export async function getGraphStats(): Promise<GraphStats> {
  const { data } = await apiClient.get<GraphStats>('/graph/stats')
  return data
}
