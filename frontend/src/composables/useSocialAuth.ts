import { onBeforeUnmount, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useSocialAuthStore } from '@/stores/socialAuth'

export function useSocialAuth() {
  const store = useSocialAuthStore()
  const { statuses, loading, actionPlatform, error, notice, statusMap } = storeToRefs(store)

  const refreshOnFocus = (): void => {
    void store.loadStatuses()
  }

  onMounted(() => {
    void store.loadStatuses()
    store.startStatusRefresh()
    window.addEventListener('focus', refreshOnFocus)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('focus', refreshOnFocus)
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
