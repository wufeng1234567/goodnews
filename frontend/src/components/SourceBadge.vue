<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    sourceName?: string
    publishedAt?: string | null
    url?: string
  }>(),
  {
    sourceName: '',
    publishedAt: null,
    url: '',
  },
)

const domain = computed(() => {
  if (!props.url) {
    return ''
  }
  try {
    return new URL(props.url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
})

const displaySource = computed(() => props.sourceName || domain.value || '未知来源')

const formattedDate = computed(() => {
  if (!props.publishedAt) {
    return ''
  }
  const parsed = new Date(props.publishedAt)
  if (Number.isNaN(parsed.getTime())) {
    return props.publishedAt
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(parsed)
})
</script>

<template>
  <span class="source-badge">
    <span class="source-badge__name">{{ displaySource }}</span>
    <span v-if="formattedDate" class="source-badge__date">{{ formattedDate }}</span>
  </span>
</template>

<style scoped>
.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  max-width: 100%;
  color: var(--gn-muted);
  font-size: 11px;
  line-height: 1.4;
}

.source-badge__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--gn-ink-soft);
  font-weight: 600;
}

.source-badge__date::before {
  content: '·';
  margin-right: 7px;
  color: var(--gn-border);
}
</style>
