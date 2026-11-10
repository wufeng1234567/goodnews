import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getHotNews, searchNews } from '@/api/search'
import { toApiError } from '@/api/client'
import type { SearchResultItem } from '@/types'

export const useSearchStore = defineStore('search', () => {
  const hotItems = ref<SearchResultItem[]>([])
  const results = ref<SearchResultItem[]>([])
  const loading = ref(false)
  const hotLoading = ref(false)
  const error = ref('')
  const lastQuery = ref('')
  const provider = ref('')
  const hasSearched = ref(false)

  async function loadHot(limit = 8): Promise<void> {
    if (hotLoading.value) {
      return
    }
    hotLoading.value = true
    error.value = ''
    try {
      const response = await getHotNews(limit)
      hotItems.value = response.items
      provider.value = response.provider
      if (!response.items.length && response.error) {
        error.value = response.error
      }
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
    } finally {
      hotLoading.value = false
    }
  }

  async function search(query: string): Promise<void> {
    const trimmed = query.trim()
    if (!trimmed) {
      return
    }
    loading.value = true
    error.value = ''
    hasSearched.value = true
    lastQuery.value = trimmed
    try {
      const response = await searchNews(trimmed)
      results.value = response.items
      provider.value = response.provider
      if (!response.items.length && response.error) {
        error.value = response.error
      }
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
      results.value = []
    } finally {
      loading.value = false
    }
  }

  function resetSearch(): void {
    results.value = []
    error.value = ''
    hasSearched.value = false
    lastQuery.value = ''
  }

  return {
    hotItems,
    results,
    loading,
    hotLoading,
    error,
    lastQuery,
    provider,
    hasSearched,
    loadHot,
    search,
    resetSearch,
  }
})
