import apiClient from './client'
import type {
  SocialFetchRequest,
  SocialFetchResponse,
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
