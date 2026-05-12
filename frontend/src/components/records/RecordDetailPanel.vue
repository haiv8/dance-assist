<template>
  <div class="inline-detail">
    <div class="panel-head compact-head detail-panel-head">
      <div>
        <span class="detail-eyebrow">{{ item.pair_name || item.pipeline_id }}</span>
        <h2>记录详情</h2>
        <p class="helper-text">取消、删除、导出或继续复盘。</p>
      </div>
      <div class="action-row detail-actions">
        <button class="ghost-button" :disabled="!canCancel || canceling" @click="$emit('cancel')">
          {{ canceling ? "取消中..." : "取消任务" }}
        </button>
        <button class="ghost-button danger-button" :disabled="!canDelete || deleting" @click="$emit('delete')">
          {{ deleting ? "删除中..." : "删除记录" }}
        </button>
        <button class="secondary-button" :disabled="copying" @click="$emit('copy')">
          {{ copying ? "已复制" : "复制任务 ID" }}
        </button>
        <button class="secondary-button" :disabled="aiCoachLoading || item.status !== 'done'" @click="$emit('loadAi')">
          {{ aiCoachLoading ? "AI 生成中..." : "AI 解读" }}
        </button>
        <button class="secondary-button" :disabled="!canOpenCompare" @click="$emit('openCompare')">打开动作分析</button>
      </div>
    </div>

    <div v-if="detailLoading" class="feedback-state" data-tone="loading">
      <strong class="feedback-state-title">详情加载中</strong>
      <span class="feedback-state-copy">正在读取本条记录的摘要、输出文件和问题片段。</span>
    </div>

    <div v-else-if="detailError" class="feedback-state" data-tone="error">
      <strong class="feedback-state-title">详情加载失败</strong>
      <span class="feedback-state-copy">{{ detailError }}</span>
    </div>

    <div v-else-if="detail" class="detail-stack">
      <ConfidenceBanner :confidence-score="detail.report?.confidence?.score ?? detail.confidence_score" />

      <div class="detail-hero-line">
        <div>
          <span>当前记录</span>
          <strong>{{ item.pair_name || item.pipeline_id }}</strong>
        </div>
        <div>
          <span>问题片段</span>
          <strong>{{ issues.length }}</strong>
        </div>
        <div>
          <span>最近状态</span>
          <strong>{{ statusText(detail.status) }}</strong>
        </div>
      </div>

      <div v-if="detail.status === 'failed'" class="list-item-card failure-reason-card">
        <div class="task-item-head">
          <strong>失败原因</strong>
          <span class="tag danger">{{ errorTypeText(detail.error_type) }}</span>
        </div>
        <div class="failure-detail-grid">
          <span class="helper-text">错误类型：{{ detail.error_type || "未标记" }}</span>
          <span class="helper-text">原因：{{ failureMessage }}</span>
          <span class="helper-text failure-suggestion">建议：{{ failureSuggestion }}</span>
        </div>
        <details v-if="detail.raw_error" class="raw-error-details">
          <summary>查看开发调试信息</summary>
          <pre>{{ detail.raw_error }}</pre>
        </details>
      </div>

      <div v-if="inputQuality" class="list-item-card input-quality-card" :data-tone="inputQualityTone">
        <div class="task-item-head">
          <strong>输入质量</strong>
          <span class="tag" :class="inputQualityTone">{{ inputQualityLevelText }}</span>
        </div>
        <span class="helper-text">{{ inputQuality.summary || "已记录输入质量。" }}</span>
        <div class="input-quality-grid">
          <div class="metric-chip">
            <strong>教师视频</strong>
            <span>{{ videoMetaText(inputQuality.teacher_meta) }}</span>
          </div>
          <div class="metric-chip">
            <strong>学员视频</strong>
            <span>{{ videoMetaText(inputQuality.user_meta) }}</span>
          </div>
        </div>
        <ul v-if="inputQualityRecommendations.length" class="quality-recommendations">
          <li v-for="item in inputQualityRecommendations" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div class="detail-metric-board">
        <div class="metric-chip"><strong>状态</strong><span>{{ statusText(detail.status) }}</span></div>
        <div class="metric-chip"><strong>阶段</strong><span>{{ stageText(detail.stage, detail.status) }}</span></div>
        <div class="metric-chip"><strong>进度</strong><span>{{ progressPercent(detail.progress) }}%</span></div>
        <div class="metric-chip"><strong>总分</strong><span>{{ scoreText(detail.report?.score_0_100 ?? detail.report?.scores?.score_total ?? detail.score_total) }}</span></div>
        <div class="metric-chip"><strong>动作</strong><span>{{ scoreText(detail.report?.scores?.score_pose ?? detail.score_pose) }}</span></div>
        <div class="metric-chip"><strong>节奏</strong><span>{{ scoreText(detail.report?.scores?.score_tempo ?? detail.score_tempo) }}</span></div>
        <div class="metric-chip"><strong>可信度</strong><span>{{ detailConfidenceText }}</span></div>
        <div class="metric-chip"><strong>开始时间</strong><span>{{ formatDate(detail.started_at || detail.queued_at) }}</span></div>
        <div class="metric-chip"><strong>完成时间</strong><span>{{ formatDate(detail.finished_at || detail.updated_at) }}</span></div>
      </div>

      <div class="list-item-card record-note-card">
        <div class="task-item-head">
          <strong>复盘备注</strong>
          <button class="secondary-button" type="button" :disabled="flagSaving" @click="$emit('toggleStar')">
            {{ item.starred ? "★ 已标重点" : "☆ 标为重点" }}
          </button>
        </div>
        <textarea
          :value="noteDraft"
          rows="3"
          maxlength="500"
          placeholder="写一点复盘备注，例如：论文实验样例、节奏偏快、需要重点回看..."
          @input="$emit('updateNoteDraft', ($event.target as HTMLTextAreaElement).value)"
        />
        <div class="settings-maintenance-foot">
          <span class="helper-text">{{ item.flag_updated_at ? `上次保存 ${formatDate(item.flag_updated_at)}` : "填写后保存为本地标记。" }}</span>
          <button type="button" :disabled="flagSaving" @click="$emit('saveNote')">
            {{ flagSaving ? "保存中..." : "保存备注" }}
          </button>
        </div>
      </div>

      <ScoreExplanationCard :detail="detail" :issue-count="issues.length" />

      <AiCoachCard
        :ai-coach="aiCoach"
        :ai-coach-error="aiCoachError"
        :source-text="aiCoachSourceText"
        :fallback-hint="aiCoachFallbackHint"
      />

      <PriorityReviewList
        :issues="issues"
        :confidence-score="detail.report?.confidence?.score ?? detail.confidence_score"
        @jump-issue="$emit('jumpIssue', $event)"
      />

      <div class="detail-columns">
        <div class="detail-column">
          <div class="list-item-card" v-if="detailLeadText">
            <strong>整体摘要</strong>
            <span class="helper-text">{{ detailLeadText }}</span>
          </div>

          <div class="list-item-card" v-if="detailConfidenceSummaryText">
            <strong>可信度说明</strong>
            <span class="helper-text">{{ detailConfidenceSummaryText }}</span>
          </div>

          <div class="list-item-card" v-if="topJointSummary">
            <strong>重点关节</strong>
            <span class="helper-text">{{ topJointSummary }}</span>
          </div>
        </div>

        <div class="detail-column">
          <div class="list-item-card" v-if="issues.length">
            <strong>问题片段</strong>
            <div class="issue-chip-list">
              <button
                v-for="issue in issues.slice(0, 6)"
                :key="issue.id"
                type="button"
                class="issue-chip"
                @click="$emit('jumpIssue', issue)"
              >
                {{ issueTypeText(issue.type) }} · {{ timeText(issue.sec) }}
              </button>
            </div>
          </div>

          <div class="list-item-card" v-if="detailLinks.length">
            <strong>输出文件</strong>
            <div class="detail-links">
              <a
                v-for="link in detailLinks"
                :key="link.label"
                class="link-button secondary-button"
                :href="link.url"
                target="_blank"
              >
                {{ link.label }}
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { absMediaUrl } from "../../api/http";
import { normalizedConfidenceSummary } from "../../utils/confidence";
import { confidenceLevelText } from "../../composables/useScoreExplanation";
import { pipelineStageText, pipelineStatusText } from "../../services/pipelineStatus";
import AiCoachCard from "./AiCoachCard.vue";
import ConfidenceBanner from "./ConfidenceBanner.vue";
import PriorityReviewList from "./PriorityReviewList.vue";
import ScoreExplanationCard from "./ScoreExplanationCard.vue";
import type {
  AiCoachResponse,
  IssueReplayItem,
  PipelineResultSummaryResponse,
  RecordWorkspaceItem,
} from "../../types/video";

