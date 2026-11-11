<script setup lang="ts">
import { computed } from 'vue'
import type { SocialPlatform } from '@/types'

const props = defineProps<{
  platform: SocialPlatform
}>()

const meta = computed(() => {
  const values: Record<SocialPlatform, { label: string; tone: string }> = {
    xiaohongshu: { label: '小红书', tone: 'is-xhs' },
    douyin: { label: '抖音', tone: 'is-douyin' },
    bilibili: { label: 'Bilibili', tone: 'is-bilibili' },
  }
  return values[props.platform]
})
</script>

<template>
  <span class="platform-badge" :class="meta.tone">{{ meta.label }}</span>
</template>

<style scoped>
.platform-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.is-xhs {
  color: #b51f31;
  background: #fbe9eb;
}

.is-douyin {
  color: #111;
  background: #ececec;
}

.is-bilibili {
  color: #1676a8;
  background: #e5f3fa;
}
</style>
