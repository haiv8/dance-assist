<template>
  <div class="inline-detail">
    <div class="panel-head compact-head">
      <div>
        <h2>记录详情</h2>
        <p class="helper-text">主要动作集中在这里，避免为同一条记录切换多个菜单。</p>
      </div>
      <div class="action-row">
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
          {{ aiCoachLoading ? "AI生成中..." : "AI解读" }}
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
      <div class="metric-row compact-stats">
        <div class="metric-chip"><strong>状态</strong><span>{{ statusText(detail.status) }}</span></div>
        <div class="metric-chip"><strong>阶段</strong><span>{{ stageText(detail.stage, detail.status) }}</span></div>
        <div class="metric-chip"><strong>进度</strong><span>{{ progressPercent(detail.progress) }}%</span></div>
      </div>

      <div class="metric-row compact-stats">
        <div class="metric-chip"><strong>总分</strong><span>{{ scoreText(detail.report?.score_0_100 ?? detail.report?.scores?.score_total ?? detail.score_total) }}</span></div>
        <div class="metric-chip"><strong>动作</strong><span>{{ scoreText(detail.report?.scores?.score_pose ?? detail.score_pose) }}</span></div>
        <div class="metric-chip"><strong>节奏</strong><span>{{ scoreText(detail.report?.scores?.score_tempo ?? detail.score_tempo) }}</span></div>
      </div>

      <div class="metric-row compact-stats">
        <div class="metric-chip"><strong>可信度</strong><span>{{ detailConfidenceText }}</span></div>
        <div class="metric-chip"><strong>开始时间</strong><span>{{ formatDate(detail.started_at || detail.queued_at) }}</span></div>
        <div class="metric-chip"><strong>完成时间</strong><span>{{ formatDate(detail.finished_at || detail.updated_at) }}</span></div>
      </div>

      <ScoreExplanationCard :detail="detail" :issue-count="issues.length" />

      <AiCoachCard
        :ai-coach="aiCoach"
        :ai-coach-error="aiCoachError"
        :source-text="aiCoachSourceText"
        :fallback-hint="aiCoachFallbackHint"
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
import AiCoachCard from "./AiCoachCard.vue";
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
}>();

defineEmits<{
  cancel: [];
  delete: [];
  copy: [];
  loadAi: [];
  openCompare: [];
  jumpIssue: [issue: IssueReplayItem];
}>();

const detailConfidenceText = computed(() => confidenceText(props.detail?.report?.confidence?.score ?? props.detail?.confidence_score));
const detailConfidenceSummaryText = computed(() =>
  normalizedConfidenceSummary(props.detail?.report?.confidence, props.detail?.report?.confidence?.summary || props.detail?.confidence_summary),
);

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
  if (status === "pending") return "等待中";
  if (status === "running") return "分析中";
  if (status === "done") return "已完成";
  if (status === "failed") return "失败";
  if (status === "canceled") return "已取消";
  return status || "未知";
}

function stageText(stage?: string | null, status?: string | null) {
  if (stage === "queued") return "已进入队列";
  if (stage === "preparing_inputs") return "准备素材";
  if (stage === "extracting_pose") return "提取骨架";
  if (stage === "aligning_motion") return "动作对齐与评分";
  if (stage === "rendering_outputs") return "生成对比输出";
  if (stage === "packaging_results") return "整理结果";
  if (stage === "completed") return "结果已就绪";
  if (stage === "failed") return "任务失败";
  if (stage === "canceled") return "任务已取消";
  return statusText(status);
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

.detail-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
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
  .issue-chip-list {
    grid-template-columns: 1fr;
  }
}
</style>
