<script setup lang="ts">
import type { FactCheckHistoryItem, Verdict } from '@/types'

defineProps<{
  items: FactCheckHistoryItem[]
  loading?: boolean
}>()

defineEmits<{
  open: [id: string]
}>()

function verdictLabel(verdict: Verdict): string {
  const labels: Record<Verdict, string> = {
    true: '真实',
    false: '虚假',
    partially_true: '部分属实',
    insufficient_evidence: '证据不足',
  }
  return labels[verdict]
}

function verdictClass(verdict: Verdict): string {
  return `is-${verdict.replace('_', '-')}`
}

function shortDate(value: string): string {
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
</script>

<template>
  <section class="history gn-card">
    <div class="history__head">
      <div>
        <p class="gn-eyebrow">Recent checks</p>
        <h3 class="gn-serif">最近核查</h3>
      </div>
      <span v-if="items.length" class="history__count">{{ items.length }}</span>
    </div>

    <div v-if="loading" class="history__loading">读取历史中……</div>

    <div v-else-if="items.length" class="history__list">
      <button
        v-for="item in items"
        :key="item.id"
        class="history__item"
        type="button"
        @click="$emit('open', item.id)"
      >
        <span class="history__verdict" :class="verdictClass(item.verdict)">
          {{ verdictLabel(item.verdict) }}
        </span>
        <span class="history__preview">{{ item.input_preview }}</span>
        <span class="history__date">{{ shortDate(item.created_at) }}</span>
      </button>
    </div>

    <p v-else class="history__empty">还没有核查记录。完成一次核查后会显示在这里。</p>
  </section>
</template>

<style scoped>
.history {
  padding: 20px;
}

.history__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}

.history__head h3 {
  margin: 5px 0 0;
  font-size: 20px;
  letter-spacing: -0.03em;
}

.history__count {
  color: var(--gn-muted);
  font-size: 11px;
}

.history__list {
  display: grid;
  gap: 2px;
}

.history__item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 10px 0;
  border: 0;
  border-top: 1px solid rgba(222, 213, 198, 0.65);
  background: transparent;
  color: var(--gn-ink);
  text-align: left;
  cursor: pointer;
}

.history__item:hover .history__preview {
  color: var(--gn-accent);
}

.history__verdict {
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--gn-paper);
  color: var(--gn-muted);
  font-size: 9px;
  white-space: nowrap;
}

.history__verdict.is-true {
  background: var(--gn-sage-soft);
  color: var(--gn-sage);
}

.history__verdict.is-false {
  background: var(--gn-accent-soft);
  color: var(--gn-accent);
}

.history__verdict.is-partially-true {
  background: var(--gn-gold-soft);
  color: var(--gn-gold);
}

.history__preview {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  transition: color 0.18s ease;
}

.history__date {
  color: var(--gn-muted);
  font-size: 9px;
  white-space: nowrap;
}

.history__loading,
.history__empty {
  margin: 0;
  padding: 14px 0 4px;
  border-top: 1px solid rgba(222, 213, 198, 0.65);
  color: var(--gn-muted);
  font-size: 11px;
  line-height: 1.6;
}
</style>
