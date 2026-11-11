<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PlatformBadge from '@/components/PlatformBadge.vue'
import SocialCommentList from '@/components/SocialCommentList.vue'
import SocialContentCard from '@/components/SocialContentCard.vue'
import { useSocialAuth } from '@/composables/useSocialAuth'
import { useSocialFetch } from '@/composables/useSocialFetch'
import { useSocialJobs } from '@/composables/useSocialJobs'
import type { SocialAuthStatus, SocialPlatform } from '@/types'

const url = ref('')
const maxComments = ref(30)
const {
  result,
  platforms,
  loading,
  error,
  errorHint,
  errorCode,
  loadPlatforms,
  submit,
} = useSocialFetch()
const {
  statusMap: authStatusMap,
  actionPlatform: authActionPlatform,
  error: authError,
  notice: authNotice,
  login: loginPlatform,
  logout: logoutPlatform,
  switchAccount,
} = useSocialAuth()
const {
  job: fullJob,
  loading: fullJobLoading,
  error: fullJobError,
  start: startFullJob,
  exportUrl: fullJobExportUrl,
} = useSocialJobs()

const authLabels: Record<SocialAuthStatus['state'], string> = {
  not_logged_in: '未登录',
  waiting: '等待登录',
  logged_in: '已登录',
  expired: '已过期',
  failed: '登录失败',
}

function authFor(platform: SocialPlatform): SocialAuthStatus | undefined {
  return authStatusMap.value[platform]
}

function authLabel(platform: SocialPlatform): string {
  return authLabels[authFor(platform)?.state ?? 'not_logged_in']
}

function authTone(platform: SocialPlatform): string {
  const state = authFor(platform)?.state ?? 'not_logged_in'
  return `is-${state.replaceAll('_', '-')}`
}

function accountText(platform: SocialPlatform): string {
  const status = authFor(platform)
  if (!status) {
    return ''
  }
  if (status.account_name) {
    return status.account_name
  }
  if (status.logged_in) {
    return '登录态已保存'
  }
  return status.message
}

function expiryText(platform: SocialPlatform): string {
  const value = authFor(platform)?.expires_at
  if (!value) {
    return ''
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return ''
  }
  return `有效期至 ${new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed)}`
}

const showAuthHelp = computed(() => errorCode.value === 'platform_auth_required')
const resultMeta = computed(() => {
  if (!result.value) {
    return ''
  }
  const methodLabels: Record<typeof result.value.collection_method, string> = {
    public_api: '公开 API',
    browser_api: '浏览器原请求',
    browser_dom: '页面 DOM 兜底',
  }
  const authLabels: Record<typeof result.value.auth_mode, string> = {
    none: '匿名会话',
    cookie: 'Cookie 登录态',
    storage_state: '浏览器登录态',
  }
  return `${methodLabels[result.value.collection_method]} · ${authLabels[result.value.auth_mode]}`
})

const canSubmit = computed(() => url.value.trim().length > 0 && !loading.value)
const fullJobLabel = computed(() => {
  if (!fullJob.value) {
    return ''
  }
  const labels: Record<typeof fullJob.value.state, string> = {
    queued: '排队中',
    running: '正在采集',
    completed: '采集完成',
    failed: '采集失败',
    cancelled: '已取消',
  }
  return labels[fullJob.value.state]
})
const fullJobProgress = computed(() => fullJob.value?.progress ?? 0)

onMounted(() => {
  void loadPlatforms()
})

async function handleSubmit(): Promise<void> {
  if (!canSubmit.value) {
    return
  }
  await submit(url.value, maxComments.value)
}

async function handleFullCollection(): Promise<void> {
  const sourceUrl = result.value?.content.url || url.value
  if (sourceUrl) {
    await startFullJob(sourceUrl)
  }
}
</script>

