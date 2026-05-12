<template>
  <div class="list-item-card score-explain-card" v-if="scoreExplanation">
    <div class="record-title-row">
      <strong>如何看这个分数</strong>
      <InfoHint text="评分解释来自当前报告和问题片段，只用于确定复盘顺序，不会改写评分计算。" />
    </div>
    <span class="helper-text">{{ scoreExplanation.summary }}</span>
    <span class="helper-text">{{ scoreExplanation.next_action }}</span>
    <span class="helper-text">{{ scoreExplanation.score_note }}</span>
    <span class="helper-text" v-if="scoreExplanation.confidence_note">{{ scoreExplanation.confidence_note }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { scoreExplanationForDetail } from "../../composables/useScoreExplanation";
import InfoHint from "../InfoHint.vue";
import type { PipelineResultSummaryResponse, ScoreExplanation } from "../../types/video";

const props = defineProps<{
  detail: PipelineResultSummaryResponse | null;
  explanation?: ScoreExplanation | null;
  issueCount?: number;
}>();

const scoreExplanation = computed(() =>
  props.explanation || scoreExplanationForDetail(props.detail, props.issueCount || 0),
);
</script>

<style scoped>
.record-title-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
