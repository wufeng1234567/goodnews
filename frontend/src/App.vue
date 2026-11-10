<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
    <footer class="app-footer">
      <span>goodnews · 让判断慢一点，让证据快一点。</span>
      <span class="app-footer__meta">MVP / 无登录 / 同步链路</span>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding: 32px 0 72px;
}

.app-footer {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding: 24px 0 36px;
  border-top: 1px solid var(--gn-border);
  color: var(--gn-muted);
  font-size: 13px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.app-footer__meta {
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 11px;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 640px) {
  .app-main {
    width: min(100% - 24px, 1180px);
    padding-top: 20px;
  }

  .app-footer {
    width: min(100% - 24px, 1180px);
    flex-direction: column;
    gap: 6px;
  }
}
</style>
