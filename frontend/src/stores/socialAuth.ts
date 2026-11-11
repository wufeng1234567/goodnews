import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  getSocialAuthStatus,
  logoutSocial,
  startSocialLogin,
} from '@/api/social'
import { toApiError } from '@/api/client'
import type { SocialAuthStatus, SocialPlatform } from '@/types'

export const useSocialAuthStore = defineStore('socialAuth', () => {
  const statuses = ref<SocialAuthStatus[]>([])
  const loading = ref(false)
  const actionPlatform = ref<SocialPlatform | null>(null)
  const error = ref('')
  const notice = ref('')
  let pollTimer: number | null = null
  let refreshTimer: number | null = null
  let pollAttempts = 0

  const statusMap = computed<Record<string, SocialAuthStatus>>(() =>
    Object.fromEntries(statuses.value.map((status) => [status.platform, status])),
  )

  function upsert(status: SocialAuthStatus): void {
    const index = statuses.value.findIndex((item) => item.platform === status.platform)
    if (index === -1) {
      statuses.value = [...statuses.value, status]
    } else {
      const copy = [...statuses.value]
      copy[index] = status
      statuses.value = copy
    }
  }

  async function loadStatuses(): Promise<void> {
    if (loading.value) {
      return
    }
    loading.value = true
    try {
      const response = await getSocialAuthStatus()
      statuses.value = response.statuses
      const waiting = response.statuses.some((status) => status.state === 'waiting')
      if (!waiting) {
        stopPolling()
      }
    } catch {
      // Account status is supplementary; the content collection still works
      // for public Bilibili/Douyin content without a saved session.
    } finally {
      loading.value = false
    }
  }

  function stopPolling(): void {
    if (pollTimer !== null) {
      window.clearTimeout(pollTimer)
      pollTimer = null
    }
    pollAttempts = 0
  }

  async function pollLogin(): Promise<void> {
    if (pollAttempts >= 150) {
      stopPolling()
      notice.value = ''
      error.value = '登录等待超时，请重新点击登录。'
      return
    }
    pollAttempts += 1
    await loadStatuses()
    const waiting = statuses.value.some((status) => status.state === 'waiting')
    if (waiting) {
      pollTimer = window.setTimeout(() => {
        void pollLogin()
      }, 2_000)
      return
    }
    const failed = statuses.value.find((status) => status.state === 'failed')
    if (failed) {
      error.value = failed.message
      notice.value = ''
    } else if (statuses.value.some((status) => status.logged_in)) {
      notice.value = '登录成功，登录态已保存，采集时会自动使用。'
    } else {
      notice.value = ''
    }
  }

  async function login(platform: SocialPlatform): Promise<void> {
    actionPlatform.value = platform
    error.value = ''
    notice.value = '正在打开登录窗口，请完成扫码或账号登录……'
    try {
      const status = await startSocialLogin(platform)
      upsert(status)
      if (status.state === 'waiting') {
        stopPolling()
        pollAttempts = 0
        void pollLogin()
      } else if (status.state === 'failed') {
        error.value = status.message
      }
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
    } finally {
      actionPlatform.value = null
    }
  }

  async function logout(platform: SocialPlatform): Promise<void> {
    actionPlatform.value = platform
    error.value = ''
    notice.value = ''
    try {
      const status = await logoutSocial(platform)
      upsert(status)
    } catch (caught: unknown) {
      error.value = toApiError(caught).message
    } finally {
      actionPlatform.value = null
    }
  }

  async function switchAccount(platform: SocialPlatform): Promise<void> {
    await logout(platform)
    await login(platform)
  }

  function startStatusRefresh(): void {
    if (refreshTimer !== null) {
      return
    }
    refreshTimer = window.setInterval(() => {
      void loadStatuses()
    }, 60_000)
  }

  function dispose(): void {
    stopPolling()
    if (refreshTimer !== null) {
      window.clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  return {
    statuses,
    loading,
    actionPlatform,
    error,
    notice,
    statusMap,
    loadStatuses,
    login,
    logout,
    switchAccount,
    startStatusRefresh,
    dispose,
  }
})
