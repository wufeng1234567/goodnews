<script setup lang="ts">
import { computed } from 'vue'
import type { Verdict } from '@/types'

const props = defineProps<{
  verdict: Verdict
  confidence: number
}>()

interface VerdictTheme {
  label: string
  en: string
  caption: string
  tone: string
}

const themes: Record<Verdict, VerdictTheme> = {
  true: {
    label: '真实',
    en: 'TRUE',
    caption: '现有证据总体支持核心主张',
    tone: 'is-true',
  },
  false: {
    label: '虚假',
    en: 'FALSE',
    caption: '证据或人工确认图谱与主张相冲突',
    tone: 'is-false',
  },
  partially_true: {
    label: '部分属实',
    en: 'PARTIALLY TRUE',
    caption: '主张中仅部分信息获得证据支持',
    tone: 'is-partial',
  },
  insufficient_evidence: {
    label: '证据不足',
    en: 'INSUFFICIENT',
    caption: '暂时无法证实或证伪，请谨慎转发',
    tone: 'is-insufficient',
  },
}

const theme = computed(() => themes[props.verdict])
const confidencePercent = computed(() => Math.round(props.confidence * 100))
const gaugeBackground = computed(
  () =>
    `conic-gradient(var(--gn-accent) ${confidencePercent.value * 3.6}deg, var(--gn-paper-deep) 0deg)`,
)
</script>

<template>
  <section class="verdict-card" :class="theme.tone">
    <div class="verdict-card__main">
      <p class="verdict-card__eyebrow">Final verdict</p>
      <div class="verdict-card__headline">
        <span class="verdict-card__stamp">{{ theme.en }}</span>
        <h2 class="gn-serif">{{ theme.label }}</h2>
      </div>
      <p class="verdict-card__caption">{{ theme.caption }}</p>
    </div>

    <div class="confidence">
      <div class="confidence__gauge" :style="{ background: gaugeBackground }">
        <div class="confidence__inner">
          <strong>{{ confidencePercent }}<small>%</small></strong>
          <span>置信度</span>
        </div>
      </div>
      <p>模型与系统约束综合评分</p>
    </div>
  </section>
</template>

<style scoped>
.verdict-card {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  padding: 30px 34px;
  border: 1px solid var(--gn-border);
  border-radius: 22px;
  overflow: hidden;
  background: var(--gn-card);
  box-shadow: var(--gn-shadow);
}

.verdict-card::after {
  content: '';
  position: absolute;
  right: -70px;
  bottom: -90px;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: var(--tone-soft);
  opacity: 0.8;
}

.verdict-card__main {
  position: relative;
  z-index: 1;
}

.verdict-card__eyebrow {
  margin: 0 0 7px;
  color: var(--tone);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.verdict-card__headline {
  display: flex;
  align-items: center;
  gap: 14px;
}

.verdict-card__headline h2 {
  margin: 0;
  font-size: clamp(36px, 6vw, 62px);
  font-weight: 700;
  letter-spacing: -0.065em;
  line-height: 1;
}

.verdict-card__stamp {
  padding: 5px 9px;
  border: 1px solid var(--tone);
  border-radius: 5px;
  color: var(--tone);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  transform: rotate(-4deg);
}

.verdict-card__caption {
  margin: 12px 0 0;
  color: var(--gn-ink-soft);
  font-size: 13px;
}

.confidence {
  position: relative;
  z-index: 1;
  flex: none;
  text-align: center;
}

.confidence__gauge {
  width: 112px;
  height: 112px;
  padding: 8px;
  border-radius: 50%;
}

.confidence__inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--gn-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--gn-ink);
}

.confidence__inner strong {
  font-family: var(--gn-serif);
  font-size: 30px;
  line-height: 1;
}

.confidence__inner small {
  font-size: 14px;
  font-weight: 500;
}

.confidence__inner span {
  margin-top: 4px;
  color: var(--gn-muted);
  font-size: 10px;
}

.confidence p {
  margin: 8px 0 0;
  color: var(--gn-muted);
  font-size: 10px;
}

.is-true {
  --tone: var(--gn-sage);
  --tone-soft: var(--gn-sage-soft);
}

.is-false {
  --tone: var(--gn-accent);
  --tone-soft: var(--gn-accent-soft);
}

.is-partial {
  --tone: var(--gn-gold);
  --tone-soft: var(--gn-gold-soft);
}

.is-insufficient {
  --tone: #6f675d;
  --tone-soft: #e9e2d8;
}

@media (max-width: 640px) {
  .verdict-card {
    padding: 22px;
    align-items: flex-start;
    border-radius: 18px;
  }

  .confidence__gauge {
    width: 84px;
    height: 84px;
    padding: 6px;
  }

  .confidence__inner strong {
    font-size: 22px;
  }

  .confidence p {
    display: none;
  }

  .verdict-card__stamp {
    display: none;
  }
}
</style>
