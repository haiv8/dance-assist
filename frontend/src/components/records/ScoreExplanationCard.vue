<template>
  <div class="list-item-card score-explain-card" v-if="scoreExplanation">
    <strong>如何看这个分数</strong>
    <span class="helper-text">{{ scoreExplanation.summary }}</span>
    <span class="helper-text">{{ scoreExplanation.next_action }}</span>
    <span class="helper-text">{{ scoreExplanation.score_note }}</span>
    <span class="helper-text" v-if="scoreExplanation.confidence_note">{{ scoreExplanation.confidence_note }}</span>
    <span class="helper-text">动作分看空间姿态接近程度，节奏分看快慢和转场时机，可信度看姿态跟踪是否稳定。</span>
    <span class="helper-text">AI 助教只解释已生成的结构化报告，不参与动作评分计算。</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { scoreExplanationForDetail } from "../../composables/useScoreExplanation";
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
