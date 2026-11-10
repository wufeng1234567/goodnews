<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/EmptyState.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import SearchResultCard from '@/components/SearchResultCard.vue'
import { useNewsSearch } from '@/composables/useNewsSearch'
import type { SearchResultItem } from '@/types'

const router = useRouter()
const query = ref('')

const {
  hotItems,
  results,
  loading,
  hotLoading,
  error,
  provider,
  hasSearched,
  loadHot,
  search,
} = useNewsSearch()

const items = computed(() => (hasSearched.value ? results.value : hotItems.value))
const isBusy = computed(() => loading.value || hotLoading.value)
const listTitle = computed(() => (hasSearched.value ? '搜索结果' : '今日热点'))
const listHint = computed(() =>
  hasSearched.value
    ? `关键词「${query.value.trim() || '...'}」`
    : '来自公开新闻 RSS，点击标题看原文，点击“核查这条”进入分析。',
)

onMounted(() => {
  void loadHot()
})

async function handleSearch(): Promise<void> {
  await search(query.value)
}

function handleFactCheck(item: SearchResultItem): void {
  void router.push({ name: 'home', query: { url: item.url } })
}
</script>

<template>
  <div class="explore">
    <header class="explore-head">
      <p class="gn-eyebrow">News radar</p>
      <h1 class="gn-serif">今天，<em>发生了什么？</em></h1>
      <p class="explore-head__lede">
        先看热点，再挑一条值得核实的新闻。搜索不是终点，信息探索才是。
      </p>
    </header>

    <section class="search-box gn-card">
      <el-input
        v-model="query"
        class="search-box__input"
        size="large"
        placeholder="搜索新闻关键词，例如：人工智能、台风、某条热搜……"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <span class="search-box__icon">⌕</span>
        </template>
      </el-input>
      <el-button type="primary" size="large" :loading="loading" @click="handleSearch">
        搜索新闻
      </el-button>
    </section>

    <div class="list-head">
      <div>
        <p class="gn-eyebrow">{{ hasSearched ? 'Search results' : 'Trending now' }}</p>
        <h2 class="gn-serif">{{ listTitle }}</h2>
        <p>{{ listHint }}</p>
      </div>
      <span v-if="provider" class="list-head__provider">{{ provider }}</span>
    </div>

    <el-alert
      v-if="error"
      class="explore__error"
      :title="error"
      type="warning"
      :closable="false"
      show-icon
    />

    <LoadingSkeleton v-if="isBusy" :rows="4" />

    <div v-else-if="items.length" class="result-list">
      <SearchResultCard
        v-for="item in items"
        :key="item.id"
        :item="item"
        show-rank
        @action="handleFactCheck"
      />
    </div>

    <EmptyState
      v-else
      :title="hasSearched ? '没有找到相关新闻' : '热点暂时没有加载出来'"
      :description="
        hasSearched
          ? '换一个更短、更具体的关键词再试，或者直接去核查台粘贴链接。'
          : '可以直接搜索关键词，或去核查台粘贴一篇待核实文章。'
      "
    />

    <section class="explore-foot">
      <span class="explore-foot__line" />
      <p>新闻会过期，证据链不会。每一条核查都保留来源、时间与推理过程。</p>
    </section>
  </div>
</template>

<style scoped>
.explore {
  display: grid;
  gap: 24px;
  padding-top: 24px;
}

.explore-head {
  max-width: 780px;
  padding: 10px 4px 4px;
}

.explore-head h1 {
  margin: 10px 0 12px;
  font-size: clamp(45px, 7vw, 80px);
  font-weight: 700;
  letter-spacing: -0.07em;
  line-height: 1;
}

.explore-head h1 em {
  color: var(--gn-accent);
  font-style: normal;
}

.explore-head__lede {
  margin: 0;
  color: var(--gn-ink-soft);
  font-size: 15px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 18px;
}

.search-box__input {
  flex: 1;
}

.search-box__input :deep(.el-input__wrapper) {
  min-height: 48px;
  padding: 0 14px;
  border: 0;
  box-shadow: none;
  background: transparent;
}

.search-box__input :deep(.el-input__inner) {
  font-size: 14px;
}

.search-box__icon {
  color: var(--gn-accent);
  font-family: var(--gn-serif);
  font-size: 24px;
}

.search-box :deep(.el-button) {
  flex: none;
  height: 46px;
  padding: 0 24px;
  border-radius: 12px;
}

.list-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 8px 4px 0;
}

.list-head h2 {
  margin: 5px 0 4px;
  font-size: 27px;
  letter-spacing: -0.04em;
}

.list-head p:last-child {
  margin: 0;
  color: var(--gn-muted);
  font-size: 11px;
}

.list-head__provider {
  color: var(--gn-muted);
  font-family: monospace;
  font-size: 10px;
}

.explore__error {
  border-radius: 12px;
}

.result-list {
  display: grid;
  gap: 10px;
}

.explore-foot {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 20px 4px;
  color: var(--gn-muted);
  font-size: 11px;
}

.explore-foot__line {
  flex: 1;
  height: 1px;
  background: var(--gn-border);
}

.explore-foot p {
  margin: 0;
}

@media (max-width: 640px) {
  .explore {
    padding-top: 10px;
  }

  .explore-head h1 {
    font-size: 48px;
  }

  .search-box {
    align-items: stretch;
    flex-direction: column;
  }

  .search-box :deep(.el-button) {
    width: 100%;
  }

  .list-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }

  .explore-foot {
    align-items: flex-start;
  }

  .explore-foot__line {
    display: none;
  }
}
</style>
