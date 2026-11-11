import { onBeforeUnmount, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useSocialAuthStore } from '@/stores/socialAuth'

export function useSocialAuth() {
  const store = useSocialAuthStore()
  const { statuses, loading, actionPlatform, error, notice, statusMap } = storeToRefs(store)

  onMounted(() => {
    void store.loadStatuses()
    store.startStatusRefresh()
  })

  onBeforeUnmount(() => {
    store.dispose()
  })

  return {
    statuses,
    loading,
    actionPlatform,
    error,
    notice,
    statusMap,
    login: store.login,
    logout: store.logout,
    switchAccount: store.switchAccount,
    loadStatuses: store.loadStatuses,
  }
}
