import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  createFactCheck,
  getFactCheckDetail,
  getFactCheckHistory,
} from '@/api/factcheck'
import { toApiError } from '@/api/client'
import type {
  FactCheckHistoryItem,
  FactCheckRequest,
  FactCheckResponse,
} from '@/types'

export const useFactCheckStore = defineStore('factcheck', () => {
  const result = ref<FactCheckResponse | null>(null)
  const history = ref<FactCheckHistoryItem[]>([])
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref('')
  const activeStep = ref(0)
  const historyLoading = ref(false)
  let progressTimer: number | null = null

  const hasResult = computed(() => result.value !== null)
  const hasHistory = computed(() => history.value.length > 0)

  function startProgress(): void {
    stopProgress()
    activeStep.value = 0
    progressTimer = window.setInterval(() => {
      activeStep.value = Math.min(activeStep.value + 1, 4)
    }, 3600)
  }

  function stopProgress(): void {
    if (progressTimer !== null) {
      window.clearInterval(progressTimer)
      progressTimer = null
    }
  }

  async function run(payload: FactCheckRequest): Promise<void> {
    loading.value = true
    error.value = ''
    result.value = null
    startProgress()
    try {
      result.value = await createFactCheck(payload)
      await loadHistory()
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
    } finally {
      stopProgress()
      loading.value = false
    }
  }

  async function openRecord(id: string): Promise<void> {
    detailLoading.value = true
    error.value = ''
    try {
      result.value = await getFactCheckDetail(id)
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
    } finally {
      detailLoading.value = false
    }
  }

  async function loadHistory(): Promise<void> {
    if (historyLoading.value) {
      return
    }
    historyLoading.value = true
    try {
      const response = await getFactCheckHistory()
      history.value = response.items
    } catch {
      // History is supplementary; never replace the main analysis result with
      // a history-loading error.
    } finally {
      historyLoading.value = false
    }
  }

  function dismissResult(): void {
    result.value = null
    error.value = ''
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
    run,
    openRecord,
    loadHistory,
    dismissResult,
  }
})
