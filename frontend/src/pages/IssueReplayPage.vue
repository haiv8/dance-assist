<template>
  <main class="app-page issue-page">
    <section class="surface-card page-head">
      <div class="page-head-row">
        <div>
          <h1>问题回放</h1>
          <p class="page-subtitle">把高误差片段、节奏异常区间和可信度风险整理成可直接复盘的列表，点击后会在当前条目下方展开详细信息。</p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="loading" @click="refreshPage">
            {{ loading ? "刷新中..." : "刷新列表" }}
          </button>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell">
          <span class="status-caption">报告数</span>
          <strong class="status-main">{{ reports.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">问题片段</span>
          <strong class="status-main">{{ issueItems.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">动作误差</span>
          <strong class="status-main">{{ poseIssueCount }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">节奏与可信度</span>
          <strong class="status-main">{{ tempoAndConfidenceCount }}</strong>
        </div>
      </div>
    </section>

    <section class="selection-grid issue-summary-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>筛选条件</h2>
            <p class="helper-text">先按报告、问题类型和严重程度过滤，再点开具体条目进行回放。</p>
          </div>
        </div>

        <div class="field-grid two-col-fields">
          <div class="field-block">
            <label class="field-label">报告检索</label>
            <input v-model.trim="keyword" type="text" :placeholder="searchPlaceholder" />
          </div>
          <div class="field-block">
            <label class="field-label">问题类型</label>
            <select v-model="issueTypeFilter">
              <option value="all">全部类型</option>
              <option value="pose_error">动作误差</option>
              <option value="tempo">节奏异常</option>
              <option value="confidence">可信度风险</option>
              <option value="tracking_bad">跟踪问题</option>
            </select>
          </div>
        </div>

        <div class="field-grid two-col-fields">
          <div class="field-block">
            <label class="field-label">严重程度</label>
            <select v-model="severityFilter">
              <option value="all">全部优先级</option>
              <option value="high">高优先级</option>
              <option value="medium">中优先级</option>
              <option value="low">低优先级</option>
            </select>
          </div>
          <div class="field-block">
            <label class="field-label">显示数量</label>
            <select v-model.number="limit">
              <option :value="20">最近 20 条</option>
              <option :value="50">最近 50 条</option>
              <option :value="100">最近 100 条</option>
            </select>
          </div>
        </div>

        <div v-if="error" class="feedback-inline" style="margin-top: 12px;">{{ error }}</div>
        <p v-else class="helper-text issue-note">{{ filterSummary }}</p>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>当前焦点</h2>
            <p class="helper-text">这里同步展示当前展开的问题片段，方便你快速确认定位信息。</p>
          </div>
        </div>

        <div v-if="selectedIssue" class="summary-stack">
          <div class="summary-row">
            <span>所属报告</span>
            <strong>{{ selectedIssue.pairName }}</strong>
          </div>
          <div class="summary-row">
            <span>问题类型</span>
            <strong>{{ issueTypeText(selectedIssue.type) }}</strong>
          </div>
          <div class="summary-row">
            <span>定位时间</span>
            <strong>{{ timeText(selectedIssue.sec) }}</strong>
          </div>
          <div class="summary-row">
            <span>优先级</span>
            <strong>{{ severityText(selectedIssue.severity) }}</strong>
          </div>
        </div>
        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">当前没有聚焦的问题片段</strong>
          <span class="feedback-state-copy">点开下方任意一条问题后，这里会同步显示摘要。</span>
        </div>
      </article>
    </section>

    <section class="issue-layout">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>问题列表</h2>
            <p class="helper-text">按报告完成时间倒序展示，如果存在标记点，会优先用标记点来定位复盘。</p>
          </div>
          <span class="tag">{{ filteredIssues.length }} 条</span>
        </div>

        <div v-if="loading && !reports.length" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">问题列表加载中</strong>
          <span class="feedback-state-copy">正在读取历史报告与问题标记，请稍候。</span>
        </div>
        <div v-else-if="!filteredIssues.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">当前筛选下没有可复盘的问题片段</strong>
          <span class="feedback-state-copy">可以调整筛选条件，或者刷新报告后再进来查看。</span>
        </div>
        <div v-else class="issue-list">
          <div v-for="item in filteredIssues" :key="item.id" class="issue-item-shell">
            <button
              type="button"
              class="issue-item"
              :class="{ active: selectedIssueId === item.id }"
              @click="toggleIssue(item.id)"
            >
              <div class="issue-item-head">
                <div>
                  <strong>{{ item.pairName }}</strong>
                  <p class="helper-text">{{ issueTypeText(item.type) }} · {{ timeText(item.sec) }}</p>
                </div>
                <span class="tag" :class="severityTone(item.severity)">{{ severityText(item.severity) }}</span>
              </div>

              <p class="helper-text issue-item-copy">{{ item.summary }}</p>

              <div class="task-item-meta">
                <span>完成时间：{{ formatDate(item.finishedAt) }}</span>
                <span>总分：{{ scoreText(item.scoreTotal) }}</span>
                <span>可信度：{{ confidenceText(item.confidenceScore) }}</span>
              </div>
            </button>

            <div
              v-if="selectedIssueId === item.id"
              ref="detailPanelRef"
              class="issue-inline-detail"
            >
              <div class="panel-head compact-head">
                <div>
                  <h2>复盘动作</h2>
                  <p class="helper-text">从这里可以直接跳回动作分析、报告中心或任务中心，不用来回找入口。</p>
                </div>
                <div class="action-row">
                  <button class="ghost-button danger-button" type="button" :disabled="deletingIssue" @click="deleteSelectedIssue">
                    {{ deletingIssue ? "删除中..." : "删除记录" }}
                  </button>
                </div>
              </div>

              <div v-if="selectedIssue" class="detail-stack">
                <div class="metric-row compact-stats">
                  <div class="metric-chip"><strong>问题类型</strong><span>{{ issueTypeText(selectedIssue.type) }}</span></div>
                  <div class="metric-chip"><strong>定位时间</strong><span>{{ timeText(selectedIssue.sec) }}</span></div>
                  <div class="metric-chip"><strong>优先级</strong><span>{{ severityText(selectedIssue.severity) }}</span></div>
                </div>

                <div class="list-item-card">
                  <strong>复盘摘要</strong>
                  <span class="helper-text">{{ selectedIssue.summary }}</span>
                </div>

                <div class="list-item-card" v-if="selectedIssue.action">
                  <strong>处理建议</strong>
                  <span class="helper-text">{{ selectedIssue.action }}</span>
                </div>

                <div class="detail-links issue-links">
                  <button class="secondary-button" type="button" @click="jumpToCompare">定位到动作分析</button>
                  <button class="secondary-button" type="button" @click="openReport">打开报告中心</button>
                  <button class="secondary-button" type="button" @click="openTask">打开任务中心</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deletePipelineTask, getAnalysisReport, listAnalysisReports } from "../api/pipelines";
import { focusDetailPanel } from "../utils/detailPanel";
import { normalizedConfidenceIssues, normalizedConfidenceSummary } from "../utils/confidence";
import { friendlyError } from "../utils/errors";
import type { AnalysisReportDetailResponse, AnalysisReportItem } from "../types/video";

type IssueSeverity = "high" | "medium" | "low";

type IssueReplayItem = {
  id: string;
  pipelineId: string;
  pairName: string;
  teacherVideoId?: string | null;
  userVideoId?: string | null;
  type: string;
  severity: IssueSeverity;
  sec: number;
  frame?: number | null;
  summary: string;
  action?: string;
  finishedAt?: string | null;
  scoreTotal?: number | null;
  confidenceScore?: number | null;
};

const router = useRouter();
const route = useRoute();

const loading = ref(false);
const error = ref("");
const reports = ref<AnalysisReportItem[]>([]);
const issueMap = ref<Record<string, IssueReplayItem[]>>({});
const keyword = ref("");
const issueTypeFilter = ref("all");
const severityFilter = ref("all");
const limit = ref(50);
const detailPanelRef = ref<HTMLElement | null>(null);
const selectedIssueId = ref("");
const deletingIssue = ref(false);

const searchPlaceholder = "搜索教师或学员素材名称";

const issueItems = computed(() => reports.value.flatMap((report) => issueMap.value[report.pipeline_id] || []));
const filteredIssues = computed(() => {
  const needle = keyword.value.trim().toLowerCase();
  return issueItems.value.filter((item) => {
    const matchesKeyword = !needle || item.pairName.toLowerCase().includes(needle);
    const matchesType = issueTypeFilter.value === "all" || item.type === issueTypeFilter.value;
    const matchesSeverity = severityFilter.value === "all" || item.severity === severityFilter.value;
    return matchesKeyword && matchesType && matchesSeverity;
  });
});
const selectedIssue = computed(() => filteredIssues.value.find((item) => item.id === selectedIssueId.value) ?? null);
const poseIssueCount = computed(() => issueItems.value.filter((item) => item.type === "pose_error").length);
const tempoAndConfidenceCount = computed(() => issueItems.value.filter((item) => item.type === "tempo" || item.type === "confidence").length);
const filterSummary = computed(() => {
  if (!reports.value.length) return "问题回放会从已完成报告中提取可复盘的标记点。";
  return `当前已从 ${reports.value.length} 份报告中整理出 ${filteredIssues.value.length} 条可直接复盘的问题片段。`;
});

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

function issueTypeText(value?: string) {
  if (value === "pose_error") return "动作误差";
  if (value === "tempo") return "节奏异常";
  if (value === "confidence") return "可信度风险";
  if (value === "tracking_bad") return "跟踪问题";
  return value || "待定";
}

function confidenceText(value?: number | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return `${Math.round(num * 100)}%`;
}

function scoreText(value?: number | null) {
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

function markerSeverity(value?: string): IssueSeverity {
  if (value === "severe" || value === "clear") return "high";
  if (value === "mild") return "medium";
  return "medium";
}

function extractIssues(report: AnalysisReportDetailResponse): IssueReplayItem[] {
  const result: IssueReplayItem[] = [];
  const pairName = report.pair_name || report.pipeline_id;
  const markers = Array.isArray(report.report?.markers) ? report.report?.markers : [];

  for (const marker of markers) {
    const sec = Number((marker as any)?.sec);
    if (!Number.isFinite(sec)) continue;
    result.push({
      id: `${report.pipeline_id}_marker_${(marker as any)?.frame ?? sec}_${(marker as any)?.type || "unknown"}`,
      pipelineId: report.pipeline_id,
      pairName,
      teacherVideoId: report.teacher_video_id,
      userVideoId: report.user_video_id,
      type: String((marker as any)?.type || "pose_error"),
      severity: markerSeverity((marker as any)?.severity),
      sec,
      frame: Number((marker as any)?.frame),
      summary: `${issueTypeText(String((marker as any)?.type || "pose_error"))}，${timeText(sec)}，${(marker as any)?.severity ? severityText(markerSeverity((marker as any)?.severity)) : "需要关注"}`,
      action: "建议跳回动作分析页，结合双视频和时间轴对照这一段。",
      finishedAt: report.finished_at || report.updated_at,
      scoreTotal: report.score_total,
      confidenceScore: report.confidence_score,
    });
  }

  const tempoSegments = Array.isArray(report.report?.tempo_segments) ? report.report?.tempo_segments : [];
  for (let index = 0; index < tempoSegments.length; index += 1) {
    const segment = tempoSegments[index] as any;
    const sec = Number(segment?.start_sec ?? segment?.sec ?? segment?.t0);
    if (!Number.isFinite(sec)) continue;
    result.push({
      id: `${report.pipeline_id}_tempo_${index}`,
      pipelineId: report.pipeline_id,
      pairName,
      teacherVideoId: report.teacher_video_id,
      userVideoId: report.user_video_id,
      type: "tempo",
      severity: "medium",
      sec,
      frame: null,
      summary: `第 ${index + 1} 段节奏异常，建议对照拍点和动作转场。`,
      action: "可先聚焦这一段的拍点、重心转移和动作发力节奏。",
      finishedAt: report.finished_at || report.updated_at,
      scoreTotal: report.score_total,
      confidenceScore: report.confidence_score,
    });
  }

  const confidenceSummary = normalizedConfidenceSummary(report.report?.confidence, report.confidence_summary);
  const confidenceIssues = normalizedConfidenceIssues(report.report?.confidence);
  for (let index = 0; index < confidenceIssues.length; index += 1) {
    const issue = confidenceIssues[index] as any;
    const markerSec = Number(markers.find((item: any) => Number.isFinite(Number(item?.sec)))?.sec);
    result.push({
      id: `${report.pipeline_id}_confidence_${index}`,
      pipelineId: report.pipeline_id,
      pairName,
      teacherVideoId: report.teacher_video_id,
      userVideoId: report.user_video_id,
      type: "confidence",
      severity: "high",
      sec: Number.isFinite(markerSec) ? markerSec : 0,
      frame: null,
      summary: String(issue?.message || confidenceSummary || "本轮分析存在可信度风险。"),
      action: String(issue?.suggestion || "建议先改善拍摄视角或跟踪质量，再重新复测。"),
      finishedAt: report.finished_at || report.updated_at,
      scoreTotal: report.score_total,
      confidenceScore: report.confidence_score,
    });
  }

  return result.sort((a, b) => a.sec - b.sec);
}

async function loadReports() {
  loading.value = true;
  error.value = "";
  try {
    const data = await listAnalysisReports({ limit: limit.value });
    reports.value = data.items;
    const nextMap: Record<string, IssueReplayItem[]> = {};
    for (const report of reports.value) {
      try {
        const detail = await getAnalysisReport(report.pipeline_id);
        nextMap[report.pipeline_id] = extractIssues(detail);
      } catch {
        nextMap[report.pipeline_id] = [];
      }
    }
    issueMap.value = nextMap;
    alignSelection();
  } catch (err: any) {
    error.value = friendlyError(err, "问题回放列表加载失败");
  } finally {
    loading.value = false;
  }
}

function alignSelection() {
  const pipelineQuery = typeof route.query.pipeline === "string" ? route.query.pipeline : "";
  const secQuery = Number(typeof route.query.sec === "string" ? route.query.sec : "");
  if (pipelineQuery) {
    const hit = filteredIssues.value.find((item) => item.pipelineId === pipelineQuery && (!Number.isFinite(secQuery) || Math.abs(item.sec - secQuery) < 0.11));
    if (hit) {
      void openIssue(hit.id);
      return;
    }
  }
  if (!filteredIssues.value.length) {
    selectedIssueId.value = "";
    return;
  }
  if (!selectedIssueId.value || !filteredIssues.value.some((item) => item.id === selectedIssueId.value)) {
    selectedIssueId.value = filteredIssues.value[0].id;
  }
}

async function refreshPage() {
  await loadReports();
}

async function openIssue(issueId: string) {
  selectedIssueId.value = issueId;
  await Promise.resolve();
  focusDetailPanel(detailPanelRef, { forceScroll: true });
}

function closeIssueDetail() {
  selectedIssueId.value = "";
}

async function toggleIssue(issueId: string) {
  if (issueId === selectedIssueId.value) {
    closeIssueDetail();
    return;
  }
  await openIssue(issueId);
}

async function deleteSelectedIssue() {
  const issue = selectedIssue.value;
  if (!issue?.pipelineId) return;

  const confirmed = window.confirm(`确认删除“${issue.pairName}”的历史记录吗？相关报告和问题片段会一起移除。`);
  if (!confirmed) return;

  deletingIssue.value = true;
  error.value = "";
  try {
    await deletePipelineTask(issue.pipelineId);
    reports.value = reports.value.filter((item) => item.pipeline_id !== issue.pipelineId);
    const nextMap = { ...issueMap.value };
    delete nextMap[issue.pipelineId];
    issueMap.value = nextMap;
    alignSelection();
  } catch (err: any) {
    error.value = friendlyError(err, "删除历史记录失败");
  } finally {
    deletingIssue.value = false;
  }
}

function jumpToCompare() {
  if (!selectedIssue.value) return;
  void router.push({
    path: "/compare",
    query: {
      pipeline: selectedIssue.value.pipelineId,
      teacher: selectedIssue.value.teacherVideoId || undefined,
      user: selectedIssue.value.userVideoId || undefined,
      sec: String(selectedIssue.value.sec),
      mode: "local",
    },
  });
}

function openReport() {
  if (!selectedIssue.value) return;
  void router.push({ path: "/reports", query: { pipeline: selectedIssue.value.pipelineId } });
}

function openTask() {
  if (!selectedIssue.value) return;
  void router.push({ path: "/tasks", query: { pipeline: selectedIssue.value.pipelineId } });
}

watch([keyword, issueTypeFilter, severityFilter], () => {
  alignSelection();
});

watch(limit, () => {
  void loadReports();
});

watch(
  () => [route.query.pipeline, route.query.sec],
  () => {
    alignSelection();
  },
);

onMounted(() => {
  void loadReports();
});
</script>

<style scoped>
.issue-summary-grid {
  align-items: start;
}

.issue-note {
  margin-top: 14px;
  line-height: 1.7;
}

.issue-layout {
  display: grid;
  gap: 16px;
}

.issue-list,
.detail-stack,
.issue-item-shell,
.summary-stack {
  display: grid;
  gap: 12px;
}

.issue-item {
  display: grid;
  gap: 12px;
  width: 100%;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.98);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

.issue-item:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(226, 109, 61, 0.18);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.issue-item.active {
  border-color: rgba(226, 109, 61, 0.32);
  background: linear-gradient(180deg, rgba(255, 248, 243, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.issue-item-head,
.issue-links,
.summary-row,
.task-item-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.issue-item-head strong {
  display: block;
  margin-bottom: 4px;
}

.issue-item-head p {
  margin: 0;
}

.issue-item-copy {
  line-height: 1.65;
}

.summary-row {
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.summary-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.issue-inline-detail {
  display: grid;
  gap: 14px;
  padding: 16px 18px 18px;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.issue-links {
  margin-top: 4px;
}

.danger-button {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.22);
}

.danger-button:hover:not(:disabled) {
  border-color: rgba(180, 35, 24, 0.4);
  background: rgba(180, 35, 24, 0.08);
}

@media (max-width: 1024px) {
  .two-col-fields,
  .compact-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .issue-item-head,
  .issue-links,
  .summary-row,
  .task-item-meta {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