const props = defineProps<{
  item: RecordWorkspaceItem;
  detail: PipelineResultSummaryResponse | null;
  detailLoading: boolean;
  detailError: string;
  issues: IssueReplayItem[];
  aiCoach: AiCoachResponse | null;
  aiCoachError: string;
  aiCoachLoading: boolean;
  aiCoachSourceText: string;
  aiCoachFallbackHint: string;
  canCancel: boolean;
  canDelete: boolean;
  canOpenCompare: boolean;
  copying: boolean;
  deleting: boolean;
  canceling: boolean;
  noteDraft: string;
  flagSaving: boolean;
}>();

defineEmits<{
  cancel: [];
  delete: [];
  copy: [];
  loadAi: [];
  openCompare: [];
  jumpIssue: [issue: IssueReplayItem];
  toggleStar: [];
  saveNote: [];
  updateNoteDraft: [value: string];
}>();

const detailConfidenceText = computed(() => confidenceText(props.detail?.report?.confidence?.score ?? props.detail?.confidence_score));
const inputQuality = computed(() => {
  const value = props.detail?.report?.input_quality;
  return value && typeof value === "object" ? value as Record<string, any> : null;
});
const inputQualityTone = computed(() => {
  const level = String(inputQuality.value?.level || "").toLowerCase();
  if (level === "good") return "good";
  if (level === "warning") return "warning";
  if (level === "error") return "danger";
  return "neutral";
});
const inputQualityLevelText = computed(() => {
  const level = String(inputQuality.value?.level || "").toLowerCase();
  if (level === "good") return "良好";
  if (level === "warning") return "需留意";
  if (level === "error") return "不可读";
  return "暂无";
});
const inputQualityRecommendations = computed(() => {
  const items = inputQuality.value?.recommendations;
  return Array.isArray(items) ? items.filter((item) => typeof item === "string" && item.trim()).slice(0, 3) : [];
});
const detailConfidenceSummaryText = computed(() =>
  normalizedConfidenceSummary(props.detail?.report?.confidence, props.detail?.report?.confidence?.summary || props.detail?.confidence_summary),
);
const failureMessage = computed(() => (
  props.detail?.error_message ||
  props.detail?.message ||
  errorTypeText(props.detail?.error_type) ||
  "本次分析未成功完成。"
));
const failureSuggestion = computed(() => (
  props.detail?.error_suggestion ||
  fallbackFailureSuggestion(props.detail?.error_type)
));

