import apiClient from './client'
import type {
  SocialAuthStatus,
  SocialAuthStatusListResponse,
  SocialFetchRequest,
  SocialFetchResponse,
  SocialJobCreateRequest,
  SocialJobStatus,
  SocialPlatform,
  SocialPlatformListResponse,
  SocialReplyResponse,
} from '@/types'

export async function fetchSocialContent(
  payload: SocialFetchRequest,
): Promise<SocialFetchResponse> {
  const { data } = await apiClient.post<SocialFetchResponse>('/social/fetch', payload)
  return data
}

export async function getSocialPlatforms(): Promise<SocialPlatformListResponse> {
  const { data } = await apiClient.get<SocialPlatformListResponse>('/social/platforms')
  return data
}

export async function getSocialAuthStatus(): Promise<SocialAuthStatusListResponse> {
  const { data } = await apiClient.get<SocialAuthStatusListResponse>('/social/auth/status')
  return data
}

export async function startSocialLogin(
  platform: SocialPlatform,
): Promise<SocialAuthStatus> {
  const { data } = await apiClient.post<SocialAuthStatus>('/social/auth/login', { platform })
  return data
}

export async function logoutSocial(platform: SocialPlatform): Promise<SocialAuthStatus> {
  const { data } = await apiClient.post<SocialAuthStatus>('/social/auth/logout', { platform })
  return data
}

export async function refreshSocialSession(
  platform: SocialPlatform,
): Promise<SocialAuthStatus> {
  const { data } = await apiClient.post<SocialAuthStatus>('/social/auth/refresh', { platform })
  return data
}

export async function createSocialJob(
  payload: SocialJobCreateRequest,
): Promise<SocialJobStatus> {
  const { data } = await apiClient.post<SocialJobStatus>('/social/jobs', payload)
  return data
}

export async function getSocialJob(jobId: string): Promise<SocialJobStatus> {
  const { data } = await apiClient.get<SocialJobStatus>(`/social/jobs/${jobId}`)
  return data
}

export async function fetchSocialReplies(
  platform: SocialPlatform,
  contentId: string,
  rootId: string,
): Promise<SocialReplyResponse> {
  const { data } = await apiClient.get<SocialReplyResponse>('/social/comments/replies', {
    params: {
      platform,
      content_id: contentId,
      root_id: rootId,
      max_comments: 50_000,
    },
  })
  return data
}

export function socialJobExportUrl(jobId: string, format: 'xlsx' | 'md' | 'txt'): string {
  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  return `${base}/social/jobs/${jobId}/export?format=${format}`
}
