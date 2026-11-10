<script setup lang="ts">
import { computed } from 'vue'
import ClaimList from './ClaimList.vue'
import EvidenceTimeline from './EvidenceTimeline.vue'
import GraphVerificationCard from './GraphVerificationCard.vue'
import SourceBadge from './SourceBadge.vue'
import TraceSteps from './TraceSteps.vue'
import VerdictCard from './VerdictCard.vue'
import type { FactCheckResponse } from '@/types'

const props = defineProps<{
  result: FactCheckResponse
}>()

defineEmits<{
  reset: []
}>()

const articleHost = computed(() => {
  if (!props.result.source_url) {
    return ''
  }
  try {
    return new URL(props.result.source_url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
})

const durationText = computed(() => `${(props.result.duration_ms / 1000).toFixed(1)} 秒`)
const fetchedWithLabel = computed(() => {
  const labels: Record<FactCheckResponse['article']['fetched_with'], string> = {
    input_text: '用户文本',
    scrapy: 'Scrapy 静态抓取',
    scrapy_playwright: 'Playwright 渲染抓取',
  }
  return labels[props.result.article.fetched_with]
})
const createdText = computed(() => {
  const parsed = new Date(props.result.created_at)
  if (Number.isNaN(parsed.getTime())) {
    return props.result.created_at
  }
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed)
})
</script>

<template>
  <article class="report">
    <header class="report__header">
      <div class="report__meta">
        <p class="gn-eyebrow">Report · {{ createdText }}</p>
        <h1 class="gn-serif">{{ result.article.title }}</h1>
        <div class="report__source">
          <SourceBadge
            :source-name="result.article.source_name || articleHost"
            :published-at="result.article.published_at"
            :url="result.source_url || ''"
          />
          <span>{{ result.article.word_count }} 字</span>
          <span>耗时 {{ durationText }}</span>
        </div>
      </div>
      <el-button class="report__reset" plain @click="$emit('reset')">新的核查</el-button>
    </header>

    <VerdictCard :verdict="result.verdict" :confidence="result.confidence" />

    <div v-if="result.warnings.length" class="report__warnings">
      <el-alert
        v-for="warning in result.warnings"
        :key="warning"
        :title="warning"
        type="warning"
        :closable="false"
        show-icon
      />
    </div>

    <section class="reasoning gn-card">
      <p class="gn-eyebrow">Reasoning</p>
      <h3 class="gn-serif">裁决理由</h3>
      <p class="reasoning__text">{{ result.reasoning }}</p>
    </section>

    <div class="report__grid">
      <div class="report__main">
        <ClaimList :claims="result.claims" />
        <EvidenceTimeline :items="result.evidence" :claims="result.claims" />
      </div>
      <aside class="report__side">
        <GraphVerificationCard :graph="result.graph_verification" />
        <TraceSteps :steps="result.trace" />
        <section class="article-source gn-card">
          <p class="gn-eyebrow">Source article</p>
          <h3 class="gn-serif">核查原文</h3>
          <p class="article-source__title">{{ result.article.title }}</p>
          <p class="article-source__meta">
            {{ result.article.author || '作者未标注' }} · {{ fetchedWithLabel }}
          </p>
          <a
            v-if="result.source_url"
            class="article-source__link"
            :href="result.source_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            打开原始链接 <span aria-hidden="true">↗</span>
          </a>
          <p v-else class="article-source__meta">本次为用户文本输入，无外部链接。</p>
        </section>
      </aside>
    </div>
  </article>
</template>

<style scoped>
.report {
  display: grid;
  gap: 18px;
}

.report__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 4px 2px 8px;
}

.report__header h1 {
  margin: 7px 0 8px;
  font-size: clamp(24px, 3.4vw, 36px);
  font-weight: 600;
  letter-spacing: -0.045em;
  line-height: 1.28;
}

.report__source {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  color: var(--gn-muted);
  font-size: 11px;
}

.report__reset {
  flex: none;
  border-radius: 999px;
}

.report__warnings {
  display: grid;
  gap: 8px;
}

.reasoning {
  padding: 24px;
}

.reasoning h3 {
  margin: 5px 0 10px;
  font-size: 21px;
  letter-spacing: -0.03em;
}

.reasoning__text {
  margin: 0;
  color: var(--gn-ink-soft);
  font-size: 13px;
  line-height: 1.85;
  white-space: pre-wrap;
}

.report__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(300px, 0.8fr);
  align-items: start;
  gap: 18px;
}

.report__main,
.report__side {
  display: grid;
  gap: 18px;
}

.article-source {
  padding: 22px;
}

.article-source h3 {
  margin: 5px 0 10px;
  font-size: 20px;
}

.article-source__title {
  margin: 0 0 4px;
  color: var(--gn-ink-soft);
  font-size: 13px;
  line-height: 1.55;
}

.article-source__meta {
  margin: 0;
  color: var(--gn-muted);
  font-size: 10px;
}

.article-source__link {
  display: inline-block;
  margin-top: 12px;
  color: var(--gn-accent);
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}

@media (max-width: 900px) {
  .report__grid {
    grid-template-columns: 1fr;
  }

  .report__side {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .report__header {
    flex-direction: column;
    gap: 12px;
  }

  .report__side {
    grid-template-columns: 1fr;
  }

  .reasoning {
    padding: 20px;
  }
}
</style>
