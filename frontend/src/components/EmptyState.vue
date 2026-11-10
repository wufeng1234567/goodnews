<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    description?: string
  }>(),
  {
    title: '暂无内容',
    description: '',
  },
)
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__mark">○</div>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
  </div>
</template>

<style scoped>
.empty-state {
  padding: 58px 24px;
  border: 1px dashed var(--gn-border);
  border-radius: 16px;
  text-align: center;
  color: var(--gn-muted);
  background: rgba(255, 253, 248, 0.45);
}

.empty-state__mark {
  width: 44px;
  height: 44px;
  margin: 0 auto 14px;
  border: 1px solid var(--gn-border);
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--gn-accent);
  font-family: var(--gn-serif);
  font-size: 24px;
}

.empty-state h3 {
  margin: 0 0 6px;
  color: var(--gn-ink);
  font-family: var(--gn-serif);
  font-size: 18px;
  font-weight: 600;
}

.empty-state p {
  margin: 0;
  font-size: 13px;
}
</style>
