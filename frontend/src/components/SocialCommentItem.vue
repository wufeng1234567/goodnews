<script setup lang="ts">
import { computed } from 'vue'
import type { SocialComment } from '@/types'

const props = withDefaults(
  defineProps<{
    comment: SocialComment
    depth?: number
  }>(),
  {
    depth: 0,
  },
)

const isReply = computed(() => props.depth > 0)

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

      <div v-if="comment.replies.length" class="comment__replies">
        <SocialCommentItem
          v-for="reply in comment.replies"
          :key="reply.id"
          :comment="reply"
          :depth="depth + 1"
        />
      </div>
    </div>
  </article>
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

.comment.is-reply {
  border-top: 0;
}
</style>
