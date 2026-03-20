<template>
  <main class="app-page issue-page">
    <section class="surface-card page-head">
      <div class="page-head-row">
        <div>
          <h1>&#38382;&#39064;&#22238;&#25918;</h1>
          <p class="page-subtitle">
            &#25226;&#39640;&#35823;&#24046;&#29255;&#27573;&#12289;&#33410;&#22863;&#24322;&#24120;&#21306;&#38388;&#21644;&#20302;&#21487;&#20449;&#24230;&#25552;&#31034;&#25910;&#25972;&#25104;&#19968;&#20010;&#29420;&#31435;&#39029;&#38754;&#65292;
            &#26041;&#20415;&#20320;&#30452;&#25509;&#23450;&#20301;&#22797;&#30424;&#12290;
          </p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="loading" @click="refreshPage">
            {{ loading ? refreshLoadingLabel : refreshLabel }}
          </button>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell">
          <span class="status-caption">&#25253;&#21578;&#25968;</span>
          <strong class="status-main">{{ reports.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">&#38382;&#39064;&#29255;&#27573;</span>
          <strong class="status-main">{{ issueItems.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">&#21160;&#20316;&#35823;&#24046;</span>
          <strong class="status-main">{{ poseIssueCount }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">&#33410;&#22863;&#19982;&#21487;&#20449;&#24230;</span>
          <strong class="status-main">{{ tempoAndConfidenceCount }}</strong>
        </div>
      </div>
    </section>

    <section class="selection-grid issue-summary-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#31579;&#36873;&#26465;&#20214;</h2>
            <p class="helper-text">&#20808;&#25353;&#25253;&#21578;&#12289;&#38382;&#39064;&#31867;&#22411;&#21644;&#20005;&#37325;&#31243;&#24230;&#36807;&#28388;&#65292;&#20877;&#36827;&#20837;&#21491;&#20391;&#24555;&#36895;&#22797;&#30424;&#12290;</p>
          </div>
        </div>

        <div class="field-grid two-col-fields">
          <div class="field-block">
            <label class="field-label">&#25253;&#21578;&#26816;&#32034;</label>
            <input v-model.trim="keyword" type="text" :placeholder="searchPlaceholder" />
          </div>
          <div class="field-block">
            <label class="field-label">&#38382;&#39064;&#31867;&#22411;</label>
            <select v-model="issueTypeFilter">
              <option value="all">&#20840;&#37096;&#31867;&#22411;</option>
              <option value="pose_error">&#21160;&#20316;&#35823;&#24046;</option>
              <option value="tempo">&#33410;&#22863;&#24322;&#24120;</option>
              <option value="confidence">&#21487;&#20449;&#24230;&#39118;&#38505;</option>
              <option value="tracking_bad">&#36319;&#36394;&#38382;&#39064;</option>
            </select>
          </div>
        </div>

        <div class="field-grid two-col-fields">
          <div class="field-block">
            <label class="field-label">&#20005;&#37325;&#31243;&#24230;</label>
            <select v-model="severityFilter">
              <option value="all">&#20840;&#37096;&#20248;&#20808;&#32423;</option>
              <option value="high">&#39640;&#20248;&#20808;&#32423;</option>
              <option value="medium">&#20013;&#20248;&#20808;&#32423;</option>
              <option value="low">&#20302;&#20248;&#20808;&#32423;</option>
            </select>
          </div>
          <div class="field-block">
            <label class="field-label">&#26174;&#31034;&#25968;&#37327;</label>
            <select v-model.number="limit">
              <option :value="20">&#26368;&#36817; 20 &#26465;</option>
              <option :value="50">&#26368;&#36817; 50 &#26465;</option>
              <option :value="100">&#26368;&#36817; 100 &#26465;</option>
            </select>
          </div>
        </div>

        <div v-if="error" class="feedback-inline" style="margin-top: 12px;">{{ error }}</div>
        <p v-else class="helper-text issue-note">{{ filterSummary }}</p>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#24403;&#21069;&#28966;&#28857;</h2>
            <p class="helper-text">&#40664;&#35748;&#23637;&#31034;&#31526;&#21512;&#26465;&#20214;&#30340;&#31532;&#19968;&#26465;&#38382;&#39064;&#65292;&#21487;&#20197;&#20174;&#19979;&#26041;&#21015;&#34920;&#210?;&#25442;&#22797;&#30424;&#12290;</p>
          </div>
        </div>

        <div v-if="selectedIssue" class="summary-stack">
          <div class="summary-row">
            <span>&#25152;&#23646;&#25253;&#21578;</span>
            <strong>{{ selectedIssue.pairName }}</strong>
          </div>
          <div class="summary-row">
            <span>&#38382;&#39064;&#31867;&#22411;</span>
            <strong>{{ issueTypeText(selectedIssue.type) }}</strong>
          </div>
          <div class="summary-row">
            <span>&#23450;&#20301;&#26102;&#38388;</span>
            <strong>{{ timeText(selectedIssue.sec) }}</strong>
          </div>
          <div class="summary-row">
            <span>&#20248;&#20808;&#32423;</span>
            <strong>{{ severityText(selectedIssue.severity) }}</strong>
          </div>
        </div>
        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#26242;&#26102;&#27809;&#26377;&#31526;&#21512;&#26465;&#20214;&#30340;&#38382;&#39064;&#29255;&#27573;</strong>
          <span class="feedback-state-copy">&#21487;&#20197;&#25918;&#23485;&#31579;&#36873;&#26465;&#20214;&#65292;&#25110;&#32773;&#20808;&#22238;&#21040;&#21160;&#20316;&#20998;&#26512;&#39029;&#29983;&#25104;&#26032;&#32467;&#26524;&#12290;</span>
        </div>
      </article>
    </section>

    <section class="issue-layout">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#38382;&#39064;&#21015;&#34920;</h2>
            <p class="helper-text">&#25353;&#25253;&#21578;&#23436;&#25104;&#26102;&#38388;&#20502;&#24207;&#23637;&#31034;&#65292;&#22914;&#26524;&#23384;&#22312;&#26631;&#35760;&#28857;&#65292;&#20250;&#20248;&#20808;&#29992;&#26631;&#35760;&#28857;&#26469;&#23450;&#20301;&#22797;&#30424;&#12290;</p>
          </div>
          <span class="tag">{{ filteredIssues.length }} &#26465;</span>
        </div>

        <div v-if="loading && !reports.length" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">&#38382;&#39064;&#21015;&#34920;&#21152;&#36733;&#20013;</strong>
          <span class="feedback-state-copy">&#27491;&#22312;&#35835;&#21462;&#21382;&#21490;&#25253;&#21578;&#19982;&#38382;&#39064;&#26631;&#35760;&#65292;&#35831;&#31245;&#20505;&#12290;</span>
        </div>
        <div v-else-if="!filteredIssues.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#24403;&#21069;&#31579;&#36873;&#19979;&#27809;&#26377;&#21487;&#22797;&#30424;&#30340;&#38382;&#39064;&#29255;&#27573;</strong>
          <span class="feedback-state-copy">&#21487;&#20197;&#35843;&#20302;&#31579;&#36873;&#38376;&#27083;&#65292;&#25110;&#32773;&#21047;&#26032;&#25253;&#21578;&#21518;&#20877;&#36827;&#26469;&#26597;&#30475;&#12290;</span>
        </div>
        <div v-else class="issue-list">
          <button
            v-for="item in filteredIssues"
            :key="item.id"
            type="button"
            class="issue-item"
            :class="{ active: selectedIssueId === item.id }"
            @click="selectedIssueId = item.id"
          >
            <div class="issue-item-head">
              <div>
                <strong>{{ item.pairName }}</strong>
                <p class="helper-text">{{ issueTypeText(item.type) }} ? {{ timeText(item.sec) }}</p>
              </div>
              <span class="tag" :class="severityTone(item.severity)">{{ severityText(item.severity) }}</span>
            </div>

            <p class="helper-text issue-item-copy">{{ item.summary }}</p>

            <div class="task-item-meta">
              <span>&#23436;&#25104;&#26102;&#38388;&#65306;{{ formatDate(item.finishedAt) }}</span>
              <span>&#24635;&#20998;&#65306;{{ scoreText(item.scoreTotal) }}</span>
              <span>&#21487;&#20449;&#24230;&#65306;{{ confidenceText(item.confidenceScore) }}</span>
            </div>
          </button>
        </div>
      </article>

      <article class="surface-card detail-panel">
        <div class="panel-head compact-head">
          <div>
            <h2>&#22797;&#30424;&#21160;&#20316;</h2>
            <p class="helper-text">&#20174;&#36825;&#37324;&#21487;&#20197;&#30452;&#25509;&#36339;&#22238;&#21160;&#20316;&#20998;&#26512;&#12289;&#25253;&#21578;&#20013;&#24515;&#25110;&#20219;&#21153;&#20013;&#24515;&#65292;&#23613;&#37327;&#19981;&#35753;&#20320;&#37325;&#22797;&#23547;&#25214;&#20837;&#21475;&#12290;</p>
          </div>
        </div>

        <div v-if="selectedIssue" class="detail-stack">
          <div class="metric-row compact-stats">
            <div class="metric-chip"><strong>&#38382;&#39064;&#31867;&#22411;</strong><span>{{ issueTypeText(selectedIssue.type) }}</span></div>
            <div class="metric-chip"><strong>&#23450;&#20301;&#26102;&#38388;</strong><span>{{ timeText(selectedIssue.sec) }}</span></div>
            <div class="metric-chip"><strong>&#20248;&#20808;&#32423;</strong><span>{{ severityText(selectedIssue.severity) }}</span></div>
          </div>

          <div class="list-item-card">
            <strong>&#22797;&#30424;&#25688;&#35201;</strong>
            <span class="helper-text">{{ selectedIssue.summary }}</span>
          </div>

          <div class="list-item-card" v-if="selectedIssue.action">
            <strong>&#22788;&#29702;&#24314;&#35758;</strong>
            <span class="helper-text">{{ selectedIssue.action }}</span>
          </div>

          <div class="detail-links issue-links">
            <button class="secondary-button" type="button" @click="jumpToCompare">&#23450;&#20301;&#21040;&#21160;&#20316;&#20998;&#26512;</button>
            <button class="secondary-button" type="button" @click="openReport">&#25171;&#24320;&#25253;&#21578;&#20013;&#24515;</button>
            <button class="secondary-button" type="button" @click="openTask">&#25171;&#24320;&#20219;&#21153;&#20013;&#24515;</button>
          </div>
        </div>
        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#35831;&#20808;&#36873;&#25321;&#19968;&#26465;&#38382;&#39064;</strong>
          <span class="feedback-state-copy">&#24038;&#20391;&#38382;&#39064;&#21345;&#29255;&#34987;&#36873;&#20013;&#21518;&#65292;&#36825;&#37324;&#20250;&#25552;&#20379;&#30452;&#25509;&#22797;&#30424;&#30340;&#20837;&#21475;&#12290;</span>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getAnalysisReport, listAnalysisReports } from "../api/pipelines";
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

const refreshLabel = "刷新列表";
const refreshLoadingLabel = "刷新中...";
const searchPlaceholder = "搜索教师或学员素材名称";

const loading = ref(false);
const error = ref("");
const reports = ref<AnalysisReportItem[]>([]);
const issueMap = ref<Record<string, IssueReplayItem[]>>({});
const keyword = ref("");
const issueTypeFilter = ref("all");
const severityFilter = ref("all");
const limit = ref(50);
const selectedIssueId = ref("");

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
      action: "可先聚焦这段的拍点、重心转移和动作发力节奏。",
      finishedAt: report.finished_at || report.updated_at,
      scoreTotal: report.score_total,
      confidenceScore: report.confidence_score,
    });
  }

  const confidenceIssues = Array.isArray(report.report?.confidence?.issues) ? report.report?.confidence?.issues : [];
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
      summary: String(issue?.message || report.confidence_summary || "本轮分析存在可信度风险。"),
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
    error.value = err?.response?.data?.detail ?? err?.message ?? "问题回放列表加载失败";
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
      selectedIssueId.value = hit.id;
      return;
    }
  }
  if (!selectedIssueId.value || !filteredIssues.value.some((item) => item.id === selectedIssueId.value)) {
    selectedIssueId.value = filteredIssues.value[0]?.id || "";
  }
}

async function refreshPage() {
  await loadReports();
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
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, 0.92fr);
  gap: 16px;
}

.issue-list,
.detail-stack {
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

.summary-stack {
  display: grid;
  gap: 10px;
}

.summary-row {
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.summary-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.detail-panel {
  min-height: 100%;
}

.issue-links {
  margin-top: 4px;
}

@media (max-width: 1180px) {
  .issue-layout {
    grid-template-columns: 1fr;
  }
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
