import { ref } from 'vue'
import { defineStore } from 'pinia'
import { createSocialJob, getSocialJob, socialJobExportUrl } from '@/api/social'
import { toApiError } from '@/api/client'
import type { SocialJobStatus } from '@/types'

export const useSocialJobStore = defineStore('socialJob', () => {
  const job = ref<SocialJobStatus | null>(null)
  const loading = ref(false)
  const error = ref('')
  let pollTimer: number | null = null
  let attempts = 0

  function stopPolling(): void {
    if (pollTimer !== null) {
      window.clearTimeout(pollTimer)
      pollTimer = null
    }
    attempts = 0
  }

  async function poll(): Promise<void> {
    if (!job.value) {
      return
    }
    if (attempts >= 900) {
      stopPolling()
      error.value = '全量采集等待超时，请稍后重试或降低评论上限。'
      return
    }
    attempts += 1
    try {
      job.value = await getSocialJob(job.value.id)
      if (job.value.state === 'queued' || job.value.state === 'running') {
        pollTimer = window.setTimeout(() => {
          void poll()
        }, 2_000)
      } else if (job.value.state === 'failed') {
        error.value = job.value.error || '全量评论采集失败'
      }
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
      stopPolling()
    }
  }

  async function start(url: string): Promise<void> {
    loading.value = true
    error.value = ''
    stopPolling()
    try {
      job.value = await createSocialJob({
        url,
        include_replies: true,
        max_comments: 0,
      })
      void poll()
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
    } finally {
      loading.value = false
    }
  }

  function exportUrl(format: 'xlsx' | 'md' | 'txt'): string {
    return job.value ? socialJobExportUrl(job.value.id, format) : '#'
  }

  function dispose(): void {
    stopPolling()
  }

  return {
    job,
    loading,
    error,
    start,
    stopPolling,
    exportUrl,
    dispose,
  }
})
