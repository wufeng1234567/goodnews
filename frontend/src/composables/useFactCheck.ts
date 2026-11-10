import { storeToRefs } from 'pinia'
import { useFactCheckStore } from '@/stores/factcheck'

export function useFactCheck() {
  const store = useFactCheckStore()
  const {
    result,
    history,
    loading,
    detailLoading,
    historyLoading,
    error,
    activeStep,
    hasResult,
    hasHistory,
  } = storeToRefs(store)

  async function submit(content: string): Promise<void> {
    const trimmed = content.trim()
    if (!trimmed) {
      return
    }
    // Automatic detection keeps the UI to one input and one primary button.
    // The backend safely distinguishes a URL from free text.
    await store.run({ input_type: 'auto', content: trimmed, language: 'zh' })
  }

  async function openRecord(id: string): Promise<void> {
    await store.openRecord(id)
  }

  return {
    result,
    history,
    loading,
    detailLoading,
    historyLoading,
    error,
    activeStep,
    hasResult,
    hasHistory,
    submit,
    openRecord,
    loadHistory: store.loadHistory,
    dismissResult: store.dismissResult,
  }
}
