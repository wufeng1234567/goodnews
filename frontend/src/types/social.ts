/** Mirrors backend/app/models/social.py. */
export type SocialPlatform = 'xiaohongshu' | 'douyin' | 'bilibili'

export type SocialContentType = 'video' | 'note' | 'article' | 'unknown'

export interface SocialAuthor {
  id: string
  name: string
  handle: string
  avatar_url: string | null
  profile_url: string | null
  follower_count: number | null
}

export interface SocialMetrics {
  view_count: number | null
  play_count: number | null
  like_count: number | null
  comment_count: number | null
  share_count: number | null
  collect_count: number | null
  coin_count: number | null
  danmaku_count: number | null
  extra: Record<string, number>
  total_engagement: number
}

export interface SocialContent {
  platform: SocialPlatform
  content_id: string
  content_type: SocialContentType
  url: string
  title: string
  description: string
  author: SocialAuthor
  published_at: string | null
  cover_url: string | null
  media_urls: string[]
  duration_seconds: number | null
  tags: string[]
  metrics: SocialMetrics
}

export interface SocialComment {
  id: string
  content_id: string
  parent_id: string | null
  text: string
  author_name: string
  author_id: string
  author_avatar_url: string | null
  like_count: number
  reply_count: number
  created_at: string | null
  replies: SocialComment[]
}

export interface SocialFetchRequest {
  url: string
  max_comments?: number
  include_replies?: boolean
}

export interface SocialFetchResponse {
  id: string
  platform: SocialPlatform
  content: SocialContent
  comments: SocialComment[]
  fetched_at: string
  total_comments_fetched: number
  has_more: boolean
  collection_method: 'public_api' | 'browser_api'
  auth_mode: 'none' | 'cookie' | 'storage_state'
  warnings: string[]
}

export interface SocialPlatformInfo {
  platform: SocialPlatform
  label: string
  supported: boolean
  needs_login_for_comments: boolean
  login_command: string
  note: string
}

export interface SocialPlatformListResponse {
  platforms: SocialPlatformInfo[]
}

export type SocialAuthState = 'not_logged_in' | 'waiting' | 'logged_in' | 'expired' | 'failed'

export interface SocialAuthStatus {
  platform: SocialPlatform
  state: SocialAuthState
  logged_in: boolean
  account_name: string | null
  message: string
  expires_at: string | null
  last_login_at: string | null
  last_checked_at: string | null
  last_refreshed_at: string | null
  auto_refresh: boolean
}

export interface SocialAuthStatusListResponse {
  statuses: SocialAuthStatus[]
}

export type SocialJobState = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface SocialJobCreateRequest {
  url: string
  include_replies: boolean
  max_comments: number
}

export interface SocialHistoryItem {
  id: string
  platform: SocialPlatform
  content_id: string
  url: string
  title: string
  author_name: string
  comments_fetched: number
  fetched_at: string
}

export interface SocialHistoryListResponse {
  items: SocialHistoryItem[]
}

export interface SocialReplyResponse {
  root_id: string
  replies: SocialComment[]
  total_fetched: number
  has_more: boolean
}

export interface SocialJobStatus {
  id: string
  platform: SocialPlatform
  url: string
  state: SocialJobState
  progress: number
  max_comments: number
  total_fetched: number
  record_id: string | null
  error: string
  created_at: string | null
  updated_at: string | null
  finished_at: string | null
}