<template>
  <div class="social-page">
    <header class="social-head">
      <p class="gn-eyebrow">Social ingestion</p>
      <h1 class="gn-serif">把社媒内容，<em>连评论一起取回来。</em></h1>
      <p class="social-head__lede">
        粘贴小红书、抖音或 Bilibili 的内容链接，自动提取标题、作者、热度数据和评论。
        只采集公开页面，不绕过登录或付费墙。
      </p>
    </header>

    <section v-if="platforms.length" class="platform-strip">
      <article v-for="item in platforms" :key="item.platform" class="platform-note">
        <div class="platform-note__head">
          <PlatformBadge :platform="item.platform" />
          <span class="platform-note__state" :class="authTone(item.platform)">
            {{ authLabel(item.platform) }}
          </span>
        </div>
        <p>{{ item.note }}</p>
        <p v-if="accountText(item.platform)" class="platform-note__account">
          {{ accountText(item.platform) }}
          <span v-if="expiryText(item.platform)"> · {{ expiryText(item.platform) }}</span>
        </p>
        <div class="platform-note__actions">
          <template v-if="authFor(item.platform)?.state === 'waiting'">
            <el-button size="small" disabled>等待登录…</el-button>
            <el-button
              size="small"
              link
              type="danger"
              :disabled="authActionPlatform === item.platform"
              @click="logoutPlatform(item.platform)"
            >
              取消
            </el-button>
          </template>
          <template v-else-if="authFor(item.platform)?.logged_in">
            <el-button
              size="small"
              link
              type="primary"
              :loading="authActionPlatform === item.platform"
              @click="switchAccount(item.platform)"
            >
              切换账号
            </el-button>
            <el-button
              size="small"
              link
              type="danger"
              :disabled="authActionPlatform === item.platform"
              @click="logoutPlatform(item.platform)"
            >
              退出
            </el-button>
          </template>
          <el-button
            v-else
            size="small"
            type="primary"
            plain
            :loading="authActionPlatform === item.platform"
            @click="loginPlatform(item.platform)"
          >
            登录
          </el-button>
        </div>
      </article>
    </section>

    <el-alert
      v-if="authNotice"
      class="auth-notice"
      :title="authNotice"
      type="info"
      :closable="false"
      show-icon
    />
    <el-alert
      v-if="authError"
      class="auth-notice"
      :title="authError"
      type="error"
      :closable="false"
      show-icon
    />

    <section class="social-form gn-card">
      <div class="social-form__head">
        <div>
          <p class="gn-eyebrow">Paste a link</p>
          <h2 class="gn-serif">内容 + 评论一次采集</h2>
        </div>
        <span class="social-form__supported">XHS / DY / BILI</span>
      </div>

      <el-input
        v-model="url"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 5 }"
        resize="none"
        maxlength="2000"
        placeholder="粘贴内容链接，或直接粘贴包含链接的分享文案……"
        @keydown.ctrl.enter.prevent="handleSubmit"
        @keydown.meta.enter.prevent="handleSubmit"
      />

      <div class="social-form__footer">
        <div class="social-form__limit">
          <span>抓取评论数</span>
          <el-select v-model="maxComments" size="small" style="width: 100px">
            <el-option :value="20" label="20 条" />
            <el-option :value="30" label="30 条" />
            <el-option :value="50" label="50 条" />
            <el-option :value="100" label="100 条" />
          </el-select>
        </div>
        <el-button type="primary" size="large" :loading="loading" :disabled="!canSubmit" @click="handleSubmit">
          获取内容与评论
        </el-button>
      </div>
    </section>

    <section v-if="error" class="social-error gn-card">
      <el-alert :title="error" type="warning" :closable="false" show-icon />
      <template v-if="showAuthHelp">
        <p class="social-error__label">完成平台登录后再试：</p>
        <code class="social-error__command">{{ errorHint || 'scripts\\social-login.bat xiaohongshu' }}</code>
        <p class="social-error__note">
          登录脚本会在本机打开 Edge，扫码完成后把登录态保存到本地，不会写入 Git。
        </p>
      </template>
      <p v-else-if="errorHint" class="social-error__note">{{ errorHint }}</p>
    </section>

    <section v-if="loading" class="social-loading gn-card">
      <div class="social-loading__head">
        <span class="social-loading__pulse" />
        <div>
          <p class="gn-eyebrow">Collecting</p>
          <h2 class="gn-serif">正在打开平台并抓取评论</h2>
          <p>抖音/小红书使用浏览器会话，通常需要 10–30 秒，请保持页面打开。</p>
        </div>
      </div>
      <LoadingSkeleton :rows="3" />
    </section>

    <template v-else-if="result">
      <div class="result-meta">
        <span>{{ resultMeta }}</span>
        <span>本次 {{ result.total_comments_fetched }} 条评论</span>
        <span v-if="result.content.content_id">ID {{ result.content.content_id }}</span>
      </div>

      <SocialContentCard :content="result.content" />

      <div v-if="result.warnings.length" class="social-warnings">
        <el-alert
          v-for="warning in result.warnings"
          :key="warning"
          :title="warning"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>

      <SocialCommentList
        :comments="result.comments"
        :has-more="result.has_more"
        :platform="result.platform"
        :content-id="result.content.content_id"
      />

      <section class="full-collection gn-card">
        <div class="full-collection__head">
          <div>
            <p class="gn-eyebrow">Full archive</p>
            <h2 class="gn-serif">评论全量采集与导出</h2>
            <p>
              当前只是预览。全量模式会在后台持续翻页/滚动，完成后可导出 Excel、Markdown 或 TXT；
              平台登录态、风控和评论总量会影响实际可获取数量。
            </p>
          </div>
          <el-button
            type="primary"
            plain
            :loading="fullJobLoading || fullJob?.state === 'running' || fullJob?.state === 'queued'"
            :disabled="fullJobLoading || fullJob?.state === 'running' || fullJob?.state === 'queued'"
            @click="handleFullCollection"
          >
            一键获取完整评论
          </el-button>
        </div>

        <div v-if="fullJob" class="full-collection__status">
          <div class="full-collection__line">
            <el-tag
              :type="fullJob.state === 'completed' ? 'success' : fullJob.state === 'failed' ? 'danger' : 'warning'"
              effect="light"
              round
            >
              {{ fullJobLabel }}
            </el-tag>
            <span>已抓取 {{ fullJob.total_fetched }} 条评论（含回复）</span>
          </div>
          <el-progress
            v-if="fullJob.state === 'queued' || fullJob.state === 'running'"
            :percentage="fullJobProgress"
            :stroke-width="6"
            :show-text="false"
          />
          <p v-if="fullJob.state === 'running' || fullJob.state === 'queued'" class="full-collection__hint">
            任务在后台运行，可以继续浏览页面；完成后下方会出现下载按钮。
          </p>
          <div v-if="fullJob.state === 'completed'" class="export-actions">
            <span>下载：</span>
            <a :href="fullJobExportUrl('xlsx')" download>Excel (.xlsx)</a>
            <a :href="fullJobExportUrl('md')" download>Markdown (.md)</a>
            <a :href="fullJobExportUrl('txt')" download>纯文本 (.txt)</a>
          </div>
          <el-alert
            v-if="fullJobError"
            :title="fullJobError"
            type="error"
            :closable="false"
            show-icon
          />
        </div>
      </section>
    </template>

    <EmptyState
      v-else-if="!error"
      title="还没有采集内容"
      description="从上面的输入框粘贴一条链接。Bilibili 与抖音可直接采集，小红书需要先完成登录。"
    />
  </div>
