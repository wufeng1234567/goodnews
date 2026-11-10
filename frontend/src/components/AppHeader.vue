<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <header class="site-header">
    <div class="site-header__inner">
      <RouterLink class="brand" to="/" aria-label="goodnews 首页">
        <span class="brand__mark">g.</span>
        <span class="brand__text">
          <strong>goodnews</strong>
          <small>先核实，再转发</small>
        </span>
      </RouterLink>

      <nav class="nav" aria-label="主导航">
        <RouterLink class="nav__link" exact-active-class="is-active" to="/">核查台</RouterLink>
        <RouterLink class="nav__link" active-class="is-active" to="/explore">热点探索</RouterLink>
      </nav>

      <span class="status-pill">
        <span class="status-pill__dot" />
        MVP 在线
      </span>
    </div>
  </header>
</template>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 20;
  border-bottom: 1px solid rgba(222, 213, 198, 0.75);
  background: rgba(244, 239, 229, 0.86);
  backdrop-filter: blur(16px);
}

.site-header__inner {
  width: min(1180px, calc(100% - 40px));
  min-height: 76px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 36px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--gn-ink);
}

.brand__mark {
  width: 38px;
  height: 38px;
  border-radius: 12px 12px 12px 4px;
  background: var(--gn-ink);
  color: var(--gn-paper);
  font-family: var(--gn-serif);
  font-size: 24px;
  font-weight: 700;
  line-height: 36px;
  text-align: center;
  box-shadow: 5px 5px 0 var(--gn-accent-soft);
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.brand__text strong {
  font-family: var(--gn-serif);
  font-size: 21px;
  letter-spacing: -0.03em;
}

.brand__text small {
  margin-top: 3px;
  color: var(--gn-muted);
  font-size: 10px;
  letter-spacing: 0.14em;
}

.nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav__link {
  position: relative;
  padding: 8px 12px;
  border-radius: 999px;
  color: var(--gn-ink-soft);
  font-size: 14px;
  text-decoration: none;
  transition: background 0.18s ease, color 0.18s ease;
}

.nav__link:hover {
  background: rgba(255, 253, 248, 0.85);
}

.nav__link.is-active {
  color: var(--gn-accent);
  font-weight: 700;
}

.nav__link.is-active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 2px;
  width: 14px;
  height: 2px;
  border-radius: 2px;
  background: var(--gn-accent);
  transform: translateX(-50%);
}

.status-pill {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 10px;
  border: 1px solid var(--gn-border);
  border-radius: 999px;
  background: rgba(255, 253, 248, 0.7);
  color: var(--gn-muted);
  font-size: 11px;
  letter-spacing: 0.04em;
}

.status-pill__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gn-sage);
  box-shadow: 0 0 0 3px var(--gn-sage-soft);
}

@media (max-width: 720px) {
  .site-header__inner {
    width: calc(100% - 24px);
    min-height: 66px;
    gap: 14px;
  }

  .brand__text small,
  .status-pill {
    display: none;
  }

  .brand__mark {
    width: 34px;
    height: 34px;
    line-height: 32px;
  }

  .nav {
    margin-left: auto;
  }

  .nav__link {
    padding: 7px 9px;
    font-size: 13px;
  }
}
</style>
