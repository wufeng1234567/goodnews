<script setup lang="ts">
import type { Claim, Verdict } from '@/types'

defineProps<{
  claims: Claim[]
}>()

type TagType = 'success' | 'danger' | 'warning' | 'info'

function verdictLabel(verdict: Verdict | null): string {
  const labels: Record<Verdict, string> = {
    true: '真实',
    false: '虚假',
    partially_true: '部分属实',
    insufficient_evidence: '证据不足',
  }
  return verdict ? labels[verdict] : '待判断'
}

function verdictTagType(verdict: Verdict | null): TagType {
  if (verdict === 'true') {
    return 'success'
  }
  if (verdict === 'false') {
    return 'danger'
  }
  if (verdict === 'partially_true') {
    return 'warning'
  }
  return 'info'
}

function importanceLabel(importance: Claim['importance']): string {
  return importance === 'high' ? '核心' : importance === 'low' ? '次要' : '重要'
}

function confidenceText(confidence: number | null): string {
  return confidence === null ? '未评分' : `${Math.round(confidence * 100)}%`
}
</script>

<template>
  <section class="claim-list gn-card">
    <div class="section-head">
      <div>
        <p class="gn-eyebrow">Atomic claims</p>
        <h3 class="gn-serif">逐条主张</h3>
      </div>
      <span class="section-head__count">{{ claims.length }} 条</span>
    </div>

    <article v-for="(claim, index) in claims" :key="claim.id" class="claim">
      <div class="claim__topline">
        <span class="claim__number">{{ String(index + 1).padStart(2, '0') }}</span>
        <el-tag :type="verdictTagType(claim.verdict)" effect="light" round size="small">
          {{ verdictLabel(claim.verdict) }}
        </el-tag>
        <span class="claim__importance">{{ importanceLabel(claim.importance) }}</span>
        <span class="claim__confidence">{{ confidenceText(claim.confidence) }}</span>
      </div>
      <p class="claim__text">{{ claim.text }}</p>
      <p v-if="claim.reasoning" class="claim__reasoning">{{ claim.reasoning }}</p>
      <div v-if="claim.entities.length || claim.evidence_ids.length" class="claim__meta">
        <span v-if="claim.entities.length">实体：{{ claim.entities.join(' / ') }}</span>
        <span v-if="claim.evidence_ids.length">引用证据：{{ claim.evidence_ids.join(' · ') }}</span>
      </div>
    </article>

    <p v-if="!claims.length" class="claim-list__empty">没有抽取到可独立核查的主张。</p>
  </section>
</template>

<style scoped>
.claim-list {
  padding: 24px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
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

.claim {
  padding: 18px 0;
  border-top: 1px solid rgba(222, 213, 198, 0.7);
}

.claim__topline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.claim__number {
  color: var(--gn-muted);
  font-family: var(--gn-serif);
  font-size: 12px;
}

.claim__importance,
.claim__confidence {
  color: var(--gn-muted);
  font-size: 10px;
}

.claim__importance {
  padding-left: 7px;
  border-left: 1px solid var(--gn-border);
}

.claim__confidence {
  margin-left: auto;
}

.claim__text {
  margin: 11px 0 6px;
  color: var(--gn-ink);
  font-family: var(--gn-serif);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.55;
}

.claim__reasoning {
  margin: 0;
  color: var(--gn-ink-soft);
  font-size: 12px;
  line-height: 1.7;
}

.claim__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin-top: 9px;
  color: var(--gn-muted);
  font-size: 10px;
}

.claim-list__empty {
  margin: 20px 0 6px;
  color: var(--gn-muted);
  font-size: 13px;
}
</style>
