import apiClient from './client'
import type { HotNewsResponse, SearchResponse } from '@/types'

export async function searchNews(query: string, limit = 8): Promise<SearchResponse> {
  const { data } = await apiClient.post<SearchResponse>('/search', { query, limit })
  return data
}

export async function getHotNews(limit = 8): Promise<HotNewsResponse> {
  const { data } = await apiClient.get<HotNewsResponse>('/search/hot', {
    params: { limit },
  })
  return data
}
