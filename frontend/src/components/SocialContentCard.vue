<script setup lang="ts">
import { computed } from 'vue'
import PlatformBadge from './PlatformBadge.vue'
import type { SocialContent } from '@/types'

const props = defineProps<{
  content: SocialContent
}>()

interface MetricItem {
  label: string
  value: number
}

function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—'
  }
  if (value >= 100_000_000) {
    return `${(value / 100_000_000).toFixed(1).replace('.0', '')}亿`
  }
  if (value >= 10_000) {
    return `${(value / 10_000).toFixed(1).replace('.0', '')}万`
  }
  return new Intl.NumberFormat('zh-CN').format(value)
}

const metricItems = computed<MetricItem[]>(() => {
  const metrics = props.content.metrics
  const items: MetricItem[] = []
  const views = metrics.view_count ?? metrics.play_count
  if (views !== null) {
    items.push({ label: '播放/浏览', value: views })
  }
  if (metrics.like_count !== null) {
    items.push({ label: '点赞', value: metrics.like_count })
  }
  if (metrics.comment_count !== null) {
    items.push({ label: '评论', value: metrics.comment_count })
  }
  if (metrics.share_count !== null) {
    items.push({ label: '分享', value: metrics.share_count })
  }
  if (metrics.collect_count !== null) {
    items.push({ label: '收藏', value: metrics.collect_count })
  }
  if (metrics.coin_count) {
    items.push({ label: '投币', value: metrics.coin_count })
  }
  if (metrics.danmaku_count) {
    items.push({ label: '弹幕', value: metrics.danmaku_count })
  }
  return items
})

const publishedText = computed(() => {
  if (!props.content.published_at) {
    return '发布时间未提供'
  }
  const parsed = new Date(props.content.published_at)
  if (Number.isNaN(parsed.getTime())) {
    return props.content.published_at
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed)
})

const typeLabel = computed(() => {
  const labels: Record<SocialContent['content_type'], string> = {
    video: '视频',
    note: '图文笔记',
    article: '文章',
    unknown: '内容',
  }
  return labels[props.content.content_type]
})

const authorMeta = computed(() => {
  const author = props.content.author
  const parts: string[] = []
  if (author.handle) {
    parts.push(`@${author.handle}`)
  }
  if (author.follower_count !== null) {
    parts.push(`${formatCount(author.follower_count)} 粉丝`)
  }
  return parts.join(' · ')
})

const coverUrl = computed(() => props.content.cover_url || '')
const contentLink = computed(() => props.content.url)
</script>

<template>
  <article class="social-content gn-card">
    <div class="social-content__head">
      <div class="social-content__badges">
        <PlatformBadge :platform="content.platform" />
        <span class="social-content__type">{{ typeLabel }}</span>
        <span class="social-content__date">{{ publishedText }}</span>
      </div>
      <a
        class="social-content__open"
        :href="contentLink"
        target="_blank"
        rel="noopener noreferrer"
      >
        查看原内容 ↗
      </a>
    </div>

    <div class="social-content__body">
      <div class="social-content__main">
        <h2 class="gn-serif">{{ content.title }}</h2>
        <div class="social-content__author">
          <span class="social-content__avatar">{{ content.author.name.slice(0, 1) }}</span>
          <div>
            <strong>{{ content.author.name }}</strong>
            <p>{{ authorMeta || '作者信息未完整提供' }}</p>
          </div>
        </div>
        <p v-if="content.description" class="social-content__desc">{{ content.description }}</p>
        <div v-if="content.tags.length" class="social-content__tags">
          <span v-for="tag in content.tags.slice(0, 8)" :key="tag" class="social-content__tag">
            #{{ tag }}
          </span>
        </div>
      </div>

      <a
        v-if="coverUrl"
        class="social-content__cover"
        :href="contentLink"
        target="_blank"
        rel="noopener noreferrer"
      >
        <img :src="coverUrl" :alt="content.title" referrerpolicy="no-referrer" />
      </a>
    </div>

    <div class="social-content__metrics">
      <div v-for="metric in metricItems" :key="metric.label" class="metric">
        <strong>{{ formatCount(metric.value) }}</strong>
        <span>{{ metric.label }}</span>
      </div>
    </div>
  </article>
</template>

<style scoped>
.social-content {
  padding: 24px;
  overflow: hidden;
}

.social-content__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.social-content__badges {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.social-content__type,
.social-content__date {
  color: var(--gn-muted);
  font-size: 10px;
}

.social-content__type {
  padding-left: 8px;
  border-left: 1px solid var(--gn-border);
}

.social-content__open {
  flex: none;
  color: var(--gn-accent);
  font-size: 11px;
  font-weight: 600;
  text-decoration: none;
}

.social-content__body {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.social-content__main {
  min-width: 0;
  flex: 1;
}

.social-content__main h2 {
  margin: 0 0 14px;
  font-size: clamp(23px, 3vw, 32px);
  font-weight: 600;
  letter-spacing: -0.04em;
  line-height: 1.35;
}

.social-content__author {
  display: flex;
  align-items: center;
  gap: 10px;
}

.social-content__avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  flex: none;
  color: var(--gn-card);
  background: var(--gn-ink);
  font-family: var(--gn-serif);
  font-size: 16px;
}

.social-content__author strong {
  font-size: 12px;
  font-weight: 600;
}

.social-content__author p {
  margin: 2px 0 0;
  color: var(--gn-muted);
  font-size: 10px;
}

.social-content__desc {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 15px 0 0;
  color: var(--gn-ink-soft);
  font-size: 12px;
  line-height: 1.75;
  white-space: pre-wrap;
}

.social-content__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.social-content__tag {
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--gn-paper);
  color: var(--gn-muted);
  font-size: 10px;
}

.social-content__cover {
  flex: none;
  width: 190px;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border-radius: 14px;
  background: var(--gn-paper-deep);
}

.social-content__cover img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.social-content__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid rgba(222, 213, 198, 0.7);
}

.metric {
  min-width: 84px;
  padding: 0 18px;
  border-left: 1px solid var(--gn-border);
}

.metric:first-child {
  padding-left: 0;
  border-left: 0;
}

.metric strong {
  display: block;
  color: var(--gn-ink);
  font-family: var(--gn-serif);
  font-size: 20px;
  line-height: 1.1;
}

.metric span {
  display: block;
  margin-top: 3px;
  color: var(--gn-muted);
  font-size: 10px;
}

@media (max-width: 760px) {
  .social-content {
    padding: 18px;
  }

  .social-content__body {
    flex-direction: column-reverse;
    gap: 16px;
  }

  .social-content__cover {
    width: 100%;
    max-height: 220px;
  }

  .social-content__metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    row-gap: 14px;
  }

  .metric {
    padding-left: 0;
    border-left: 0;
  }
}
</style>
