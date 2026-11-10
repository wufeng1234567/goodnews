export interface GraphStats {
  entity_count: number
  relation_count: number
  available: boolean
  note: string
}

export interface DependencyStatus {
  name: string
  ok: boolean
  detail: string
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  app_name: string
  version: string
  environment: string
  llm_configured: boolean
  dependencies: DependencyStatus[]
  graph: GraphStats
}