const topJointSummary = computed(() => {
  const joints = props.detail?.report?.top_joints ?? props.detail?.top_joints;
  if (!Array.isArray(joints) || !joints.length) return "";
  return joints.slice(0, 3).map((item: any) => `${item[0]} (${Number(item[1]).toFixed(3)})`).join("、");
});

const detailLeadText = computed(() => (
  props.detail?.report?.recommendations?.overall ||
  props.detail?.overall_advice ||
  props.detail?.report?.beginner_report?.summary ||
  props.detail?.beginner_summary ||
  props.detail?.report?.teaching_report?.summary ||
  props.detail?.teaching_summary ||
  ""
));

const detailLinks = computed(() => {
  const files = props.detail?.files || {};
  const links = [
    { label: "报告 JSON", url: files.report_url },
    { label: "摘要 JSON", url: files.summary_url },
    { label: "教师骨架视频", url: files.teacher_overlay_url },
    { label: "学员骨架视频", url: files.user_overlay_url },
    { label: "时间轴 JSON", url: files.timeline_json_url },
  ];
  return links.filter((item) => item.url).map((item) => ({ label: item.label, url: absMediaUrl(item.url) }));
});

function progressPercent(progress?: number | null) {
  const value = Number(progress ?? 0);
  if (!Number.isFinite(value)) return 0;
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

function statusText(status?: string | null) {
  return pipelineStatusText(status);
}

function errorTypeText(value?: string | null) {
  const map: Record<string, string> = {
    video_missing: "视频文件不存在",
    video_unreadable: "视频无法读取",
    ffmpeg_missing: "缺少 ffmpeg",
    pose_cache_missing: "姿态缓存缺失",
    model_missing: "模型缺失",
    low_quality_input: "输入质量不足",
    pipeline_internal_error: "内部异常",
    canceled: "用户取消",
    timeout: "任务超时",
  };
  return value ? map[value] || value : "未知原因";
}

function fallbackFailureSuggestion(value?: string | null) {
  const map: Record<string, string> = {
    video_missing: "请确认教师或学员视频文件仍在本地素材库中，再重新发起分析。",
    video_unreadable: "请换用可正常播放的视频，或重新导出为常见 MP4 格式。",
    ffmpeg_missing: "请安装 ffmpeg/ffprobe，并确认命令行可以直接执行。",
    pose_cache_missing: "请重新运行分析，让系统重新生成姿态缓存。",
    model_missing: "请检查 models/pose_landmarker_full.task 是否存在。",
    low_quality_input: "请改善拍摄角度、全身入镜、光照和遮挡情况后再试。",
    pipeline_internal_error: "请保留任务 ID 和调试信息，重试后仍失败再检查后端日志。",
    canceled: "任务已取消，可重新发起分析。",
    timeout: "请尝试使用更短的视频，或检查本机资源占用后重新分析。",
  };
  return value ? map[value] || "请检查输入视频和本地环境，修复后重试。" : "请检查视频、模型和系统状态，修复后重试。";
}

function stageText(stage?: string | null, status?: string | null) {
  return pipelineStageText(stage, status);
}

function issueTypeText(value?: string) {
  if (value === "pose_error") return "动作误差";
  if (value === "tempo") return "节奏异常";
  if (value === "confidence") return "可信度风险";
  if (value === "tracking_bad") return "跟踪问题";
  return value || "待定";
}

function confidenceText(value?: number | string | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return `${Math.round(num * 100)}% (${confidenceLevelText(num)})`;
}

function videoMetaText(meta?: Record<string, any> | null) {
  if (!meta || typeof meta !== "object") return "暂无元信息";
  const duration = Number(meta.duration_sec);
  const width = Number(meta.width);
  const height = Number(meta.height);
  const fps = Number(meta.fps);
  const parts = [
    Number.isFinite(duration) && duration > 0 ? `${duration.toFixed(1)}s` : "",
    Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0 ? `${Math.round(width)}x${Math.round(height)}` : "",
    Number.isFinite(fps) && fps > 0 ? `${fps.toFixed(1)}fps` : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" / ") : "暂无元信息";
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
.inline-detail,
.detail-stack,
.detail-column,
.detail-columns,
.issue-chip-list {
  display: grid;
  gap: 14px;
}

.inline-detail {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(15, 143, 179, 0.22);
  background:
    linear-gradient(180deg, rgba(248, 252, 255, 0.99) 0%, rgba(255, 255, 255, 0.99) 100%);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.1);
}

.detail-panel-head {
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.detail-panel-head h2 {
  margin-top: 2px;
}

.detail-eyebrow {
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  overflow-wrap: anywhere;
}

.detail-actions {
  justify-content: flex-end;
}

.compact-stats,
.detail-metric-board,
.detail-hero-line {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.detail-hero-line {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(15, 143, 179, 0.12);
  background:
    linear-gradient(90deg, rgba(232, 247, 252, 0.92) 0%, rgba(255, 255, 255, 0.86) 100%);
}

.detail-hero-line > div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.detail-hero-line span {
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 800;
}

.detail-hero-line strong {
  overflow-wrap: anywhere;
}

.detail-metric-board {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.detail-metric-board .metric-chip {
  min-height: 74px;
}

.detail-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.record-note-card {
  gap: 10px;
}

.record-note-card textarea {
  width: 100%;
  resize: vertical;
  min-height: 84px;
}

.record-note-card .settings-maintenance-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.failure-reason-card {
  border-color: rgba(180, 35, 24, 0.18);
  background: rgba(254, 242, 242, 0.72);
  gap: 8px;
}

.failure-suggestion {
  color: var(--text);
  font-weight: 650;
}

.failure-detail-grid {
  display: grid;
  gap: 6px;
}

.raw-error-details {
  border-top: 1px solid rgba(180, 35, 24, 0.12);
  padding-top: 8px;
}

.raw-error-details summary {
  cursor: pointer;
  color: var(--muted);
  font-size: 0.86rem;
  font-weight: 700;
}

.raw-error-details pre {
  overflow-x: auto;
  white-space: pre-wrap;
  margin: 8px 0 0;
  padding: 10px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.08);
  color: var(--text);
  font-size: 0.78rem;
  line-height: 1.55;
}

.input-quality-card {
  gap: 10px;
}

.input-quality-card[data-tone="good"] {
  border-color: rgba(22, 163, 74, 0.18);
  background: rgba(240, 253, 244, 0.58);
}

.input-quality-card[data-tone="warning"] {
  border-color: rgba(217, 119, 6, 0.22);
  background: rgba(255, 251, 235, 0.72);
}

.input-quality-card[data-tone="danger"] {
  border-color: rgba(180, 35, 24, 0.2);
  background: rgba(254, 242, 242, 0.72);
}

.input-quality-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.quality-recommendations {
  margin: 0;
  padding-left: 1.1rem;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.7;
}

.issue-chip-list {
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

.danger-button {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.22);
}

.danger-button:hover:not(:disabled) {
  border-color: rgba(180, 35, 24, 0.4);
  background: rgba(180, 35, 24, 0.08);
}

@media (max-width: 1180px) {
  .detail-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1024px) {
  .compact-stats,
  .detail-metric-board,
  .detail-hero-line,
  .input-quality-grid,
  .issue-chip-list {
    grid-template-columns: 1fr;
  }
}
</style>
