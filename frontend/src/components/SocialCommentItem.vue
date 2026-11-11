<script setup lang="ts">
import { computed, ref } from 'vue'
import { fetchSocialReplies } from '@/api/social'
import { toApiError } from '@/api/client'
import type { SocialComment, SocialPlatform } from '@/types'

const props = withDefaults(
  defineProps<{
    comment: SocialComment
    depth?: number
    platform?: SocialPlatform
    contentId?: string
  }>(),
  {
    depth: 0,
  },
)

const isReply = computed(() => props.depth > 0)
const visibleReplies = computed(() => props.comment.replies.slice(0, 3))
const replyTotal = computed(() =>
  Math.max(props.comment.reply_count || 0, props.comment.replies.length),
)
const hasMoreReplies = computed(() => replyTotal.value > 3)
const dialogVisible = ref(false)
const loadingReplies = ref(false)
const replyError = ref('')
const dialogReplies = ref<SocialComment[]>([])

function formatCount(value: number): string {
  if (value >= 10_000) {
    return `${(value / 10_000).toFixed(1).replace('.0', '')}万`
  }
  return String(value)
}

function formatDate(value: string | null): string {
  if (!value) {
    return ''
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return ''
  }
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed)
}

const initial = computed(() => props.comment.author_name.slice(0, 1) || '匿')

async function openReplies(): Promise<void> {
  dialogVisible.value = true
  replyError.value = ''
  dialogReplies.value = props.comment.replies
  const declared = props.comment.reply_count || 0
  if (
    props.platform === 'bilibili' &&
    props.contentId &&
    declared > props.comment.replies.length
  ) {
    loadingReplies.value = true
    try {
      const response = await fetchSocialReplies(
        props.platform,
        props.contentId,
        props.comment.id,
      )
      dialogReplies.value = response.replies
    } catch (caught: unknown) {
      replyError.value = toApiError(caught).message
    } finally {
      loadingReplies.value = false
    }
  }
}
</script>

<template>
  <article class="comment" :class="{ 'is-reply': isReply }">
    <div class="comment__avatar">{{ initial }}</div>
    <div class="comment__body">
      <div class="comment__head">
        <strong>{{ comment.author_name }}</strong>
        <span v-if="comment.created_at" class="comment__date">
          {{ formatDate(comment.created_at) }}
        </span>
      </div>
      <p class="comment__text">{{ comment.text }}</p>
      <div class="comment__meta">
        <span>赞 {{ formatCount(comment.like_count) }}</span>
        <span v-if="comment.reply_count">回复 {{ formatCount(comment.reply_count) }}</span>
      </div>

      <div v-if="visibleReplies.length" class="comment__replies">
        <SocialCommentItem
          v-for="reply in visibleReplies"
          :key="reply.id"
          :comment="reply"
          :depth="depth + 1"
          :platform="platform"
          :content-id="contentId"
        />
      </div>
      <button
        v-if="hasMoreReplies"
        type="button"
        class="comment__more"
        @click="openReplies"
      >
        查看更多回复（{{ formatCount(replyTotal) }}）
      </button>
    </div>
  </article>

  <el-dialog
    v-model="dialogVisible"
    :title="`${comment.author_name} 的完整评论`"
    width="min(760px, 92vw)"
    append-to-body
    class="reply-dialog"
  >
    <div class="reply-dialog__scroll">
      <div class="reply-dialog__parent">
        <div class="reply-dialog__parent-head">
          <strong>{{ comment.author_name }}</strong>
          <span>{{ formatDate(comment.created_at) }}</span>
        </div>
        <p>{{ comment.text }}</p>
        <div class="reply-dialog__parent-meta">
          <span>赞 {{ formatCount(comment.like_count) }}</span>
          <span>回复 {{ formatCount(comment.reply_count) }}</span>
        </div>
      </div>

      <div class="reply-dialog__heading">
        <span>全部子回复</span>
        <span v-if="loadingReplies">加载中…</span>
        <span v-else>{{ dialogReplies.length }} 条已加载</span>
      </div>
      <div v-if="dialogReplies.length" class="reply-dialog__list">
        <SocialCommentItem
          v-for="reply in dialogReplies"
          :key="reply.id"
          :comment="reply"
          :depth="1"
          :platform="platform"
          :content-id="contentId"
        />
      </div>
      <p v-else class="reply-dialog__empty">暂无已加载的子回复。</p>
      <p v-if="loadingReplies" class="reply-dialog__loading">正在加载完整子回复…</p>
      <p v-if="replyError" class="reply-dialog__error">{{ replyError }}</p>
      <p
        v-else-if="!loadingReplies && replyTotal > dialogReplies.length"
        class="reply-dialog__note"
      >
        平台回复总数约 {{ formatCount(replyTotal) }} 条，当前仅加载
        {{ dialogReplies.length }} 条。可使用“一键获取完整评论”后台任务导出完整数据。
      </p>
    </div>
  </el-dialog>
