<script setup lang="ts">
withDefaults(
  defineProps<{
    rows?: number
  }>(),
  {
    rows: 3,
  },
)
</script>

<template>
  <div class="skeleton" aria-label="加载中" aria-busy="true">
    <div v-for="row in rows" :key="row" class="skeleton__row">
      <span class="skeleton__rank" />
      <div class="skeleton__body">
        <span class="skeleton__title" :style="{ width: `${72 - row * 8}%` }" />
        <span class="skeleton__line" />
        <span class="skeleton__line skeleton__line--short" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton {
  display: grid;
  gap: 10px;
}

.skeleton__row {
  display: flex;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--gn-border);
  border-radius: 14px;
  background: rgba(255, 253, 248, 0.7);
}

.skeleton__rank {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: var(--gn-paper-deep);
}

.skeleton__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.skeleton__title,
.skeleton__line {
  display: block;
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--gn-paper-deep), #f8f3ea, var(--gn-paper-deep));
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}

.skeleton__title {
  height: 16px;
}

.skeleton__line {
  width: 92%;
}

.skeleton__line--short {
  width: 54%;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
