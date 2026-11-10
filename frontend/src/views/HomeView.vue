<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import FactCheckForm from '@/components/FactCheckForm.vue'
import FactCheckProgress from '@/components/FactCheckProgress.vue'
import FactCheckReport from '@/components/FactCheckReport.vue'
import HistoryStrip from '@/components/HistoryStrip.vue'
import { getGraphStats } from '@/api/health'
import { useFactCheck } from '@/composables/useFactCheck'
import type { GraphStats } from '@/types'

const route = useRoute()
const prefill = ref('')
const graphStats = ref<GraphStats | null>(null)

const {
  result,
  history,
  loading,
  detailLoading,
  historyLoading,
  error,
  activeStep,
  hasResult,
  submit,
  openRecord,
  loadHistory,
  dismissResult,
} = useFactCheck()

const pipelineSteps = [
  { index: '01', label: '抓取正文', text: 'Scrapy 调度，trafilatura 提取' },
  { index: '02', label: '拆解主张', text: '把文章拆成可独立核查的原子事实' },
  { index: '03', label: '检索证据', text: '多轮新闻搜索，带查询回跳' },
  { index: '04', label: '图谱校验', text: 'Neo4j 人工关系拦截过度推断' },
  { index: '05', label: '形成裁决', text: '输出可追溯结论与置信度' },
]

const graphSummary = computed(() => {
  if (!graphStats.value?.available) {
    return '图谱暂不可用'
  }
  return `${graphStats.value.entity_count} 实体 / ${graphStats.value.relation_count} 关系`
})

watch(
  () => route.query.url,
  (value) => {
    if (typeof value === 'string' && value.trim()) {
      prefill.value = value.trim()
    }
  },
  { immediate: true },
)

onMounted(() => {
  void loadHistory()
  void fetchGraphStats()
})

async function fetchGraphStats(): Promise<void> {
  try {
    graphStats.value = await getGraphStats()
  } catch {
    graphStats.value = null
  }
}

async function handleSubmit(content: string): Promise<void> {
  await submit(content)
}

async function handleHistoryOpen(id: string): Promise<void> {
  await openRecord(id)
  window.scrollTo({ top: 260, behavior: 'smooth' })
}

function handleReset(): void {
  dismissResult()
  prefill.value = ''
}
</script>

<template>
  <div class="home">
    <section class="hero">
      <div class="hero__copy">
        <p class="gn-eyebrow">Goodnews · Evidence before virality</p>
        <h1 class="gn-serif">
          先别转发，<br />
          <em>先核实。</em>
        </h1>
        <p class="hero__lede">
          粘贴一条新闻链接或一段文字。goodnews 会拆解可核查主张、检索交叉证据，
          再用人工确认的 Neo4j 图谱检查模型是否过度推断。
        </p>
        <div class="hero__facts">
          <span><b>5</b> 步状态图</span>
          <span><b>2</b> 轮证据回跳</span>
          <span><b>1</b> 条独立证据链</span>
        </div>
      </div>

      <div class="hero__note">
        <span class="hero__note-mark">“</span>
        <p>结论可以不确定，<br />但必须说清楚为什么。</p>
        <small>goodnews editorial principle</small>
      </div>
    </section>

    <div class="workspace">
      <div class="workspace__main">
        <FactCheckForm
          :initial-content="prefill"
          :loading="loading"
          @submit="handleSubmit"
        />

        <el-alert
          v-if="error"
          class="workspace__error"
          :title="error"
          type="error"
          :closable="false"
          show-icon
        />

        <FactCheckProgress v-if="loading" :active-step="activeStep" />

        <template v-else-if="detailLoading">
          <section class="detail-loading gn-card">
            <el-skeleton :rows="8" animated />
          </section>
        </template>

        <FactCheckReport
          v-else-if="hasResult && result"
          :result="result"
          @reset="handleReset"
        />
      </div>

      <aside class="workspace__side">
        <section class="pipeline gn-card">
          <p class="gn-eyebrow">The chain</p>
          <h2 class="gn-serif">一次核查，如何发生</h2>
          <ol class="pipeline__list">
            <li v-for="step in pipelineSteps" :key="step.index" class="pipeline__item">
              <span class="pipeline__index">{{ step.index }}</span>
              <div>
                <strong>{{ step.label }}</strong>
                <p>{{ step.text }}</p>
              </div>
            </li>
          </ol>
        </section>

        <section class="graph-brief gn-card">
          <p class="gn-eyebrow">Knowledge graph</p>
          <h2 class="gn-serif">人工校验图谱</h2>
          <p class="graph-brief__count">{{ graphSummary }}</p>
          <p class="graph-brief__text">
            图谱为空或没有命中关系时，系统只会返回“证据不足”，不会把模型猜测写成图谱事实。
          </p>
        </section>

        <HistoryStrip
          :items="history"
          :loading="historyLoading"
          @open="handleHistoryOpen"
        />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.home {
  display: grid;
  gap: 28px;
}

