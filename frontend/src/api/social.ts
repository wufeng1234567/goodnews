import apiClient from './client'
import type {
  SocialAuthStatus,
  SocialAuthStatusListResponse,
  SocialFetchRequest,
  SocialFetchResponse,
  SocialPlatform,
  SocialPlatformListResponse,
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
