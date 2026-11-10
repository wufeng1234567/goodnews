<script setup lang="ts">
import type { NodeStatus, TraceStep } from '@/types'

defineProps<{
  steps: TraceStep[]
}>()

function statusLabel(status: NodeStatus): string {
  const labels: Record<NodeStatus, string> = {
    pending: '等待',
    running: '进行中',
    completed: '完成',
    failed: '失败',
    skipped: '跳过',
  }
  return labels[status]
}
</script>

<template>
  <details class="trace gn-card">
    <summary class="trace__summary">
      <div>
        <p class="gn-eyebrow">Pipeline trace</p>
        <h3 class="gn-serif">处理轨迹</h3>
      </div>
      <span class="trace__toggle">{{ steps.length }} 步 · 展开</span>
    </summary>

    <ol class="trace__list">
      <li v-for="step in steps" :key="`${step.sequence}-${step.node}`" class="trace__item">
        <span class="trace__dot" :class="`is-${step.status}`" />
        <div class="trace__body">
          <div class="trace__line">
            <strong>{{ step.label }}</strong>
            <span>{{ step.duration_ms }} ms</span>
          </div>
          <p>{{ step.detail }}</p>
        </div>
        <span class="trace__status">{{ statusLabel(step.status) }}</span>
      </li>
    </ol>
  </details>
</template>

<style scoped>
.trace {
  padding: 18px 22px;
}

.trace__summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  list-style: none;
}

.trace__summary::-webkit-details-marker {
  display: none;
}

.trace__summary h3 {
  margin: 5px 0 0;
  font-size: 20px;
  letter-spacing: -0.03em;
}

.trace__toggle {
  margin-top: 4px;
  color: var(--gn-muted);
  font-size: 10px;
}

.trace[open] .trace__toggle {
  font-size: 0;
}

.trace[open] .trace__toggle::after {
  content: '收起';
  font-size: 10px;
}

.trace__list {
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
}

.trace__item {
  display: grid;
  grid-template-columns: 10px 1fr auto;
  align-items: start;
  gap: 10px;
  padding: 10px 0;
  border-top: 1px solid rgba(222, 213, 198, 0.6);
}

.trace__dot {
  width: 7px;
  height: 7px;
  margin-top: 7px;
  border-radius: 50%;
  background: var(--gn-muted);
}

.trace__dot.is-completed {
  background: var(--gn-sage);
}

.trace__dot.is-failed {
  background: var(--gn-accent);
}

.trace__dot.is-running {
  background: var(--gn-gold);
}

.trace__body {
  min-width: 0;
}

.trace__line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.trace__line strong {
  font-size: 12px;
  font-weight: 600;
}

.trace__line span {
  flex: none;
  color: var(--gn-muted);
  font-size: 9px;
}

.trace__body p {
  margin: 3px 0 0;
  color: var(--gn-muted);
  font-size: 10px;
  line-height: 1.55;
}

.trace__status {
  color: var(--gn-muted);
  font-size: 9px;
}
</style>