.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(250px, 0.6fr);
  align-items: end;
  gap: 40px;
  padding: 34px 4px 14px;
}

.hero__copy h1 {
  margin: 11px 0 16px;
  font-size: clamp(52px, 8vw, 100px);
  font-weight: 700;
  letter-spacing: -0.075em;
  line-height: 0.96;
}

.hero__copy h1 em {
  position: relative;
  color: var(--gn-accent);
  font-style: normal;
}

.hero__copy h1 em::after {
  content: '';
  position: absolute;
  left: 3px;
  right: -2px;
  bottom: 2px;
  height: 9px;
  z-index: -1;
  border-radius: 50%;
  background: var(--gn-accent-soft);
}

.hero__lede {
  max-width: 590px;
  margin: 0;
  color: var(--gn-ink-soft);
  font-size: 15px;
  line-height: 1.8;
}

.hero__facts {
  display: flex;
  flex-wrap: wrap;
  gap: 22px;
  margin-top: 25px;
  color: var(--gn-muted);
  font-size: 11px;
}

.hero__facts b {
  margin-right: 4px;
  color: var(--gn-accent);
  font-family: var(--gn-serif);
  font-size: 18px;
  font-weight: 700;
}

.hero__note {
  position: relative;
  padding: 26px 24px 22px;
  border-left: 2px solid var(--gn-accent);
  background: rgba(255, 253, 248, 0.55);
}

.hero__note-mark {
  position: absolute;
  top: -16px;
  left: 12px;
  color: var(--gn-accent-soft);
  font-family: Georgia, serif;
  font-size: 90px;
  line-height: 1;
}

.hero__note p {
  position: relative;
  margin: 20px 0 14px;
  font-family: var(--gn-serif);
  font-size: 22px;
  font-weight: 600;
  line-height: 1.55;
}

.hero__note small {
  color: var(--gn-muted);
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  align-items: start;
  gap: 22px;
}

.workspace__main,
.workspace__side {
  display: grid;
  gap: 18px;
}

.workspace__error {
  border-radius: 12px;
}

.detail-loading {
  padding: 28px;
}

.pipeline {
  padding: 22px;
}

.pipeline h2 {
  margin: 6px 0 18px;
  font-size: 22px;
  letter-spacing: -0.035em;
}

.pipeline__list {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.pipeline__item {
  display: grid;
  grid-template-columns: 30px 1fr;
  gap: 9px;
  padding: 10px 0;
  border-top: 1px solid rgba(222, 213, 198, 0.65);
}

.pipeline__index {
  color: var(--gn-accent);
  font-family: var(--gn-serif);
  font-size: 11px;
  font-weight: 700;
}

.pipeline__item strong {
  display: block;
  font-size: 12px;
  font-weight: 600;
}

.pipeline__item p {
  margin: 2px 0 0;
  color: var(--gn-muted);
  font-size: 10px;
  line-height: 1.55;
}

.graph-brief {
  padding: 22px;
  background: linear-gradient(150deg, rgba(63, 107, 84, 0.1), rgba(255, 253, 248, 0.86));
}

.graph-brief h2 {
  margin: 6px 0 10px;
  font-size: 21px;
  letter-spacing: -0.035em;
}

.graph-brief__count {
  margin: 0;
  color: var(--gn-sage);
  font-family: var(--gn-serif);
  font-size: 17px;
  font-weight: 700;
}

.graph-brief__text {
  margin: 8px 0 0;
  color: var(--gn-ink-soft);
  font-size: 11px;
  line-height: 1.7;
}

@media (max-width: 980px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 22px;
  }

  .hero__note {
    display: none;
  }

  .workspace {
    grid-template-columns: 1fr;
  }

  .workspace__side {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace__side > :last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 640px) {
  .hero {
    padding-top: 16px;
  }

  .hero__copy h1 {
    font-size: 56px;
  }

  .hero__facts {
    gap: 14px;
  }

  .workspace__side {
    grid-template-columns: 1fr;
  }

  .workspace__side > :last-child {
    grid-column: auto;
  }
}
</style>
