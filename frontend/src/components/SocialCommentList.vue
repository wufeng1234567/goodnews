<script setup lang="ts">
import { computed } from 'vue'
import EmptyState from './EmptyState.vue'
import SocialCommentItem from './SocialCommentItem.vue'
import type { SocialComment, SocialPlatform } from '@/types'

const props = withDefaults(
  defineProps<{
    comments: SocialComment[]
    hasMore?: boolean
    platform?: SocialPlatform
    contentId?: string
  }>(),
  {
    hasMore: false,
  },
)

function countTree(items: SocialComment[]): number {
  return items.reduce((total, item) => total + 1 + countTree(item.replies), 0)
}

const totalCount = computed(() => countTree(props.comments))
</script>

<template>
  <section class="comment-list gn-card">
    <div class="section-head">
      <div>
        <p class="gn-eyebrow">Comments</p>
        <h2 class="gn-serif">评论区</h2>
      </div>
      <span class="section-head__count">{{ totalCount }} 条</span>
    </div>

    <EmptyState
      v-if="!comments.length"
      title="暂未获取到评论"
      description="平台可能要求登录、限制频率，或这条内容的评论区未公开。"
    />

    <div v-else class="comment-list__items">
      <SocialCommentItem
        v-for="comment in comments"
        :key="comment.id"
        :comment="comment"
        :platform="platform"
        :content-id="contentId"
      />
    </div>

    <p v-if="hasMore && comments.length" class="comment-list__more">
      评论区仍有更多内容未展示。
    </p>
  </section>
</template>

<style scoped>
.comment-list {
  padding: 24px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.section-head h2 {
  margin: 5px 0 0;
  font-size: 22px;
  letter-spacing: -0.03em;
}

.section-head__count {
  padding: 4px 9px;
  border-radius: 999px;
  background: var(--gn-paper);
  color: var(--gn-muted);
  font-size: 11px;
}

.comment-list__more {
  margin: 12px 0 0;
  padding-top: 12px;
  border-top: 1px dashed var(--gn-border);
  color: var(--gn-muted);
  font-size: 10px;
}
</style>