</template>

<style scoped>
.social-page {
  display: grid;
  gap: 20px;
  padding-top: 18px;
}

.social-head {
  max-width: 860px;
  padding: 8px 4px 2px;
}

.social-head h1 {
  margin: 10px 0 13px;
  font-size: clamp(42px, 6.3vw, 72px);
  font-weight: 700;
  letter-spacing: -0.07em;
  line-height: 1.03;
}

.social-head h1 em {
  color: var(--gn-accent);
  font-style: normal;
}

.social-head__lede {
  max-width: 700px;
  margin: 0;
  color: var(--gn-ink-soft);
  font-size: 14px;
  line-height: 1.8;
}

.platform-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.platform-note {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 7px;
  padding: 12px 14px;
  border: 1px solid var(--gn-border);
  border-radius: 12px;
  background: rgba(255, 253, 248, 0.55);
}

.platform-note__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.platform-note__state {
  padding: 3px 7px;
  border-radius: 999px;
  background: var(--gn-paper-deep);
  color: var(--gn-muted);
  font-size: 9px;
  white-space: nowrap;
}

.platform-note__state.is-logged-in {
  color: var(--gn-sage);
  background: var(--gn-sage-soft);
}

.platform-note__state.is-waiting {
  color: var(--gn-gold);
  background: var(--gn-gold-soft);
}

