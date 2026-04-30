<template>
  <section class="confidence-banner" :data-tone="tone">
    <div class="confidence-icon" aria-hidden="true">{{ icon }}</div>
    <div class="confidence-copy">
      <strong>{{ title }}</strong>
      <span>{{ message }}</span>
    </div>
    <span class="confidence-score">{{ scoreText }}</span>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  confidenceScore?: number | string | null;
}>();

const score = computed(() => {
  const value = Number(props.confidenceScore);
  return Number.isFinite(value) ? value : null;
});

const tone = computed(() => {
  if (score.value === null) return "neutral";
  if (score.value >= 0.78) return "good";
  if (score.value >= 0.55) return "warning";
  return "danger";
});

const title = computed(() => {
  if (tone.value === "good") return "可信度较高";
  if (tone.value === "warning") return "可信度中等";
  if (tone.value === "danger") return "可信度较低";
  return "暂无可信度";
});

const message = computed(() => {
  if (tone.value === "good") return "本次分析可信度较高，可重点参考评分和问题片段。";
  if (tone.value === "warning") return "本次分析可信度中等，整体趋势可参考，局部片段建议结合视频回看。";
  if (tone.value === "danger") return "本次分析可信度较低，建议先检查拍摄角度、全身入镜、光照和遮挡情况。";
  return "暂无可信度信息，请结合视频和问题片段判断。";
});

const icon = computed(() => {
  if (tone.value === "good") return "✓";
  if (tone.value === "warning") return "!";
  if (tone.value === "danger") return "!";
  return "i";
});

const scoreText = computed(() => {
  if (score.value === null) return "--";
  return `${Math.round(score.value * 100)}%`;
});
</script>

<style scoped>
.confidence-banner {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.88);
}

.confidence-banner[data-tone="good"] {
  border-color: rgba(21, 128, 61, 0.2);
  background: rgba(240, 253, 244, 0.82);
}

.confidence-banner[data-tone="warning"] {
  border-color: rgba(226, 109, 61, 0.24);
  background: rgba(255, 247, 237, 0.82);
}

.confidence-banner[data-tone="danger"] {
  border-color: rgba(180, 35, 24, 0.22);
  background: rgba(254, 242, 242, 0.82);
}

.confidence-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--accent-dark);
  font-weight: 900;
}

.confidence-banner[data-tone="good"] .confidence-icon {
  color: #15803d;
}

.confidence-banner[data-tone="warning"] .confidence-icon {
  color: #b45309;
}

.confidence-banner[data-tone="danger"] .confidence-icon {
  color: #b42318;
}

.confidence-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.confidence-copy span {
  color: var(--muted);
  font-size: 0.9rem;
}

.confidence-score {
  font-weight: 900;
  color: var(--text);
}

@media (max-width: 720px) {
  .confidence-banner {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .confidence-score {
    grid-column: 2;
  }
}
</style>
