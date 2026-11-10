<script setup lang="ts">
import { computed } from 'vue'
import type { GraphMatch, GraphVerificationResult } from '@/types'

const props = defineProps<{
  graph: GraphVerificationResult
}>()

type TagType = 'success' | 'danger' | 'warning' | 'info'

const statusMeta = computed(() => {
  const map: Record<
    GraphVerificationResult['status'],
    { label: string; type: TagType; note: string }
  > = {
    supported: {
      label: '图谱支持',
      type: 'success',
      note: '找到人工确认的关系，与主张一致。',
    },
    contradicted: {
      label: '图谱冲突',
      type: 'danger',
      note: '人工确认关系与主张冲突，最终结论已被系统约束。',
    },
    insufficient: {
      label: '证据不足',
      type: 'info',
      note: '图谱未提供可确认关系，不会用图谱补写事实。',
    },
  }
  return map[props.graph.status]
})

function matchType(status: GraphMatch['status']): TagType {
  if (status === 'supported') {
    return 'success'
  }
  if (status === 'contradicted') {
    return 'danger'
  }
  return 'info'
}

function matchLabel(status: GraphMatch['status']): string {
  return status === 'supported' ? '一致' : status === 'contradicted' ? '冲突' : '无记录'
}

function predicateLabel(predicate: string): string {
  const labels: Record<string, string> = {
    located_in: '位于',
    headquartered_in: '总部位于',
    capital_of: '是首都',
    ceo_of: 'CEO 是',
    founded_by: '创立者是',
    member_of: '成员',
    launched_by: '发射方',
    discovered_by: '发现者',
    born_in: '出生于',
    has_nationality: '国籍',
    part_of: '属于',
  }
  return labels[predicate] ?? predicate
}
</script>

<template>
  <section class="graph-card gn-card">
    <div class="graph-card__head">
      <div>
        <p class="gn-eyebrow">Knowledge graph</p>
        <h3 class="gn-serif">图谱校验</h3>
      </div>
      <el-tag :type="statusMeta.type" effect="light" round>{{ statusMeta.label }}</el-tag>
    </div>

    <p class="graph-card__note">{{ statusMeta.note }}</p>
    <p class="graph-card__meta">
      图谱规模 {{ graph.graph_entities }} 实体 / {{ graph.graph_relations }} 关系 ·
      第 {{ graph.round }} 轮校验 · {{ graph.elapsed_ms }} ms
    </p>

    <div v-if="graph.matches.length" class="match-list">
      <div v-for="(match, index) in graph.matches" :key="`${match.claim_id}-${index}`" class="match">
        <div class="match__top">
          <span class="match__claim">{{ match.claim_id }}</span>
          <el-tag :type="matchType(match.status)" size="small" effect="plain">
            {{ matchLabel(match.status) }}
          </el-tag>
        </div>
        <p class="match__relation">
          <strong>{{ match.subject }}</strong>
          <span>{{ predicateLabel(match.predicate) }}</span>
          <strong>{{ match.claimed_object }}</strong>
        </p>
        <p v-if="match.graph_object && match.status === 'contradicted'" class="match__diff">
          图谱确认：{{ match.graph_object }}
        </p>
        <p v-if="match.note" class="match__note">{{ match.note }}</p>
      </div>
    </div>

    <p v-else class="graph-card__empty">本次没有命中任何已确认实体关系。</p>

    <ul v-if="graph.notes.length" class="graph-card__notes">
      <li v-for="note in graph.notes" :key="note">{{ note }}</li>
    </ul>
  </section>
</template>

<style scoped>
.graph-card {
  padding: 22px;
}

.graph-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.graph-card__head h3 {
  margin: 5px 0 0;
  font-size: 21px;
  letter-spacing: -0.03em;
}

.graph-card__note {
  margin: 14px 0 6px;
  color: var(--gn-ink-soft);
  font-size: 12px;
}

.graph-card__meta {
  margin: 0;
  color: var(--gn-muted);
  font-size: 10px;
}

.match-list {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.match {
  padding: 11px 12px;
  border-radius: 10px;
  background: var(--gn-paper);
}

.match__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.match__claim {
  color: var(--gn-muted);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.match__relation {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin: 7px 0 0;
  font-size: 12px;
}

.match__relation span {
  color: var(--gn-muted);
  font-size: 10px;
}

.match__relation strong {
  font-weight: 600;
}

.match__diff {
  margin: 5px 0 0;
  color: var(--gn-accent);
  font-size: 11px;
}

.match__note {
  margin: 5px 0 0;
  color: var(--gn-muted);
  font-size: 10px;
  line-height: 1.5;
}

.graph-card__empty {
  margin: 16px 0 0;
  color: var(--gn-muted);
  font-size: 12px;
}

.graph-card__notes {
  margin: 16px 0 0;
  padding: 12px 14px 12px 28px;
  border-top: 1px dashed var(--gn-border);
  color: var(--gn-muted);
  font-size: 10px;
  line-height: 1.7;
}
</style>
