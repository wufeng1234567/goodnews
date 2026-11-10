<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    initialContent?: string
    loading?: boolean
  }>(),
  {
    initialContent: '',
    loading: false,
  },
)

const emit = defineEmits<{
  submit: [content: string]
}>()

const content = ref(props.initialContent)

watch(
  () => props.initialContent,
  (value) => {
    content.value = value
  },
)

const isProbableUrl = computed(() => {
  const value = content.value.trim()
  if (!value || /\s/.test(value)) {
    return false
  }
  try {
    const parsed = new URL(value)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
})

const inputHint = computed(() =>
  isProbableUrl.value ? '已识别为链接，将抓取正文后核查' : '按文本内容核查，贴入报道全文效果更好',
)

const canSubmit = computed(() => content.value.trim().length > 0 && !props.loading)

function handleSubmit(): void {
  if (!canSubmit.value) {
    return
  }
  emit('submit', content.value.trim())
}

function handleKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <section class="input-card gn-card">
    <div class="input-card__head">
      <div>
        <p class="gn-eyebrow">Fact-check workbench</p>
        <h2 class="gn-serif">把新闻放进来，证据链交给我们。</h2>
      </div>
      <span class="input-card__limit">≤ 50,000 字</span>
    </div>

    <el-input
      v-model="content"
      class="input-card__textarea"
      type="textarea"
      :autosize="{ minRows: 6, maxRows: 12 }"
      maxlength="50000"
      show-word-limit
      resize="none"
      placeholder="粘贴新闻链接，或直接贴入一段需要核查的文字……"
      @keydown="handleKeydown"
    />

    <div class="input-card__footer">
      <div class="input-card__hint">
        <span class="input-card__pulse" />
        {{ inputHint }}
      </div>
      <div class="input-card__actions">
        <span class="input-card__shortcut">Ctrl / ⌘ + Enter</span>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          :disabled="!canSubmit"
          @click="handleSubmit"
        >
          开始核查
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.input-card {
  padding: 26px;
  background:
    linear-gradient(135deg, rgba(255, 253, 248, 0.96), rgba(255, 250, 240, 0.92));
}

.input-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.input-card__head h2 {
  margin: 7px 0 0;
  font-size: clamp(22px, 2.5vw, 30px);
  font-weight: 600;
  letter-spacing: -0.035em;
  line-height: 1.3;
}

.input-card__limit {
  flex: none;
  padding: 4px 9px;
  border-radius: 999px;
  background: var(--gn-paper);
  color: var(--gn-muted);
  font-size: 11px;
}

.input-card__textarea :deep(.el-textarea__inner) {
  min-height: 170px !important;
  padding: 18px 18px 30px;
  border: 1px solid var(--gn-border);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--gn-ink);
  font-family: var(--gn-sans);
  font-size: 15px;
  line-height: 1.8;
  box-shadow: inset 0 1px 3px rgba(76, 57, 34, 0.04);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.input-card__textarea :deep(.el-textarea__inner:focus) {
  border-color: var(--gn-accent);
  box-shadow: 0 0 0 4px rgba(184, 66, 45, 0.08);
}

.input-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-top: 18px;
}

.input-card__hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--gn-muted);
  font-size: 12px;
}

.input-card__pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gn-sage);
  box-shadow: 0 0 0 4px var(--gn-sage-soft);
}

.input-card__actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.input-card__shortcut {
  color: var(--gn-muted);
  font-size: 11px;
  letter-spacing: 0.02em;
}

.input-card__actions :deep(.el-button) {
  min-width: 132px;
  height: 44px;
  border-radius: 12px;
  box-shadow: 0 8px 18px rgba(184, 66, 45, 0.2);
}

@media (max-width: 700px) {
  .input-card {
    padding: 20px;
    border-radius: 16px;
  }

  .input-card__footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .input-card__actions {
    width: 100%;
    justify-content: space-between;
  }

  .input-card__shortcut {
    display: none;
  }

  .input-card__actions :deep(.el-button) {
    width: 100%;
  }
}
</style>
