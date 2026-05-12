<template>
  <section class="list-item-card priority-review-card">
    <div class="priority-head">
      <div>
        <strong>本次优先复盘</strong>
        <span class="helper-text">先回放高风险片段。</span>
      </div>
      <span class="tag neutral">{{ priorityItems.length }} 项</span>
    </div>

    <span v-if="lowConfidence" class="priority-warning">
      可信度较低，结合视频回看。
    </span>

    <div v-if="!priorityItems.length" class="priority-empty">
      暂无片段，完成分析后自动列入。
    </div>

    <div v-else class="priority-list">
      <article v-for="item in priorityItems" :key="item.id" class="priority-item">
        <div class="priority-meta">
          <span>{{ timeText(item.sec) }}</span>
          <span>{{ severityText(item.severity) }}</span>
          <span>{{ issueTypeText(item.type) }}</span>
        </div>
        <strong>{{ item.summary || "片段待确认，先回看视频。" }}</strong>
        <span class="helper-text">{{ item.action || fallbackAction(item.type) }}</span>
        <button type="button" class="secondary-button priority-jump" @click="$emit('jumpIssue', item)">
          跳转回放
        </button>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { isLowConfidence } from "../../composables/useScoreExplanation";
import type { IssueReplayItem } from "../../types/video";

const props = defineProps<{
  issues: IssueReplayItem[];
  confidenceScore?: number | string | null;
}>();

defineEmits<{
  jumpIssue: [issue: IssueReplayItem];
}>();

const severityRank: Record<string, number> = { high: 0, medium: 1, low: 2 };

const priorityItems = computed(() => {
  const valid = (props.issues || []).filter((item) => item && item.summary && item.type && Number.isFinite(Number(item.sec)));
  const high = valid.filter((item) => item.severity === "high");
  const medium = valid.filter((item) => item.severity === "medium");
  const source = high.length >= 3 ? high : [...high, ...medium];
  const fallback = source.length ? source : valid;
  return [...fallback]
    .sort((a, b) => {
      const severityDelta = (severityRank[a.severity] ?? 9) - (severityRank[b.severity] ?? 9);
      if (severityDelta !== 0) return severityDelta;
      return Number(a.sec) - Number(b.sec);
    })
    .slice(0, 5);
});

const lowConfidence = computed(() => isLowConfidence(props.confidenceScore));

function issueTypeText(value?: string) {
  const type = String(value || "").trim();
  if (type === "pose" || type === "pose_error") return "动作误差";
  if (type === "tempo" || type === "tempo_fast" || type === "tempo_slow") return "节奏异常";
  if (type === "confidence" || type === "quality") return "可信度风险";
  if (type === "tracking" || type === "tracking_bad" || type === "tracking_issue") return "跟踪问题";
  return value || "待定";
}

function severityText(value?: string) {
  if (value === "high") return "高优先级";
  if (value === "medium") return "中优先级";
  if (value === "low") return "低优先级";
  return "待确认";
}

function fallbackAction(type?: string) {
  const normalized = String(type || "").trim();
  if (normalized === "tempo" || normalized === "tempo_fast" || normalized === "tempo_slow") {
    return "慢速回放进入和结束，对齐节拍。";
  }
  if (
    normalized === "confidence" ||
    normalized === "quality" ||
    normalized === "tracking" ||
    normalized === "tracking_bad" ||
    normalized === "tracking_issue"
  ) {
    return "检查入镜、遮挡和光照，再确认评分可信度。";
  }
  return "慢速拆解，再串联完整片段。";
}

function timeText(sec?: number | null) {
  const num = Number(sec);
  if (!Number.isFinite(num)) return "--";
  return `${num.toFixed(2)}s`;
}
</script>

<style scoped>
.priority-review-card,
.priority-list,
.priority-item {
  display: grid;
  gap: 12px;
}

.priority-review-card {
  border-color: rgba(226, 109, 61, 0.2);
  background:
    radial-gradient(circle at top right, rgba(226, 109, 61, 0.12), transparent 32%),
    rgba(255, 255, 255, 0.92);
}

.priority-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.priority-head .helper-text {
  display: block;
  margin-top: 4px;
}

.priority-warning {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(180, 35, 24, 0.18);
  background: rgba(254, 242, 242, 0.72);
  color: #b42318;
  font-weight: 700;
}

.priority-empty {
  padding: 14px;
  border-radius: 12px;
  border: 1px dashed rgba(15, 23, 42, 0.14);
  color: var(--muted);
  background: rgba(248, 250, 252, 0.78);
}

.priority-item {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  background: rgba(248, 250, 252, 0.82);
}

.priority-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.priority-meta span {
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.76);
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 800;
}

.priority-jump {
  justify-self: start;
}
</style>