.platform-note__state.is-expired,
.platform-note__state.is-failed {
  color: var(--gn-accent);
  background: var(--gn-accent-soft);
}

.platform-note p {
  margin: 2px 0 0;
  color: var(--gn-muted);
  font-size: 10px;
  line-height: 1.55;
}

.platform-note p.platform-note__account {
  color: var(--gn-ink-soft);
  font-size: 9px;
}

.platform-note__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
  min-height: 28px;
  margin-top: auto;
}

.auth-notice {
  border-radius: 12px;
}

.social-form {
  padding: 24px;
}

.social-form__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 16px;
}

.social-form__head h2 {
  margin: 5px 0 0;
  font-size: 24px;
  letter-spacing: -0.035em;
}

.social-form__supported {
  color: var(--gn-muted);
  font-size: 9px;
  letter-spacing: 0.12em;
}

.social-form :deep(.el-textarea__inner) {
  padding: 14px;
  border-radius: 12px;
  border-color: var(--gn-border);
  background: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  line-height: 1.7;
}

.social-form__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-top: 14px;
}

.social-form__limit {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--gn-muted);
  font-size: 11px;
}

.social-form__footer :deep(.el-button) {
  min-width: 152px;
  border-radius: 11px;
}

.social-error {
  padding: 18px;
}

.social-error__label {
  margin: 14px 0 5px;
  color: var(--gn-ink-soft);
  font-size: 11px;
}

.social-error__command {
  display: inline-block;
  padding: 8px 11px;
  border-radius: 8px;
  background: var(--gn-ink);
  color: var(--gn-paper);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 11px;
  word-break: break-all;
}

.social-error__note {
  margin: 8px 0 0;
  color: var(--gn-muted);
  font-size: 10px;
  line-height: 1.65;
}

.social-loading {
  padding: 22px;
}

.social-loading__head {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.social-loading__head h2 {
  margin: 4px 0 4px;
  font-size: 21px;
  letter-spacing: -0.03em;
}

.social-loading__head p:last-child {
  margin: 0;
  color: var(--gn-muted);
  font-size: 11px;
}

.social-loading__pulse {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid var(--gn-accent-soft);
  border-top-color: var(--gn-accent);
  animation: spin 0.9s linear infinite;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  padding: 0 4px;
  color: var(--gn-muted);
  font-family: monospace;
  font-size: 9px;
}

.social-warnings {
  display: grid;
  gap: 8px;
}

.full-collection {
  padding: 22px 24px;
}

.full-collection__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.full-collection__head h2 {
  margin: 5px 0 5px;
  font-size: 22px;
  letter-spacing: -0.03em;
}

.full-collection__head p:last-child {
  max-width: 660px;
  margin: 0;
  color: var(--gn-muted);
  font-size: 11px;
  line-height: 1.65;
}

.full-collection__head :deep(.el-button) {
  flex: none;
  border-radius: 10px;
}

.full-collection__status {
  display: grid;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(222, 213, 198, 0.7);
}

.full-collection__line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--gn-ink-soft);
  font-size: 11px;
}

.full-collection__hint {
  margin: 0;
  color: var(--gn-muted);
  font-size: 10px;
}

.export-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--gn-muted);
  font-size: 11px;
}

.export-actions a {
  padding: 5px 10px;
  border: 1px solid var(--gn-border);
  border-radius: 8px;
  color: var(--gn-accent);
  font-weight: 600;
  text-decoration: none;
}

.export-actions a:hover {
  border-color: var(--gn-accent);
  background: var(--gn-accent-soft);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 800px) {
  .platform-strip {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .social-head h1 {
    font-size: 44px;
  }

  .social-form {
    padding: 18px;
  }

  .social-form__footer {
    flex-direction: column;
    align-items: stretch;
  }

  .social-form__footer :deep(.el-button) {
    width: 100%;
  }
}
</style>
