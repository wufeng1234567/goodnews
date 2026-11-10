<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  activeStep: number
}>()

const stages = [
  { key: 'fetch_article', label: '抓取文章正文', hint: 'Scrapy + trafilatura' },
  { key: 'extract_claims', label: '拆解可核查主张', hint: 'DeepSeek 结构化抽取' },
  { key: 'retrieve_evidence', label: '检索交叉证据', hint: '新闻搜索 + 全文提取' },
  { key: 'graph_verify', label: '校验知识图谱', hint: 'Neo4j 人工关系' },
  { key: 'adjudicate', label: '形成最终裁决', hint: '证据 + 图谱双约束' },
]

const currentStage = computed(() => stages[Math.min(props.activeStep, stages.length - 1)])

function stageState(index: number): 'done' | 'active' | 'pending' {
  if (index < props.activeStep) {
    return 'done'
  }
  if (index === props.activeStep) {
    return 'active'
  }
  return 'pending'
}
</script>

<template>
  <section class="progress-card gn-card" aria-live="polite">
    <div class="progress-card__intro">
      <span class="progress-card__spinner" />
      <div>
        <p class="gn-eyebrow">Analyzing</p>
        <h2 class="gn-serif">正在核查，请稍候</h2>
        <p class="progress-card__current">{{ currentStage.label }} · {{ currentStage.hint }}</p>
      </div>
    </div>

    <ol class="stage-list">
      <li
        v-for="(stage, index) in stages"
        :key="stage.key"
        class="stage"
        :class="`is-${stageState(index)}`"
      >
        <span class="stage__index">{{ index + 1 }}</span>
        <div class="stage__body">
          <strong>{{ stage.label }}</strong>
          <small>{{ stage.hint }}</small>
        </div>
        <span class="stage__state">
          {{ stageState(index) === 'done' ? '完成' : stageState(index) === 'active' ? '进行中' : '等待' }}
        </span>
      </li>
    </ol>

    <p class="progress-card__note">
      同一时间只跑一条同步链路。若证据覆盖不足，系统会自动补检，最多 2 轮。
    </p>
  </section>
</template>

<style scoped>
.progress-card {
  padding: 26px;
  overflow: hidden;
}

.progress-card__intro {
  display: flex;
  gap: 18px;
  align-items: flex-start;
  padding-bottom: 22px;
  border-bottom: 1px dashed var(--gn-border);
}

.progress-card__intro h2 {
  margin: 5px 0 3px;
  font-size: 26px;
  letter-spacing: -0.03em;
}

.progress-card__current {
  margin: 0;
  color: var(--gn-muted);
  font-size: 13px;
}

.progress-card__spinner {
  flex: none;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 2px solid var(--gn-accent-soft);
  border-top-color: var(--gn-accent);
  animation: spin 0.9s linear infinite;
}

.stage-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
}

.stage {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 14px;
  padding: 15px 0;
  color: var(--gn-muted);
  border-bottom: 1px solid rgba(222, 213, 198, 0.55);
}

.stage:last-child {
  border-bottom: 0;
}

.stage__index {
  width: 30px;
  height: 30px;
  border: 1px solid var(--gn-border);
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
}

.stage__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stage__body strong {
  font-size: 14px;
  font-weight: 600;
}

.stage__body small {
  font-size: 11px;
}

.stage__state {
  font-size: 11px;
  letter-spacing: 0.04em;
}

.stage.is-active {
  color: var(--gn-ink);
}

.stage.is-active .stage__index {
  border-color: var(--gn-accent);
  background: var(--gn-accent);
  color: #fff;
  box-shadow: 0 0 0 5px var(--gn-accent-soft);
}

.stage.is-done {
  color: var(--gn-sage);
}

.stage.is-done .stage__index {
  border-color: var(--gn-sage);
  background: var(--gn-sage-soft);
  color: var(--gn-sage);
}

.progress-card__note {
  margin: 14px 0 0;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--gn-paper);
  color: var(--gn-muted);
  font-size: 11px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 600px) {
  .progress-card {
    padding: 20px;
    border-radius: 16px;
  }

  .stage {
    grid-template-columns: 30px 1fr;
  }

  .stage__state {
    display: none;
  }
}
</style>
