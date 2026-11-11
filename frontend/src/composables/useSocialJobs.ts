import { onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { useSocialJobStore } from '@/stores/socialJobs'

export function useSocialJobs() {
  const store = useSocialJobStore()
  const { job, loading, error } = storeToRefs(store)

  onBeforeUnmount(() => {
    store.dispose()
  })

  return {
    job,
    loading,
    error,
    start: store.start,
    exportUrl: store.exportUrl,
    stopPolling: store.stopPolling,
  }
}
