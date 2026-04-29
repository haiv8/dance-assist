<template>
  <div class="record-shell">
    <div class="record-row-wrap">
      <label class="row-check" :class="{ disabled: !canDelete }" @click.stop>
        <input
          type="checkbox"
          :checked="selected"
          :disabled="!canDelete || bulkDeleting || deleting"
          @change="$emit('toggleSelection', item.pipelineId)"
        />
      </label>
      <button
        type="button"
        class="record-row dense-row issue-dense-row"
        :class="{ active }"
        @click="$emit('toggleIssue', item.id)"
      >
        <div class="dense-col primary-col">
          <strong>{{ issueTypeText(item.type) }}</strong>
          <p class="helper-text">{{ item.summary }}</p>
        </div>
        <div class="dense-col">
          <span class="tag" :class="severityTone(item.severity)">{{ severityText(item.severity) }}</span>
        </div>
        <div class="dense-col mono-col">{{ timeText(item.sec) }}</div>
        <div class="dense-col">
          <strong class="dense-name">{{ item.pairName || compactPipelineId(item.pipelineId) }}</strong>
          <span class="helper-text">{{ formatDate(item.finishedAt) }}</span>
        </div>
      </button>
    </div>

    <div v-if="active" class="inline-detail">
      <div class="panel-head compact-head">
        <div>
          <h2>问题回放</h2>
          <p class="helper-text">这里保留最短路径操作，方便马上回到所属记录或动作分析页。</p>
        </div>
        <div class="action-row">
          <button class="secondary-button" type="button" @click="$emit('openRecord', item)">打开所属记录</button>
          <button class="secondary-button" type="button" @click="$emit('jumpCompare', item)">定位到动作分析</button>
          <button class="ghost-button danger-button" type="button" :disabled="!canDelete || deleting" @click="$emit('deletePipeline', item.pipelineId)">
            {{ deleting ? "删除中..." : canDelete ? "删除记录" : "运行中不可删" }}
          </button>
        </div>
      </div>

      <div class="metric-row compact-stats">
        <div class="metric-chip"><strong>问题类型</strong><span>{{ issueTypeText(item.type) }}</span></div>
        <div class="metric-chip"><strong>定位时间</strong><span>{{ timeText(item.sec) }}</span></div>
        <div class="metric-chip"><strong>优先级</strong><span>{{ severityText(item.severity) }}</span></div>
      </div>

      <div class="list-item-card">
        <strong>所属记录评分</strong>
        <span class="helper-text">当前记录总分：{{ scoreText(item.scoreTotal) }}；可信度：{{ confidenceLevelText(item.confidenceScore) }}（{{ confidenceText(item.confidenceScore) }}）。</span>
        <span class="helper-text" v-if="isLowConfidence(item.confidenceScore)">该片段可能受跟踪质量影响，建议结合视频回看判断。</span>
      </div>

      <div class="list-item-card">
        <strong>问题摘要</strong>
        <span class="helper-text">{{ item.summary }}</span>
      </div>

      <div class="list-item-card" v-if="item.action">
        <strong>处理建议</strong>
        <span class="helper-text">{{ item.action }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { confidenceLevelText, isLowConfidence } from "../../composables/useScoreExplanation";
import { compactPipelineId } from "../../utils/display";
import type { IssueReplayItem } from "../../types/video";

defineProps<{
  item: IssueReplayItem;
  active: boolean;
  selected: boolean;
  canDelete: boolean;
  bulkDeleting: boolean;
  deleting: boolean;
}>();

defineEmits<{
  toggleIssue: [issueId: string];
  toggleSelection: [pipelineId: string];
  openRecord: [issue: IssueReplayItem];
  jumpCompare: [issue: IssueReplayItem];
  deletePipeline: [pipelineId: string];
}>();

function issueTypeText(value?: string) {
  if (value === "pose_error") return "动作误差";
  if (value === "tempo") return "节奏异常";
  if (value === "confidence") return "可信度风险";
  if (value === "tracking_bad") return "跟踪问题";
  return value || "待定";
}

function severityText(value?: string) {
  if (value === "high") return "高优先级";
  if (value === "medium") return "中优先级";
  return "低优先级";
}

function severityTone(value?: string) {
  if (value === "high") return "danger";
  if (value === "medium") return "warn";
  return "ok";
}

function confidenceText(value?: number | string | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return `${Math.round(num * 100)}%`;
}

function scoreText(value?: number | string | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return num.toFixed(1);
}

function timeText(sec?: number | null) {
  const num = Number(sec);
  if (!Number.isFinite(num)) return "--";
  return `${num.toFixed(2)}s`;
}

function formatDate(value?: string | null) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}
</script>

<style scoped>
.record-shell,
.inline-detail {
  display: grid;
  gap: 14px;
}

.record-row-wrap {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 10px;
  align-items: stretch;
}

.row-check {
  display: grid;
  place-items: center;
  min-height: 100%;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.76);
  cursor: pointer;
}

.row-check:hover:not(.disabled) {
  border-color: rgba(15, 143, 179, 0.28);
  background: rgba(232, 247, 252, 0.72);
}

.row-check.disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.row-check input {
  width: 18px;
  height: 18px;
  min-height: 18px;
  padding: 0;
  accent-color: var(--accent);
}

.dense-row {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) 140px 120px 220px;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.98);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

.dense-row:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(15, 143, 179, 0.22);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.04);
}

.dense-row.active {
  border-color: rgba(15, 143, 179, 0.32);
  background:
    radial-gradient(circle at top right, rgba(15, 143, 179, 0.1), transparent 32%),
    linear-gradient(180deg, rgba(248, 252, 255, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.dense-col {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.primary-col strong,
.dense-name {
  font-size: 1rem;
  line-height: 1.2;
}

.primary-col p,
.dense-col .helper-text {
  margin: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.mono-col {
  font-variant-numeric: tabular-nums;
}

.inline-detail {
  padding: 18px 20px 20px;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.compact-stats {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.danger-button {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.22);
}

.danger-button:hover:not(:disabled) {
  border-color: rgba(180, 35, 24, 0.4);
  background: rgba(180, 35, 24, 0.08);
}

@media (max-width: 1180px) {
  .dense-row {
    grid-template-columns: 1fr;
  }

  .record-row-wrap {
    grid-template-columns: 32px minmax(0, 1fr);
  }
}

@media (max-width: 1024px) {
  .compact-stats {
    grid-template-columns: 1fr;
  }
}
</style>
