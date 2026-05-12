<template>
  <section class="practice-trend-card">
    <div class="trend-card-head">
      <div>
        <span class="trend-eyebrow">进步趋势</span>
        <strong>{{ headline }}</strong>
      </div>
      <span class="trend-count">{{ points.length }} 次分析</span>
    </div>

    <div v-if="points.length < 2" class="trend-empty">
      <strong>趋势样本不足。</strong>
      <span>同一教师示范再完成一次练习后显示变化。</span>
    </div>

    <template v-else>
      <div class="trend-summary-grid">
        <div class="trend-metric">
          <span>最近一次分数</span>
          <strong>{{ formatScore(latestScore) }}</strong>
        </div>
        <div class="trend-metric">
          <span>最高分</span>
          <strong>{{ formatScore(bestScore) }}</strong>
        </div>
        <div class="trend-metric">
          <span>首次到最近</span>
          <strong :class="scoreDelta >= 0 ? 'positive' : 'negative'">{{ formatDelta(scoreDelta) }}</strong>
        </div>
        <div class="trend-metric">
          <span>问题变化</span>
          <strong :class="issueDelta <= 0 ? 'positive' : 'negative'">{{ formatIssueDelta(issueDelta) }}</strong>
        </div>
      </div>

      <div class="trend-bars" aria-label="练习趋势">
        <div v-for="series in seriesList" :key="series.key" class="trend-series">
          <div class="trend-series-label">
            <strong>{{ series.label }}</strong>
            <span>{{ series.note }}</span>
          </div>
          <div class="trend-bar-row">
            <span
              v-for="(value, index) in series.values"
              :key="`${series.key}_${index}`"
              class="trend-bar"
              :class="{ inverse: series.inverse }"
              :style="{ height: `${barHeight(value, series.inverse)}%` }"
              :title="`${series.label}: ${formatSeriesValue(series.displayValues[index], series.key)}`"
            ></span>
          </div>
        </div>
      </div>

      <div class="trend-notes">
        <span v-for="note in notes" :key="note" class="helper-text">{{ note }}</span>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { PracticeProjectTrendItem } from "../../types/video";

const props = defineProps<{
  trend: PracticeProjectTrendItem[];
}>();

const points = computed(() =>
  (props.trend || [])
    .filter((item) => item && (item.pipeline_id || item.finished_at))
    .map((item) => ({
      ...item,
      score_total: toNumber(item.score_total),
      score_pose: toNumber(item.score_pose),
      score_tempo: toNumber(item.score_tempo),
      confidence_score: toNumber(item.confidence_score),
      issue_count: Number.isFinite(Number(item.issue_count)) ? Number(item.issue_count) : 0,
    })),
);

const firstPoint = computed(() => points.value[0] || null);
const latestPoint = computed(() => points.value[points.value.length - 1] || null);
const latestScore = computed(() => latestPoint.value?.score_total ?? null);
const bestScore = computed(() => maxValue(points.value.map((item) => item.score_total)));
const scoreDelta = computed(() => (latestPoint.value?.score_total ?? 0) - (firstPoint.value?.score_total ?? 0));
const issueDelta = computed(() => (latestPoint.value?.issue_count ?? 0) - (firstPoint.value?.issue_count ?? 0));

const headline = computed(() => {
  if (points.value.length < 2) return "等待更多练习记录";
  if (scoreDelta.value > 0) return "最近一次较首次提升";
  if (scoreDelta.value < 0) return "最近一次低于首次";
  return "最近一次与首次持平";
});

const notes = computed(() => {
  const result: string[] = [headline.value];
  const confidence = latestPoint.value?.confidence_score;
  if (typeof confidence === "number" && confidence < 0.45) {
    result.push("最近可信度较低，建议结合视频回看。");
  }
  if (issueDelta.value < 0) {
    result.push("问题片段减少，保持当前练法。");
  } else if (issueDelta.value > 0) {
    result.push("问题片段增加，优先回看高优先级片段。");
  }
  return Array.from(new Set(result));
});

const seriesList = computed(() => [
  {
    key: "score_total",
    label: "总分",
    note: deltaNote(scoreDelta.value),
    values: points.value.map((item) => item.score_total),
    displayValues: points.value.map((item) => item.score_total),
    inverse: false,
  },
  {
    key: "score_pose",
    label: "动作分",
    note: deltaNote(deltaFor("score_pose")),
    values: points.value.map((item) => item.score_pose),
    displayValues: points.value.map((item) => item.score_pose),
    inverse: false,
  },
  {
    key: "score_tempo",
    label: "节奏分",
    note: deltaNote(deltaFor("score_tempo")),
    values: points.value.map((item) => item.score_tempo),
    displayValues: points.value.map((item) => item.score_tempo),
    inverse: false,
  },
  {
    key: "confidence_score",
    label: "可信度",
    note: deltaNote(deltaFor("confidence_score"), true),
    values: points.value.map((item) => item.confidence_score === null ? null : item.confidence_score * 100),
    displayValues: points.value.map((item) => item.confidence_score === null ? null : item.confidence_score * 100),
    inverse: false,
  },
  {
    key: "issue_count",
    label: "问题片段",
    note: issueDelta.value <= 0 ? "减少更好" : "有所增加",
    values: normalizeIssueCounts(points.value.map((item) => item.issue_count)),
    displayValues: points.value.map((item) => item.issue_count),
    inverse: true,
  },
]);

