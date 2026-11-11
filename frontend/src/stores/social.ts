import { ref } from 'vue'
import { defineStore } from 'pinia'
import { fetchSocialContent, getSocialPlatforms } from '@/api/social'
import { toApiError } from '@/api/client'
import type {
  SocialFetchResponse,
  SocialPlatformInfo,
} from '@/types'

export const useSocialStore = defineStore('social', () => {
  const result = ref<SocialFetchResponse | null>(null)
  const platforms = ref<SocialPlatformInfo[]>([])
  const loading = ref(false)
  const error = ref('')
  const errorHint = ref('')
  const errorCode = ref('')
  const platformLoading = ref(false)

  async function loadPlatforms(): Promise<void> {
    if (platformLoading.value) {
      return
    }
    platformLoading.value = true
    try {
      const response = await getSocialPlatforms()
      platforms.value = response.platforms
    } catch {
      // Support metadata is supplementary; the fetch action remains usable.
    } finally {
      platformLoading.value = false
    }
  }

  async function fetchContent(url: string, maxComments = 30): Promise<void> {
    loading.value = true
    error.value = ''
    errorHint.value = ''
    errorCode.value = ''
    result.value = null
    try {
      result.value = await fetchSocialContent({
        url,
        max_comments: maxComments,
        include_replies: true,
      })
    } catch (caught: unknown) {
      const apiError = toApiError(caught)
      error.value = apiError.message
      errorHint.value = apiError.hint ?? ''
      errorCode.value = apiError.code ?? ''
    } finally {
      loading.value = false
    }
  }

  function clearResult(): void {
    result.value = null
    error.value = ''
    errorHint.value = ''
    errorCode.value = ''
  }

  return {
    result,
    platforms,
    loading,
    error,
    errorHint,
    errorCode,
    platformLoading,
    loadPlatforms,
    fetchContent,
    clearResult,
  }
})
