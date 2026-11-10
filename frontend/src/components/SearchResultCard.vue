<script setup lang="ts">
import SourceBadge from './SourceBadge.vue'
import type { SearchResultItem } from '@/types'

withDefaults(
  defineProps<{
    item: SearchResultItem
    showRank?: boolean
    actionLabel?: string
  }>(),
  {
    showRank: false,
    actionLabel: '核查这条',
  },
)

defineEmits<{
  action: [item: SearchResultItem]
}>()
</script>

<template>
  <article class="result-card">
    <span v-if="showRank" class="result-card__rank">{{ String(item.rank).padStart(2, '0') }}</span>
    <div class="result-card__body">
      <div class="result-card__meta">
        <SourceBadge
          :source-name="item.source_name"
          :published-at="item.published_at"
          :url="item.url"
        />
      </div>
      <a
        class="result-card__title"
        :href="item.url"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ item.title }}
        <span aria-hidden="true">↗</span>
      </a>
      <p v-if="item.snippet" class="result-card__snippet">{{ item.snippet }}</p>
    </div>
    <el-button class="result-card__action" plain size="small" @click="$emit('action', item)">
      {{ actionLabel }}
    </el-button>
  </article>
</template>

<style scoped>
.result-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--gn-border);
  border-radius: 16px;
  background: rgba(255, 253, 248, 0.78);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.result-card:hover {
  transform: translateY(-2px);
  border-color: #cbbfae;
  box-shadow: 0 12px 28px rgba(76, 57, 34, 0.08);
}

.result-card__rank {
  flex: none;
  width: 34px;
  padding-top: 1px;
  color: var(--gn-accent);
  font-family: var(--gn-serif);
  font-size: 16px;
  font-weight: 700;
}

.result-card__body {
  min-width: 0;
  flex: 1;
}

.result-card__meta {
  margin-bottom: 6px;
}

.result-card__title {
  color: var(--gn-ink);
  font-family: var(--gn-serif);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.45;
  text-decoration: none;
}

.result-card__title:hover {
  color: var(--gn-accent);
}

.result-card__title span {
  color: var(--gn-accent);
  font-family: var(--gn-sans);
  font-size: 11px;
}

.result-card__snippet {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 7px 0 0;
  color: var(--gn-ink-soft);
  font-size: 12px;
  line-height: 1.7;
}

.result-card__action {
  flex: none;
  align-self: center;
  border-radius: 999px;
}

@media (max-width: 640px) {
  .result-card {
    flex-wrap: wrap;
    padding: 16px;
  }

  .result-card__rank {
    width: 24px;
  }

  .result-card__body {
    flex-basis: calc(100% - 44px);
  }

  .result-card__action {
    margin-left: 40px;
  }
}
</style>
