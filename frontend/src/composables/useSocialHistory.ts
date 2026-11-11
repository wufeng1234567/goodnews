import { ref } from 'vue'
import { getSocialHistory, getSocialHistoryDetail } from '@/api/social'
import { toApiError } from '@/api/client'
import type { SocialFetchResponse, SocialHistoryItem } from '@/types'

export function useSocialHistory() {
  const items = ref<SocialHistoryItem[]>([])
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref('')

  async function load(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const response = await getSocialHistory(30)
      items.value = response.items
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(recordId: string): Promise<SocialFetchResponse | null> {
    detailLoading.value = true
    error.value = ''
    try {
      return await getSocialHistoryDetail(recordId)
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
      return null
    } finally {
      detailLoading.value = false
    }
  }

  return { items, loading, detailLoading, error, load, loadDetail }
}
