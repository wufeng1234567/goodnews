import { storeToRefs } from 'pinia'
import { useSearchStore } from '@/stores/search'

export function useNewsSearch() {
  const store = useSearchStore()
  const { hotItems, results, loading, hotLoading, error, lastQuery, provider, hasSearched } =
    storeToRefs(store)

  async function loadHot(): Promise<void> {
    await store.loadHot()
  }

  async function search(query: string): Promise<void> {
    await store.search(query)
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
    resetSearch: store.resetSearch,
  }
}