</template>

<style scoped>
.comment {
  display: flex;
  gap: 11px;
  padding: 14px 0;
  border-top: 1px solid rgba(222, 213, 198, 0.62);
}

.comment__avatar {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--gn-ink-soft);
  background: var(--gn-paper-deep);
  font-family: var(--gn-serif);
  font-size: 13px;
}

.comment__body {
  min-width: 0;
  flex: 1;
}

.comment__head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.comment__head strong {
  color: var(--gn-ink-soft);
  font-size: 11px;
  font-weight: 600;
}

.comment__date {
  color: var(--gn-muted);
  font-size: 9px;
}

.comment__text {
  margin: 5px 0 0;
  color: var(--gn-ink);
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.comment__meta {
  display: flex;
  gap: 14px;
  margin-top: 5px;
  color: var(--gn-muted);
  font-size: 9px;
}

.comment__replies {
  margin-top: 7px;
  padding-left: 12px;
  border-left: 1px solid var(--gn-border);
}

.comment__replies :deep(.comment) {
  padding: 9px 0;
}

.comment__replies :deep(.comment__avatar) {
  width: 24px;
  height: 24px;
  font-size: 11px;
}

.comment__more {
  margin-top: 7px;
  padding: 0;
  border: 0;
  color: var(--gn-accent);
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 10px;
  font-weight: 600;
}

.comment__more:hover {
  text-decoration: underline;
}

.comment.is-reply {
  border-top: 0;
}

.reply-dialog__scroll {
  height: 62vh;
  overflow-y: auto;
  padding-right: 4px;
}

.reply-dialog__parent {
  padding: 14px 16px;
  border: 1px solid var(--gn-border);
  border-radius: 10px;
  background: var(--gn-paper);
}

.reply-dialog__parent-head,
.reply-dialog__parent-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--gn-muted);
  font-size: 10px;
}

.reply-dialog__parent-head strong {
  color: var(--gn-ink);
  font-size: 12px;
}

.reply-dialog__parent p {
  margin: 8px 0;
  color: var(--gn-ink);
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.reply-dialog__parent-meta {
  gap: 14px;
  font-size: 9px;
}

.reply-dialog__heading {
  display: flex;
  justify-content: space-between;
  margin: 18px 0 4px;
  color: var(--gn-ink-soft);
  font-size: 11px;
  font-weight: 600;
}

.reply-dialog__heading span:last-child {
  color: var(--gn-muted);
  font-size: 9px;
  font-weight: 400;
}

.reply-dialog__list {
  padding-left: 4px;
}

.reply-dialog__list :deep(.comment) {
  padding: 10px 0;
}

.reply-dialog__empty,
.reply-dialog__loading,
.reply-dialog__note {
  margin: 12px 0;
  color: var(--gn-muted);
  font-size: 11px;
}

.reply-dialog__error {
  margin: 12px 0;
  color: var(--gn-accent);
  font-size: 11px;
}
</style>