function toNumber(value: unknown): number | null {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function maxValue(values: Array<number | null>): number | null {
  const valid = values.filter((value): value is number => typeof value === "number");
  return valid.length ? Math.max(...valid) : null;
}

function deltaFor(key: "score_pose" | "score_tempo" | "confidence_score") {
  const first = firstPoint.value?.[key];
  const latest = latestPoint.value?.[key];
  if (typeof first !== "number" || typeof latest !== "number") return 0;
  const scale = key === "confidence_score" ? 100 : 1;
  return (latest - first) * scale;
}

function normalizeIssueCounts(values: number[]) {
  const max = Math.max(1, ...values);
  return values.map((value) => (value / max) * 100);
}

function barHeight(value: number | null, inverse = false) {
  if (value === null || !Number.isFinite(value)) return 8;
  const normalized = inverse ? 100 - value : value;
  return Math.max(8, Math.min(100, normalized));
}

function formatScore(value: number | null) {
  return typeof value === "number" ? value.toFixed(1) : "--";
}

function formatDelta(value: number) {
  if (!Number.isFinite(value)) return "--";
  if (Math.abs(value) < 0.05) return "0.0";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}`;
}

function formatIssueDelta(value: number) {
  if (!Number.isFinite(value)) return "--";
  if (value === 0) return "0";
  return `${value > 0 ? "+" : ""}${value}`;
}

function formatSeriesValue(value: number | null, key: string) {
  if (value === null || !Number.isFinite(value)) return "--";
  if (key === "issue_count") return `${Math.round(value)} 个`;
  return value.toFixed(1);
}

function deltaNote(value: number, confidence = false) {
  if (Math.abs(value) < 0.05) return "基本持平";
  const unit = confidence ? "%" : "分";
  return `${value > 0 ? "提升" : "下降"} ${Math.abs(value).toFixed(1)}${unit}`;
}
</script>

<style scoped>
.practice-trend-card {
  display: grid;
  gap: 14px;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid rgba(15, 143, 179, 0.14);
  background:
    radial-gradient(circle at top right, rgba(15, 143, 179, 0.1), transparent 34%),
    rgba(255, 255, 255, 0.9);
}

.trend-card-head,
.trend-summary-grid,
.trend-series {
  display: grid;
  gap: 10px;
}

.trend-card-head {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.trend-eyebrow,
.trend-metric span,
.trend-series-label span,
.trend-count {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.trend-eyebrow {
  display: block;
  letter-spacing: 0.08em;
}

.trend-count {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.78);
  white-space: nowrap;
}

.trend-empty {
  display: grid;
  gap: 4px;
  padding: 16px;
  border-radius: 14px;
  border: 1px dashed rgba(15, 23, 42, 0.16);
  color: var(--muted);
  background: rgba(248, 250, 252, 0.82);
}

.trend-empty strong {
  color: var(--text);
}

.trend-summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.trend-metric {
  display: grid;
  gap: 4px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(248, 250, 252, 0.84);
}

.trend-metric strong {
  font-size: 1.12rem;
}

.positive {
  color: #15803d;
}

.negative {
  color: #b42318;
}

.trend-bars {
  display: grid;
  gap: 12px;
}

.trend-series {
  grid-template-columns: 96px minmax(0, 1fr);
  align-items: end;
}

.trend-series-label {
  display: grid;
  gap: 2px;
}

.trend-bar-row {
  display: flex;
  align-items: end;
  gap: 7px;
  min-height: 82px;
  padding: 10px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(248, 250, 252, 0.74);
}

.trend-bar {
  width: 100%;
  min-width: 12px;
  max-width: 36px;
  min-height: 8px;
  border-radius: 999px 999px 6px 6px;
  background: linear-gradient(180deg, var(--accent) 0%, #eb8d56 100%);
}

.trend-bar.inverse {
  background: linear-gradient(180deg, #15803d 0%, var(--accent) 100%);
}

.trend-notes {
  display: grid;
  gap: 6px;
}

@media (max-width: 860px) {
  .trend-card-head,
  .trend-summary-grid,
  .trend-series {
    grid-template-columns: 1fr;
  }
}
</style>
