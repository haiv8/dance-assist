<template>
  <div class="list-item-card ai-record-card" v-if="aiCoach || aiCoachError">
    <div class="record-card-head">
      <strong>AI 助教解读</strong>
      <span v-if="aiCoach" class="tag neutral">{{ sourceText }}</span>
    </div>
    <span v-if="aiCoachError" class="helper-text">{{ aiCoachError }}</span>
    <template v-if="aiCoach">
      <span class="helper-text">{{ aiCoach.summary }}</span>
      <div class="issue-chip-list" v-if="aiCoach.priority_issues.length">
        <button
          v-for="issue in aiCoach.priority_issues.slice(0, 3)"
          :key="`${issue.title}_${issue.time_hint}`"
          type="button"
          class="issue-chip"
        >
          {{ issue.time_hint ? `${issue.time_hint} · ` : "" }}{{ issue.title }}
        </button>
      </div>
      <span class="helper-text" v-if="aiCoach.practice_plan[0]">
        建议先练：{{ aiCoach.practice_plan[0].title }}，{{ aiCoach.practice_plan[0].duration_min }} 分钟。
      </span>
      <span class="helper-text" v-if="fallbackHint">{{ fallbackHint }}</span>
      <span class="helper-text" v-if="aiCoach.setup_hint">{{ aiCoach.setup_hint }}</span>
      <span class="helper-text">AI 解读基于已生成的分析报告，不参与动作评分。</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { AiCoachResponse } from "../../types/video";

defineProps<{
  aiCoach: AiCoachResponse | null;
  aiCoachError: string;
  sourceText: string;
  fallbackHint: string;
}>();
</script>

<style scoped>
.ai-record-card {
  border-color: rgba(15, 143, 179, 0.18);
  background:
    radial-gradient(circle at top right, rgba(15, 143, 179, 0.12), transparent 32%),
    rgba(255, 255, 255, 0.9);
}

.record-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.issue-chip-list {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.issue-chip {
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.94);
  color: var(--text);
  padding: 0.78rem 0.88rem;
  box-shadow: none;
  text-transform: none;
  letter-spacing: 0;
  font-size: 0.86rem;
  font-weight: 700;
}

@media (max-width: 1024px) {
  .issue-chip-list {
    grid-template-columns: 1fr;
  }
}
</style>
