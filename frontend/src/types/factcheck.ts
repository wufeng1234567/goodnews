/**
 * Mirrors backend/app/models/factcheck.py and article.py.
 * Field names stay snake_case on purpose so the API payload and TS contract
 * are one-to-one; only local component props use camelCase.
 */
import type {
  EvidenceStance,
  GraphMatchStatus,
  GraphVerificationStatus,
  InputType,
  NodeStatus,
  Verdict,
} from './common'

export interface ArticleContent {
  title: string
  url: string | null
  text: string
  author: string | null
  published_at: string | null
  source_name: string | null
  fetched_with: 'input_text' | 'scrapy' | 'scrapy_playwright'
  word_count: number
}

export interface FactCheckRequest {
  input_type: InputType
  content: string
  language?: string
  max_evidence_rounds?: number | null
}

export interface Claim {
  id: string
  text: string
  entities: string[]
  importance: 'high' | 'medium' | 'low'
  verdict: Verdict | null
  confidence: number | null
  reasoning: string | null
  evidence_ids: string[]
}

export interface Evidence {
  id: string
  claim_ids: string[]
  title: string
  url: string
  snippet: string
  content_excerpt: string
  source_name: string
  published_at: string | null
  retrieved_at: string
  stance: EvidenceStance
  relevance: number
  query: string
}

export interface GraphMatch {
  claim_id: string
  subject: string
  predicate: string
  claimed_object: string
  graph_object: string | null
  status: GraphMatchStatus
  confidence: number
  note: string
}

export interface GraphVerificationResult {
  status: GraphVerificationStatus
  matches: GraphMatch[]
  checked_claims: number
  graph_entities: number
  graph_relations: number
  notes: string[]
  elapsed_ms: number
  round: number
}

export interface TraceStep {
  node: string
  label: string
  status: NodeStatus
  detail: string
  duration_ms: number
  sequence: number
}

export interface FactCheckResponse {
  id: string
  input_type: InputType
  source_url: string | null
  verdict: Verdict
  confidence: number
  claims: Claim[]
  evidence: Evidence[]
  graph_verification: GraphVerificationResult
  reasoning: string
  article: ArticleContent
  trace: TraceStep[]
  warnings: string[]
  duration_ms: number
  created_at: string
}

export interface FactCheckHistoryItem {
  id: string
  input_preview: string
  input_type: InputType
  source_url: string | null
  verdict: Verdict
  confidence: number
  created_at: string
}

export interface FactCheckHistoryResponse {
  items: FactCheckHistoryItem[]
  total: number
}
