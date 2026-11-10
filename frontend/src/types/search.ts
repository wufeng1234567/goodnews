/** Mirrors backend/app/models/search.py. */

export interface SearchRequest {
  query: string
  limit?: number
}

export interface SearchResultItem {
  id: string
  title: string
  url: string
  snippet: string
  source_name: string
  published_at: string | null
  provider: string
  rank: number
}

export interface SearchResponse {
  query: string
  items: SearchResultItem[]
  provider: string
  cached: boolean
  fetched_at: string
  error: string | null
}

export interface HotNewsResponse {
  region: string
  items: SearchResultItem[]
  provider: string
  cached: boolean
  fetched_at: string
  error: string | null
}
