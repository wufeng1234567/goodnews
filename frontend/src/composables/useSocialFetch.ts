import { storeToRefs } from 'pinia'
import { useSocialStore } from '@/stores/social'

export function useSocialFetch() {
  const store = useSocialStore()
  const {
    result,
    platforms,
    loading,
    error,
    errorHint,
    errorCode,
    platformLoading,
  } = storeToRefs(store)

  async function submit(url: string, maxComments = 30): Promise<void> {
    const trimmed = url.trim()
    if (!trimmed) {
      return
    }
    await store.fetchContent(trimmed, maxComments)
  }

  return {
    result,
    platforms,
    loading,
    error,
    errorHint,
    errorCode,
    platformLoading,
    submit,
    loadPlatforms: store.loadPlatforms,
    clearResult: store.clearResult,
  }
}
