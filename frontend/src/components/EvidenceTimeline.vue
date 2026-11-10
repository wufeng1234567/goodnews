<script setup lang="ts">
import { computed } from 'vue'
import EmptyState from './EmptyState.vue'
import SourceBadge from './SourceBadge.vue'
import type { Claim, Evidence, EvidenceStance } from '@/types'

const props = defineProps<{
  items: Evidence[]
  claims: Claim[]
}>()

const claimLabels = computed(() => {
  const map = new Map<string, string>()
  props.claims.forEach((claim, index) => map.set(claim.id, `主张 ${index + 1}`))
  return map
})

function stanceLabel(stance: EvidenceStance): string {
  return stance === 'supports' ? '支持' : stance === 'refutes' ? '反驳' : '中性'
}

function stanceType(stance: EvidenceStance): 'success' | 'danger' | 'info' {
  return stance === 'supports' ? 'success' : stance === 'refutes' ? 'danger' : 'info'
}

function stanceColor(stance: EvidenceStance): string {
  return stance === 'supports' ? '#3f6b54' : stance === 'refutes' ? '#b8422d' : '#b4aa9b'
}

function claimText(claimId: string): string {
  return claimLabels.value.get(claimId) ?? claimId
}

function bodyText(item: Evidence): string {
  return item.content_excerpt || item.snippet || '该来源未提供摘要。'
}
</script>

<template>
  <section class="evidence gn-card">
    <div class="section-head">
      <div>
        <p class="gn-eyebrow">Evidence chain</p>
        <h3 class="gn-serif">证据时间线</h3>
      </div>
      <span class="section-head__count">{{ items.length }} 条</span>
    </div>

    <EmptyState
      v-if="!items.length"
      title="暂未检索到可用证据"
      description="结论会以“证据不足”处理，不会凭空补全事实。"
    />

    <el-timeline v-else class="evidence__timeline">
      <el-timeline-item
        v-for="(item, index) in items"
        :key="item.id"
        :color="stanceColor(item.stance)"
        :hollow="item.stance === 'neutral'"
        size="normal"
      >
        <article class="evidence-item">
          <div class="evidence-item__topline">
            <span class="evidence-item__index">E{{ String(index + 1).padStart(2, '0') }}</span>
            <el-tag :type="stanceType(item.stance)" size="small" effect="light" round>
              {{ stanceLabel(item.stance) }}
            </el-tag>
            <span class="evidence-item__claims">
              {{ item.claim_ids.map(claimText).join(' / ') }}
            </span>
          </div>

          <a
            class="evidence-item__title"
            :href="item.url"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ item.title }}
            <span aria-hidden="true">↗</span>
          </a>

          <p class="evidence-item__snippet">{{ bodyText(item) }}</p>

          <div class="evidence-item__foot">
            <SourceBadge
              :source-name="item.source_name"
              :published-at="item.published_at"
              :url="item.url"
            />
            <span class="evidence-item__relevance">
              相关度 {{ Math.round(item.relevance * 100) }}%
            </span>
          </div>
        </article>
      </el-timeline-item>
    </el-timeline>
  </section>
</template>

<style scoped>
.evidence {
  padding: 24px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.section-head h3 {
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

.evidence__timeline {
  padding-left: 4px;
}

.evidence__timeline :deep(.el-timeline-item__node) {
  box-shadow: 0 0 0 4px var(--gn-card);
}

.evidence__timeline :deep(.el-timeline-item__tail) {
  border-left-color: var(--gn-border);
}

.evidence-item {
  padding: 2px 0 6px;
}

.evidence-item__topline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.evidence-item__index {
  color: var(--gn-muted);
  font-family: var(--gn-serif);
  font-size: 11px;
  letter-spacing: 0.04em;
}

.evidence-item__claims {
  color: var(--gn-muted);
  font-size: 10px;
}

.evidence-item__title {
  display: inline-block;
  margin-top: 9px;
  color: var(--gn-ink);
  font-family: var(--gn-serif);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.45;
  text-decoration: none;
}

.evidence-item__title:hover {
  color: var(--gn-accent);
}

.evidence-item__title span {
  color: var(--gn-accent);
  font-family: var(--gn-sans);
  font-size: 12px;
}

.evidence-item__snippet {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 8px 0 10px;
  color: var(--gn-ink-soft);
  font-size: 12px;
  line-height: 1.75;
}

.evidence-item__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.evidence-item__relevance {
  flex: none;
  color: var(--gn-muted);
  font-size: 10px;
}
</style>
