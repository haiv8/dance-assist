<template>
  <main class="app-page report-page">
    <section class="surface-card page-head">
      <div class="page-head-row">
        <div>
          <h1>报告中心</h1>
          <p class="page-subtitle">集中查看已完成分析的结果摘要、评分、可信度与输出文件，点击任意报告即可在当前卡片下方原位展开详情。</p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="loading" @click="refreshReports">
            {{ loading ? "刷新中..." : "刷新报告" }}
          </button>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell">
          <span class="status-caption">报告总数</span>
          <strong class="status-main">{{ reports.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">平均得分</span>
          <strong class="status-main">{{ averageScoreText }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">平均可信度</span>
          <strong class="status-main">{{ averageConfidenceText }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">低可信度报告</span>
          <strong class="status-main">{{ lowConfidenceCount }}</strong>
        </div>
      </div>
    </section>

    <section class="selection-grid report-summary-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>筛选与说明</h2>
            <p class="helper-text">先按名称、得分和可信度缩小范围，再点开某条报告查看详情。</p>
          </div>
        </div>

        <div class="field-grid two-col-fields">
          <div class="field-block">
            <label class="field-label">报告检索</label>
            <input v-model.trim="keyword" type="text" placeholder="按组合名称搜索" />
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

        <div class="field-grid two-col-fields filter-row">
          <div class="field-block">
            <label class="field-label">最低得分</label>
            <input v-model.number="minScore" type="number" min="0" max="100" step="1" />
          </div>
          <div class="field-block">
            <label class="field-label">最低可信度</label>
            <input v-model.number="minConfidencePercent" type="number" min="0" max="100" step="5" />
          </div>
        </div>

        <div v-if="error" class="feedback-inline" style="margin-top: 12px;">{{ error }}</div>
        <p v-else class="helper-text report-note">{{ filterSummary }}</p>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>当前焦点</h2>
            <p class="helper-text">这里显示当前展开报告的核心信息，方便快速浏览。</p>
          </div>
          <span v-if="selectedReport" class="tag" :class="confidenceTone(selectedReport.confidence_score)">
            {{ confidenceLevel(selectedReport.confidence_score) }}
          </span>
        </div>

        <div v-if="selectedReport" class="summary-stack">
          <div class="summary-row">
            <span>报告名称</span>
            <strong>{{ selectedReport.pair_name || selectedReport.pipeline_id }}</strong>
          </div>
          <div class="summary-row">
            <span>总分</span>
            <strong>{{ scoreText(selectedReport.score_total) }}</strong>
          </div>
          <div class="summary-row">
            <span>可信度</span>
            <strong>{{ confidenceText(selectedReport.confidence_score) }}</strong>
          </div>
          <div class="summary-row">
            <span>更新时间</span>
            <strong>{{ formatDate(selectedReport.updated_at || selectedReport.finished_at) }}</strong>
          </div>
        </div>
        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">当前没有聚焦的报告</strong>
          <span class="feedback-state-copy">点开下方任意一条报告后，这里会同步显示摘要信息。</span>
        </div>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>导航提示</h2>
            <p class="helper-text">建议优先查看高分且高可信度的结果，再决定是否回到任务中心或动作分析页继续排查。</p>
          </div>
        </div>

        <div class="summary-stack">
          <div class="summary-row">
            <span>筛选结果</span>
            <strong>{{ filteredReports.length }} 条</strong>
          </div>
          <div class="summary-row">
            <span>最低得分</span>
            <strong>{{ Number(minScore) || 0 }}</strong>
          </div>
          <div class="summary-row">
            <span>最低可信度</span>
            <strong>{{ Number(minConfidencePercent) || 0 }}%</strong>
          </div>
          <div class="summary-row">
            <span>可回到动作分析</span>
            <strong>{{ canReopenInCompare ? "可以" : "待完整视频配对" }}</strong>
          </div>
        </div>
      </article>
    </section>

    <section class="report-layout">
      <article class="surface-card report-archive-panel">
        <div class="panel-head compact-head">
          <div>
            <h2>报告列表</h2>
            <p class="helper-text">按最近更新时间倒序排列，点开后详情会直接出现在当前卡片下方。</p>
          </div>
          <span class="tag">{{ filteredReports.length }} 条</span>
        </div>

        <div v-if="loading && !reports.length" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">报告列表加载中</strong>
          <span class="feedback-state-copy">正在同步最近完成的分析结果，请稍候。</span>
        </div>
        <div v-else-if="!filteredReports.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">当前筛选下没有报告</strong>
          <span class="feedback-state-copy">可以降低筛选门槛，或回到动作分析页生成新的结果。</span>
        </div>
        <div v-else class="report-list">
          <div v-for="(item, index) in filteredReports" :key="item.pipeline_id" class="report-item-shell">
            <button
              type="button"
              class="report-item"
              :class="{ active: selectedReportId === item.pipeline_id }"
              @click="toggleReport(item.pipeline_id)"
            >
              <div class="report-item-topline">
                <span class="report-item-index">#{{ String(index + 1).padStart(2, "0") }}</span>
                <span class="tag" :class="confidenceTone(item.confidence_score)">{{ confidenceLevel(item.confidence_score) }}</span>
              </div>

              <div class="report-item-head">
                <div>
                  <strong>{{ item.pair_name || item.pipeline_id }}</strong>
                  <p class="helper-text">{{ item.pipeline_id }}</p>
                </div>
              </div>

              <p class="helper-text report-item-copy">{{ reportLead(item) }}</p>

              <div class="task-item-grid report-item-metrics">
                <div class="metric-chip"><strong>总分</strong><span>{{ scoreText(item.score_total) }}</span></div>
                <div class="metric-chip"><strong>可信度</strong><span>{{ confidenceText(item.confidence_score) }}</span></div>
                <div class="metric-chip"><strong>执行器</strong><span>{{ item.executor || "--" }}</span></div>
              </div>

              <div class="task-item-meta">
                <span>完成时间：{{ formatDate(item.finished_at || item.updated_at) }}</span>
                <span>{{ stageText(item.stage) }}</span>
              </div>
            </button>

            <div
              v-if="selectedReportId === item.pipeline_id"
              ref="detailPanelRef"
              class="report-inline-detail report-monograph-panel"
            >
              <div class="panel-head compact-head">
                <div>
                  <h2>报告详情</h2>
                  <p class="helper-text">展开内容直接跟在当前报告下方，阅读路径会更连贯。</p>
                </div>
                <div class="action-row">
                  <button class="ghost-button danger-button" :disabled="deletingReport" @click="deleteSelectedReport">
                    {{ deletingReport ? "删除中..." : "删除报告" }}
                  </button>
                  <button class="secondary-button" :disabled="copying" @click="copyReportId">
                    {{ copying ? "已复制" : "复制任务 ID" }}
                  </button>
                  <button class="secondary-button" @click="openTaskCenter">打开任务中心</button>
                  <button class="secondary-button" :disabled="!canReopenInCompare" @click="reopenInCompare">回到动作分析</button>
                </div>
              </div>

              <div v-if="detailLoading" class="feedback-state" data-tone="loading">
                <strong class="feedback-state-title">报告详情加载中</strong>
                <span class="feedback-state-copy">正在读取结果摘要和输出文件，请稍候。</span>
              </div>
              <div v-else-if="detailError" class="feedback-state" data-tone="error">
                <strong class="feedback-state-title">报告详情加载失败</strong>
                <span class="feedback-state-copy">{{ detailError }}</span>
              </div>
              <div v-else-if="detail" class="detail-stack report-monograph-stack">
                <div class="report-monograph-head">
                  <p class="report-kicker">Report Summary</p>
                  <h2>{{ detail.pair_name || detail.pipeline_id }}</h2>
                  <div class="report-summary-band">
                    <span class="tag" :class="confidenceTone(detail.report?.confidence?.score ?? detail.confidence_score)">
                      {{ confidenceLevel(detail.report?.confidence?.score ?? detail.confidence_score) }}
                    </span>
                    <span class="tag neutral">{{ stageText(detail.stage) }}</span>
                    <span class="tag neutral">{{ formatDate(detail.finished_at || detail.updated_at) }}</span>
                  </div>
                  <p class="helper-text report-monograph-copy">{{ detailLead }}</p>
                </div>

                <div class="report-scoreboard">
                  <div v-for="card in detailScoreCards" :key="card.label" class="metric-chip report-score-card">
                    <strong>{{ card.label }}</strong>
                    <span>{{ card.value }}</span>
                  </div>
                </div>

                <div class="report-reading-layout">
                  <div class="monograph-column">
                    <div v-for="section in detailNarrativeSections" :key="section.title" class="list-item-card monograph-card">
                      <strong>{{ section.title }}</strong>
                      <span class="helper-text">{{ section.body }}</span>
                    </div>
                  </div>

                  <div class="monograph-column secondary-column">
                    <div class="list-item-card monograph-card" v-if="detailSignalItems.length">
                      <strong>关键信号</strong>
                      <div class="summary-stack signal-stack">
                        <div v-for="signal in detailSignalItems" :key="signal.label" class="summary-row">
                          <span>{{ signal.label }}</span>
                          <strong>{{ signal.value }}</strong>
                        </div>
                      </div>
                    </div>

                    <div class="list-item-card monograph-card" v-if="detailLinks.length">
                      <strong>输出文件</strong>
                      <div class="detail-links output-link-grid">
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

                    <div class="list-item-card monograph-card emphasis-card" v-if="canJumpToIssue">
                      <strong>快速复盘入口</strong>
                      <span class="helper-text">检测到可定位的问题片段，可以直接跳到动作分析页查看对应时刻。</span>
                      <div class="action-row report-action-row">
                        <button class="secondary-button" type="button" @click="jumpToIssueMoment">定位问题片段</button>
                        <button class="secondary-button" type="button" @click="openTaskCenter">打开任务中心</button>
                      </div>
                    </div>
                  </div>
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
import { absMediaUrl } from "../api/http";
import { deletePipelineTask, getAnalysisReport, listAnalysisReports } from "../api/pipelines";
import { focusDetailPanel } from "../utils/detailPanel";
import { normalizedConfidenceSummary } from "../utils/confidence";
import { friendlyError } from "../utils/errors";
import type { AnalysisReportDetailResponse, AnalysisReportItem } from "../types/video";

type DetailTextSection = {
  title: string;
  body: string;
};

type DetailLinkItem = {
  label: string;
  url: string;
};

const router = useRouter();
const route = useRoute();

const reports = ref<AnalysisReportItem[]>([]);
const loading = ref(false);
const error = ref("");
const detailLoading = ref(false);
const detailError = ref("");
const detail = ref<AnalysisReportDetailResponse | null>(null);
const detailPanelRef = ref<HTMLElement | null>(null);
const selectedReportId = ref("");
const limit = ref(50);
const keyword = ref("");
const minScore = ref(0);
const minConfidencePercent = ref(0);
const copying = ref(false);
const deletingReport = ref(false);

const filteredReports = computed(() => {
  const needle = keyword.value.trim().toLowerCase();
  const scoreFloor = Number(minScore.value) || 0;
  const confidenceFloor = (Number(minConfidencePercent.value) || 0) / 100;
  return reports.value.filter((item) => {
    const name = (item.pair_name || item.pipeline_id || "").toLowerCase();
    const matchesKeyword = !needle || name.includes(needle);
    const score = Number(item.score_total);
    const confidence = Number(item.confidence_score);
    const matchesScore = !Number.isFinite(score) || score >= scoreFloor;
    const matchesConfidence = !Number.isFinite(confidence) || confidence >= confidenceFloor;
    return matchesKeyword && matchesScore && matchesConfidence;
  });
});

const selectedReport = computed(() => filteredReports.value.find((item) => item.pipeline_id === selectedReportId.value) ?? null);
const filterSummary = computed(() => {
  return `当前筛选得到 ${filteredReports.value.length} 条报告，建议优先查看高分且高可信度的结果。`;
});
const averageScoreText = computed(() => averageText(reports.value.map((item) => Number(item.score_total)), 1));
const averageConfidenceText = computed(() => {
  const values = reports.value.map((item) => Number(item.confidence_score)).filter((value) => Number.isFinite(value));
  if (!values.length) return "--";
  const total = values.reduce((sum, value) => sum + value, 0);
  return `${Math.round((total / values.length) * 100)}%`;
});
const lowConfidenceCount = computed(() => reports.value.filter((item) => Number(item.confidence_score) < 0.6).length);
const detailConfidenceText = computed(() => confidenceText(detail.value?.report?.confidence?.score ?? detail.value?.confidence_score));
const detailConfidenceSummaryText = computed(() =>
  normalizedConfidenceSummary(detail.value?.report?.confidence, detail.value?.confidence_summary),
);
const topJointSummary = computed(() => {
  const joints = detail.value?.report?.top_joints ?? detail.value?.top_joints;
  if (!Array.isArray(joints) || !joints.length) return "";
  return joints
    .slice(0, 3)
    .map((item: any) => `${item[0]} (${Number(item[1]).toFixed(3)})`)
    .join("、");
});
const detailLead = computed(() => {
  return (
    detail.value?.report?.recommendations?.overall ||
    detail.value?.overall_advice ||
    detail.value?.report?.beginner_report?.summary ||
    detail.value?.beginner_summary ||
    detail.value?.report?.teaching_report?.summary ||
    detail.value?.teaching_summary ||
    detailConfidenceSummaryText.value ||
    "当前报告已生成基础评分和摘要，可以继续查看输出文件。"
  );
});
const detailNarrativeSections = computed<DetailTextSection[]>(() => {
  const sections: DetailTextSection[] = [
    {
      title: "执行摘要",
      body:
        detail.value?.report?.beginner_report?.summary ||
        detail.value?.beginner_summary ||
        detail.value?.report?.recommendations?.overall ||
        detail.value?.overall_advice ||
        "",
    },
    {
      title: "教学建议",
      body: detail.value?.report?.teaching_report?.summary || detail.value?.teaching_summary || "",
    },
    {
      title: "可信度说明",
      body: detailConfidenceSummaryText.value,
    },
  ];
  return sections.filter((section) => section.body);
});
const detailSignalItems = computed(() => {
  const items = [
    { label: "可信度", value: detailConfidenceText.value },
    { label: "阶段", value: stageText(detail.value?.stage) },
    { label: "完成时间", value: formatDate(detail.value?.finished_at || detail.value?.updated_at) },
    { label: "重点关节", value: topJointSummary.value || "--" },
  ];
  return items.filter((item) => item.value && item.value !== "--");
});
const detailScoreCards = computed(() => [
  { label: "总分", value: scoreText(detail.value?.report?.score_0_100 ?? detail.value?.report?.scores?.score_total ?? detail.value?.score_total) },
  { label: "动作", value: scoreText(detail.value?.report?.scores?.score_pose ?? detail.value?.score_pose) },
  { label: "节奏", value: scoreText(detail.value?.report?.scores?.score_tempo ?? detail.value?.score_tempo) },
  { label: "可信度", value: detailConfidenceText.value },
]);
const detailLinks = computed<DetailLinkItem[]>(() => {
  const files = detail.value?.files || {};
  const links = [
    { label: "打开报告 JSON", url: files.report_url },
    { label: "打开摘要 JSON", url: files.summary_url },
    { label: "教师骨架视频", url: files.teacher_overlay_url },
    { label: "学员骨架视频", url: files.user_overlay_url },
    { label: "时间轴 JSON", url: files.timeline_json_url },
  ];
  return links.filter((item) => item.url).map((item) => ({ label: item.label, url: absMediaUrl(item.url) }));
});
const selectedReportQuery = computed(() => {
  const report = selectedReport.value;
  if (!report) return null;
  return {
    pipeline: report.pipeline_id,
    teacher: report.teacher_video_id || undefined,
    user: report.user_video_id || undefined,
  };
});
const canReopenInCompare = computed(() => Boolean(selectedReport.value?.teacher_video_id && selectedReport.value?.user_video_id));
const firstIssueMoment = computed(() => {
  const markers = detail.value?.report?.markers;
  if (Array.isArray(markers) && markers.length) {
    const marker = markers.find((item: any) => Number.isFinite(Number(item?.sec))) || markers[0];
    const sec = Number(marker?.sec);
    if (Number.isFinite(sec)) return { sec, frame: Number(marker?.frame) };
  }
  const tempoSegments = detail.value?.report?.tempo_segments;
  if (Array.isArray(tempoSegments) && tempoSegments.length) {
    const segment = tempoSegments[0] as any;
    const sec = Number(segment?.start_sec ?? segment?.sec ?? segment?.t0);
    if (Number.isFinite(sec)) return { sec, frame: null };
  }
  return null;
});
const canJumpToIssue = computed(() => Boolean(canReopenInCompare.value && firstIssueMoment.value));

async function loadReports(options?: { openFirst?: boolean; keepSelection?: boolean }) {
  loading.value = true;
  error.value = "";
  try {
    const data = await listAnalysisReports({
      limit: limit.value,
      q: keyword.value.trim() || undefined,
      min_score: Number(minScore.value) || undefined,
      min_confidence: ((Number(minConfidencePercent.value) || 0) / 100) || undefined,
    });
    reports.value = data.items;

    if (!reports.value.length) {
      closeReportDetail();
      return;
    }

    const hasSelection = selectedReportId.value && filteredReports.value.some((item) => item.pipeline_id === selectedReportId.value);
    if (options?.openFirst || (!hasSelection && !options?.keepSelection)) {
      await openReport(filteredReports.value[0]?.pipeline_id || reports.value[0].pipeline_id);
    } else if (!hasSelection) {
      selectedReportId.value = filteredReports.value[0]?.pipeline_id || "";
    }
  } catch (err: any) {
    error.value = friendlyError(err, "报告列表加载失败");
  } finally {
    loading.value = false;
  }
}

function closeReportDetail() {
  selectedReportId.value = "";
  detail.value = null;
  detailError.value = "";
}

async function refreshReports() {
  await loadReports({ keepSelection: true });
}

async function openReport(pipelineId: string) {
  selectedReportId.value = pipelineId;
  detailLoading.value = true;
  detailError.value = "";
  try {
    detail.value = await getAnalysisReport(pipelineId);
    focusDetailPanel(detailPanelRef, { forceScroll: true });
  } catch (err: any) {
    detail.value = null;
    detailError.value = friendlyError(err, "报告详情加载失败");
  } finally {
    detailLoading.value = false;
  }
}

async function toggleReport(pipelineId: string) {
  if (pipelineId === selectedReportId.value && detail.value) {
    closeReportDetail();
    return;
  }
  await openReport(pipelineId);
}

async function copyReportId() {
  if (!selectedReportId.value) return;
  try {
    await navigator.clipboard.writeText(selectedReportId.value);
    copying.value = true;
    window.setTimeout(() => {
      copying.value = false;
    }, 1400);
  } catch {
    detailError.value = "复制失败，请手动复制任务 ID。";
  }
}

async function deleteSelectedReport() {
  const pipelineId = selectedReportId.value;
  const currentReport = selectedReport.value;
  if (!pipelineId || !currentReport) return;

  const confirmed = window.confirm(`确认删除报告“${currentReport.pair_name || currentReport.pipeline_id}”吗？删除后相关历史记录会一起移除。`);
  if (!confirmed) return;

  deletingReport.value = true;
  detailError.value = "";
  try {
    await deletePipelineTask(pipelineId);
    reports.value = reports.value.filter((item) => item.pipeline_id !== pipelineId);

    const nextReport = filteredReports.value[0] ?? null;
    if (!nextReport) {
      closeReportDetail();
      return;
    }

    await openReport(nextReport.pipeline_id);
  } catch (err: any) {
    detailError.value = friendlyError(err, "删除报告失败");
  } finally {
    deletingReport.value = false;
  }
}

function openTaskCenter() {
  if (!selectedReportId.value) return;
  void router.push({ path: "/tasks", query: { pipeline: selectedReportId.value } });
}

function reopenInCompare() {
  const query = selectedReportQuery.value;
  if (!query?.teacher || !query?.user) return;
  void router.push({ path: "/compare", query });
}

function jumpToIssueMoment() {
  const query = selectedReportQuery.value;
  const issue = firstIssueMoment.value;
  if (!query?.teacher || !query?.user || !issue) return;
  void router.push({
    path: "/compare",
    query: {
      ...query,
      sec: String(issue.sec),
      mode: "local",
    },
  });
}

function stageText(stage?: string | null) {
  if (stage === "queued") return "已进入队列";
  if (stage === "preparing_inputs") return "准备素材";
  if (stage === "extracting_pose") return "提取骨架";
  if (stage === "aligning_motion") return "动作对齐与评分";
  if (stage === "rendering_outputs") return "生成对比输出";
  if (stage === "packaging_results") return "整理结果";
  if (stage === "completed") return "结果已就绪";
  if (stage === "failed") return "任务失败";
  if (stage === "canceled") return "任务已取消";
  return "已完成";
}

function scoreText(value?: number | string | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return num.toFixed(1);
}

function confidenceText(value?: number | string | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return `${Math.round(num * 100)}%`;
}

function averageText(values: number[], digits = 0) {
  const list = values.filter((value) => Number.isFinite(value));
  if (!list.length) return "--";
  const total = list.reduce((sum, value) => sum + value, 0);
  return (total / list.length).toFixed(digits);
}

function confidenceLevel(value?: number | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "待定";
  if (num >= 0.8) return "高可信";
  if (num >= 0.6) return "中可信";
  return "低可信";
}

function confidenceTone(value?: number | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "neutral";
  if (num >= 0.8) return "ok";
  if (num >= 0.6) return "warn";
  return "danger";
}

function formatDate(value?: string | null) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function reportLead(report: Partial<AnalysisReportItem>) {
  return (
    report.overall_advice ||
    report.beginner_summary ||
    report.teaching_summary ||
    normalizedConfidenceSummary(null, report.confidence_summary) ||
    "报告已生成评分、摘要和可查看的输出文件。"
  );
}

watch(filteredReports, () => {
  if (!filteredReports.value.length) {
    closeReportDetail();
    return;
  }
  if (selectedReportId.value && filteredReports.value.some((item) => item.pipeline_id === selectedReportId.value)) {
    return;
  }
  selectedReportId.value = filteredReports.value[0].pipeline_id;
});

watch(limit, () => {
  void loadReports({ openFirst: true });
});

onMounted(async () => {
  await loadReports({ openFirst: true });
  const pipelineQuery = typeof route.query.pipeline === "string" ? route.query.pipeline : "";
  if (pipelineQuery) {
    await openReport(pipelineQuery);
  }
});
</script>

<style scoped>
.report-summary-grid {
  align-items: start;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.filter-row {
  margin-top: 4px;
}

.report-note {
  margin-top: 14px;
  line-height: 1.7;
}

.report-layout {
  display: grid;
  gap: 16px;
}

.report-list,
.detail-stack,
.monograph-column,
.output-link-grid,
.report-item-shell,
.summary-stack {
  display: grid;
  gap: 12px;
}

.report-archive-panel,
.report-monograph-panel {
  position: relative;
  overflow: hidden;
}

.report-monograph-panel {
  background: linear-gradient(180deg, rgba(251, 248, 242, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.report-item {
  display: grid;
  gap: 12px;
  width: 100%;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.98);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

.report-item:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(226, 109, 61, 0.18);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.report-item.active {
  border-color: rgba(226, 109, 61, 0.3);
  background: linear-gradient(180deg, rgba(255, 248, 243, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.report-item-topline,
.report-item-head,
.task-item-meta,
.detail-links,
.summary-row,
.report-summary-band,
.report-action-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.report-item-head strong {
  display: block;
  margin-bottom: 4px;
  font-family: var(--font-display);
  font-size: 1.5rem;
  line-height: 1.02;
}

.report-item-head > div,
.report-item-copy,
.report-monograph-head,
.report-monograph-copy {
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.report-item-head p,
.report-item-copy,
.report-monograph-copy {
  margin: 0;
}

.report-item-copy,
.report-monograph-copy {
  line-height: 1.75;
}

.report-item-metrics {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.report-inline-detail {
  display: grid;
  gap: 18px;
  padding: 18px 20px 20px;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.report-monograph-stack {
  gap: 18px;
}

.report-monograph-head {
  display: grid;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.report-kicker,
.report-item-index {
  font-size: 0.72rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--accent-dark);
}

.report-monograph-head h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.2rem, 4vw, 3.8rem);
  line-height: 0.95;
}

.report-scoreboard {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.report-score-card {
  min-height: 96px;
  justify-content: space-between;
}

.report-score-card span {
  font-family: var(--font-display);
  font-size: 2rem;
  line-height: 1;
}

.summary-row {
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.summary-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.report-reading-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(280px, 0.95fr);
  gap: 14px;
}

.monograph-card {
  gap: 10px;
}

.emphasis-card {
  background: linear-gradient(180deg, rgba(255, 249, 244, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
  border-color: rgba(180, 78, 30, 0.18);
}

.output-link-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.danger-button {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.22);
}

.danger-button:hover:not(:disabled) {
  border-color: rgba(180, 35, 24, 0.4);
  background: rgba(180, 35, 24, 0.08);
}

@media (max-width: 1280px) {
  .report-summary-grid,
  .report-reading-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1024px) {
  .two-col-fields,
  .report-item-metrics,
  .report-scoreboard,
  .output-link-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .report-item-topline,
  .report-item-head,
  .task-item-meta,
  .detail-links,
  .summary-row,
  .report-summary-band,
  .report-action-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
