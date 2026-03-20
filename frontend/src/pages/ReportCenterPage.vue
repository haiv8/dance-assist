<template>
  <main class="app-page report-page">
    <section class="surface-card page-head">
      <div class="page-head-row">
        <div>
          <h1>&#25253;&#21578;&#20013;&#24515;</h1>
          <p class="page-subtitle">&#25226;&#24050;&#23436;&#25104;&#20998;&#26512;&#21333;&#29420;&#25910;&#25104;&#21382;&#21490;&#32467;&#26524;&#24211;&#65292;&#26041;&#20415;&#25353;&#21517;&#31216;&#12289;&#24471;&#20998;&#21644;&#21487;&#20449;&#24230;&#24555;&#36895;&#22238;&#30475;&#26377;&#25928;&#32467;&#35770;&#12290;</p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="loading" @click="refreshReports">
            {{ loading ? "\u5237\u65b0\u4e2d..." : "\u5237\u65b0\u62a5\u544a" }}
          </button>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell">
          <span class="status-caption">&#25253;&#21578;&#24635;&#25968;</span>
          <strong class="status-main">{{ reports.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">&#24179;&#22343;&#24471;&#20998;</span>
          <strong class="status-main">{{ averageScoreText }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">&#24179;&#22343;&#21487;&#20449;&#24230;</span>
          <strong class="status-main">{{ averageConfidenceText }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">&#20302;&#21487;&#20449;&#24230;&#25253;&#21578;</span>
          <strong class="status-main">{{ lowConfidenceCount }}</strong>
        </div>
      </div>
    </section>

    <section class="selection-grid report-summary-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#31579;&#36873;&#22120;</h2>
            <p class="helper-text">&#20808;&#32553;&#23567;&#32467;&#26524;&#33539;&#22260;&#65292;&#20877;&#26597;&#30475;&#21491;&#20391;&#25253;&#21578;&#25688;&#35201;&#65292;&#20250;&#27604;&#22312;&#20219;&#21153;&#39029;&#37324;&#32763;&#25214;&#26356;&#39640;&#25928;&#12290;</p>
          </div>
        </div>

        <div class="field-grid two-col-fields">
          <div class="field-block report-search-field">
            <label class="field-label">&#21517;&#31216;&#26816;&#32034;</label>
            <input v-model.trim="keyword" type="text" placeholder="&#25628;&#32034;&#25945;&#24072;&#25110;&#23398;&#21592;&#32032;&#26448;&#21517;&#31216;" />
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

        <div class="field-grid two-col-fields filter-row">
          <div class="field-block">
            <label class="field-label">&#26368;&#20302;&#24635;&#20998;</label>
            <input v-model.number="minScore" type="number" min="0" max="100" step="1" />
          </div>
          <div class="field-block">
            <label class="field-label">&#26368;&#20302;&#21487;&#20449;&#24230;</label>
            <input v-model.number="minConfidencePercent" type="number" min="0" max="100" step="5" />
          </div>
        </div>

        <div v-if="error" class="feedback-inline" style="margin-top: 12px;">{{ error }}</div>
        <p v-else class="helper-text report-note">&#25253;&#21578;&#20013;&#24515;&#40664;&#35748;&#21482;&#23637;&#31034;&#24050;&#23436;&#25104;&#20998;&#26512;&#12290;&#21518;&#32493;&#22914;&#26524;&#25105;&#20204;&#34917; PDF &#25110;&#35757;&#32451;&#24314;&#35758;&#65292;&#20063;&#20250;&#20174;&#36825;&#37324;&#32487;&#32493;&#25193;&#23637;&#12290;</p>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#24403;&#21069;&#25253;&#21578;</h2>
            <p class="helper-text">&#32858;&#28966;&#26368;&#36817;&#19968;&#27425;&#26597;&#30475;&#30340;&#20998;&#26512;&#32467;&#26524;&#65292;&#26041;&#20415;&#20320;&#36830;&#32493;&#22797;&#30424;&#22810;&#26465;&#21382;&#21490;&#35760;&#24405;&#12290;</p>
          </div>
        </div>

        <div v-if="selectedReport" class="summary-stack">
          <div class="summary-row">
            <span>&#25253;&#21578;&#21517;&#31216;</span>
            <strong>{{ selectedReport.pair_name }}</strong>
          </div>
          <div class="summary-row">
            <span>&#24635;&#20998;</span>
            <strong>{{ scoreText(selectedReport.score_total) }}</strong>
          </div>
          <div class="summary-row">
            <span>&#21487;&#20449;&#24230;</span>
            <strong>{{ confidenceText(selectedReport.confidence_score) }}</strong>
          </div>
          <div class="summary-row">
            <span>&#26356;&#26032;&#26102;&#38388;</span>
            <strong>{{ formatDate(selectedReport.updated_at || selectedReport.finished_at) }}</strong>
          </div>
        </div>
        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#36824;&#27809;&#26377;&#31526;&#21512;&#26465;&#20214;&#30340;&#25253;&#21578;</strong>
          <span class="feedback-state-copy">&#20320;&#21487;&#20197;&#25918;&#23485;&#31579;&#36873;&#26465;&#20214;&#65292;&#25110;&#32773;&#22238;&#21040;&#21160;&#20316;&#20998;&#26512;&#39029;&#29983;&#25104;&#26032;&#30340;&#32467;&#26524;&#12290;</span>
        </div>
      </article>
    </section>

    <section class="report-layout">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#21382;&#21490;&#25253;&#21578;</h2>
            <p class="helper-text">&#21482;&#20445;&#30041;&#24050;&#23436;&#25104;&#20219;&#21153;&#65292;&#24182;&#25353;&#26368;&#36817;&#26356;&#26032;&#26102;&#38388;&#20502;&#24207;&#23637;&#31034;&#12290;</p>
          </div>
          <span class="tag">{{ filteredReports.length }} &#26465;&#32467;&#26524;</span>
        </div>

        <div v-if="loading && !reports.length" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">&#25253;&#21578;&#21015;&#34920;&#21152;&#36733;&#20013;</strong>
          <span class="feedback-state-copy">&#27491;&#22312;&#21516;&#27493;&#24050;&#23436;&#25104;&#20998;&#26512;&#65292;&#35831;&#31245;&#20505;&#12290;</span>
        </div>
        <div v-else-if="!filteredReports.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#24403;&#21069;&#31579;&#36873;&#19979;&#27809;&#26377;&#25253;&#21578;</strong>
          <span class="feedback-state-copy">&#35797;&#35797;&#35843;&#20302;&#20998;&#25968;&#38376;&#27083;&#12289;&#28165;&#31354;&#26816;&#32034;&#35789;&#65292;&#25110;&#37325;&#26032;&#29983;&#25104;&#26032;&#30340;&#20998;&#26512;&#32467;&#26524;&#12290;</span>
        </div>
        <div v-else class="report-list">
          <button
            v-for="item in filteredReports"
            :key="item.pipeline_id"
            type="button"
            class="report-item"
            :class="{ active: selectedReportId === item.pipeline_id }"
            @click="openReport(item.pipeline_id)"
          >
            <div class="report-item-head">
              <div>
                <strong>{{ item.pair_name }}</strong>
                <p class="helper-text">{{ item.pipeline_id }}</p>
              </div>
              <span class="tag" :class="confidenceTone(item.confidence_score)">{{ confidenceLevel(item.confidence_score) }}</span>
            </div>

            <div class="task-item-grid">
              <div class="metric-chip"><strong>&#24635;&#20998;</strong><span>{{ scoreText(item.score_total) }}</span></div>
              <div class="metric-chip"><strong>&#21487;&#20449;&#24230;</strong><span>{{ confidenceText(item.confidence_score) }}</span></div>
              <div class="metric-chip"><strong>&#25191;&#34892;&#22120;</strong><span>{{ item.executor || '--' }}</span></div>
            </div>

            <div class="task-item-meta">
              <span>&#23436;&#25104;&#26102;&#38388;&#65306;{{ formatDate(item.finished_at || item.updated_at) }}</span>
              <span>{{ stageText(item.stage) }}</span>
            </div>
          </button>
        </div>
      </article>

      <article class="surface-card detail-panel">
        <div class="panel-head compact-head">
          <div>
            <h2>&#25253;&#21578;&#25688;&#35201;</h2>
            <p class="helper-text">&#20248;&#20808;&#23637;&#31034;&#26412;&#36718;&#20998;&#26512;&#30340;&#39640;&#20215;&#20540;&#32467;&#35770;&#65292;&#19981;&#25226;&#25152;&#26377;&#25216;&#26415;&#32454;&#33410;&#22534;&#22312;&#39318;&#23631;&#12290;</p>
          </div>
          <div class="action-row" v-if="selectedReportId">
            <button class="secondary-button" :disabled="copying" @click="copyReportId">
              {{ copying ? "\u5df2\u590d\u5236" : "\u590d\u5236\u4efb\u52a1 ID" }}
            </button>
            <button class="secondary-button" @click="openTaskCenter">
              {{ "\u6253\u5f00\u4efb\u52a1\u4e2d\u5fc3" }}
            </button>
            <button class="secondary-button" :disabled="!canReopenInCompare" @click="reopenInCompare">
              {{ "\u56de\u5230\u52a8\u4f5c\u5206\u6790" }}
            </button>
          </div>
        </div>

        <div v-if="detailLoading" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">&#25253;&#21578;&#25688;&#35201;&#21152;&#36733;&#20013;</strong>
          <span class="feedback-state-copy">&#27491;&#22312;&#35835;&#21462;&#32467;&#26524;&#25688;&#35201;&#21644;&#36755;&#20986;&#25991;&#20214;&#65292;&#35831;&#31245;&#20505;&#12290;</span>
        </div>
        <div v-else-if="detailError" class="feedback-state" data-tone="error">
          <strong class="feedback-state-title">&#25253;&#21578;&#25688;&#35201;&#21152;&#36733;&#22833;&#36133;</strong>
          <span class="feedback-state-copy">{{ detailError }}</span>
        </div>
        <div v-else-if="detail" class="detail-stack">
          <div class="metric-row compact-stats">
            <div class="metric-chip"><strong>&#24635;&#20998;</strong><span>{{ scoreText(detail.report?.score_0_100 ?? detail.report?.scores?.score_total) }}</span></div>
            <div class="metric-chip"><strong>&#21160;&#20316;</strong><span>{{ scoreText(detail.report?.scores?.score_pose) }}</span></div>
            <div class="metric-chip"><strong>&#33410;&#22863;</strong><span>{{ scoreText(detail.report?.scores?.score_tempo) }}</span></div>
          </div>

          <div class="metric-row compact-stats">
            <div class="metric-chip"><strong>&#21487;&#20449;&#24230;</strong><span>{{ detailConfidenceText }}</span></div>
            <div class="metric-chip"><strong>&#38454;&#27573;</strong><span>{{ stageText(detail.stage) }}</span></div>
            <div class="metric-chip"><strong>&#23436;&#25104;&#26102;&#38388;</strong><span>{{ formatDate(detail.finished_at || detail.updated_at) }}</span></div>
          </div>

          <div class="list-item-card" v-if="detail.report?.recommendations?.overall">
            <strong>&#25972;&#20307;&#24314;&#35758;</strong>
            <span class="helper-text">{{ detail.report.recommendations.overall }}</span>
          </div>

          <div class="list-item-card" v-if="detail.report?.beginner_report?.summary">
            <strong>&#23398;&#21592;&#21453;&#39304;</strong>
            <span class="helper-text">{{ detail.report.beginner_report.summary }}</span>
          </div>

          <div class="list-item-card" v-if="detail.report?.teaching_report?.summary">
            <strong>&#25945;&#23398;&#24314;&#35758;</strong>
            <span class="helper-text">{{ detail.report.teaching_report.summary }}</span>
          </div>

          <div class="list-item-card" v-if="detail.report?.confidence?.summary">
            <strong>&#21487;&#20449;&#24230;&#35828;&#26126;</strong>
            <span class="helper-text">{{ detail.report.confidence.summary }}</span>
          </div>

          <div class="list-item-card" v-if="topJointSummary">
            <strong>&#37325;&#28857;&#20851;&#33410;</strong>
            <span class="helper-text">{{ topJointSummary }}</span>
          </div>

          <div class="action-row" v-if="canJumpToIssue">
            <button class="secondary-button" type="button" @click="jumpToIssueMoment">&#23450;&#20301;&#38382;&#39064;&#29255;&#27573;</button>
          </div>

          <div class="detail-links" v-if="detail.files">
            <a v-if="detail.files.report_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.report_url)" target="_blank">&#25171;&#24320;&#25253;&#21578; JSON</a>
            <a v-if="detail.files.summary_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.summary_url)" target="_blank">&#25171;&#24320;&#25688;&#35201; JSON</a>
            <a v-if="detail.files.teacher_overlay_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.teacher_overlay_url)" target="_blank">&#25945;&#24072;&#39592;&#26550;&#35270;&#39057;</a>
            <a v-if="detail.files.user_overlay_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.user_overlay_url)" target="_blank">&#23398;&#21592;&#39592;&#26550;&#35270;&#39057;</a>
            <a v-if="detail.files.timeline_json_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.timeline_json_url)" target="_blank">&#26102;&#38388;&#36724; JSON</a>
            <button class="secondary-button" type="button" @click="openTaskCenter">&#25171;&#24320;&#20219;&#21153;&#20013;&#24515;</button>
            <button class="secondary-button" type="button" :disabled="!canReopenInCompare" @click="reopenInCompare">&#22238;&#21040;&#21160;&#20316;&#20998;&#26512;</button>
          </div>
        </div>
        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#35831;&#36873;&#25321;&#19968;&#26465;&#25253;&#21578;</strong>
          <span class="feedback-state-copy">&#28857;&#20987;&#24038;&#20391;&#25253;&#21578;&#21345;&#29255;&#21518;&#65292;&#36825;&#37324;&#20250;&#23637;&#31034;&#23545;&#24212;&#30340;&#24314;&#35758;&#25688;&#35201;&#21644;&#36755;&#20986;&#25991;&#20214;&#12290;</span>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { absMediaUrl } from "../api/http";
import { getAnalysisReport, listAnalysisReports } from "../api/pipelines";
import type { AnalysisReportDetailResponse, AnalysisReportItem } from "../types/video";

const router = useRouter();
const route = useRoute();

const reports = ref<AnalysisReportItem[]>([]);
const loading = ref(false);
const error = ref("");
const detailLoading = ref(false);
const detailError = ref("");
const detail = ref<AnalysisReportDetailResponse | null>(null);
const selectedReportId = ref("");
const limit = ref(50);
const keyword = ref("");
const minScore = ref(0);
const minConfidencePercent = ref(0);
const copying = ref(false);

const filteredReports = computed(() => {
  const needle = keyword.value.trim().toLowerCase();
  const scoreFloor = Number(minScore.value) || 0;
  const confidenceFloor = (Number(minConfidencePercent.value) || 0) / 100;
  return reports.value.filter((item) => {
    const matchesKeyword = !needle || item.pair_name.toLowerCase().includes(needle);
    const score = Number(item.score_total);
    const confidence = Number(item.confidence_score);
    const matchesScore = !Number.isFinite(score) || score >= scoreFloor;
    const matchesConfidence = !Number.isFinite(confidence) || confidence >= confidenceFloor;
    return matchesKeyword && matchesScore && matchesConfidence;
  });
});
const selectedReport = computed(() => filteredReports.value.find((item) => item.pipeline_id === selectedReportId.value) ?? null);
const averageScoreText = computed(() => averageText(reports.value.map((item) => Number(item.score_total)), 1));
const averageConfidenceText = computed(() => {
  const values = reports.value.map((item) => Number(item.confidence_score)).filter((value) => Number.isFinite(value));
  if (!values.length) return "--";
  const total = values.reduce((sum, value) => sum + value, 0);
  return `${Math.round((total / values.length) * 100)}%`;
});
const lowConfidenceCount = computed(() => reports.value.filter((item) => Number.isFinite(Number(item.confidence_score)) && Number(item.confidence_score) < 0.6).length);
const detailConfidenceText = computed(() => confidenceText(detail.value?.report?.confidence?.score));
const topJointSummary = computed(() => {
  const joints = detail.value?.report?.top_joints;
  if (!Array.isArray(joints) || !joints.length) return "";
  return joints.slice(0, 3).map((item: any) => `${item[0]} (${Number(item[1]).toFixed(3)})`).join("\u3001");
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
    if (Number.isFinite(sec)) {
      return { sec, frame: Number(marker?.frame) };
    }
  }
  const tempoSegments = detail.value?.report?.tempo_segments;
  if (Array.isArray(tempoSegments) && tempoSegments.length) {
    const segment = tempoSegments[0] as any;
    const sec = Number(segment?.start_sec ?? segment?.sec ?? segment?.t0);
    if (Number.isFinite(sec)) {
      return { sec, frame: null };
    }
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
      selectedReportId.value = "";
      detail.value = null;
      return;
    }
    alignSelection(options);
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? "\u62a5\u544a\u5217\u8868\u52a0\u8f7d\u5931\u8d25";
  } finally {
    loading.value = false;
  }
}

function alignSelection(options?: { openFirst?: boolean; keepSelection?: boolean }) {
  const currentList = filteredReports.value;
  if (!currentList.length) {
    selectedReportId.value = "";
    detail.value = null;
    return;
  }
  const hasSelection = selectedReportId.value && currentList.some((item) => item.pipeline_id === selectedReportId.value);
  if (options?.openFirst || (!hasSelection && !options?.keepSelection)) {
    void openReport(currentList[0].pipeline_id);
  } else if (!hasSelection) {
    selectedReportId.value = currentList[0].pipeline_id;
  }
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
  } catch (err: any) {
    detail.value = null;
    detailError.value = err?.response?.data?.detail ?? err?.message ?? "\u62a5\u544a\u6458\u8981\u52a0\u8f7d\u5931\u8d25";
  } finally {
    detailLoading.value = false;
  }
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
    detailError.value = "\u590d\u5236\u5931\u8d25\uff0c\u8bf7\u624b\u52a8\u590d\u5236\u4efb\u52a1 ID\u3002";
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
  if (stage === "queued") return "\u5df2\u8fdb\u5165\u961f\u5217";
  if (stage === "preparing_inputs") return "\u51c6\u5907\u7d20\u6750";
  if (stage === "extracting_pose") return "\u63d0\u53d6\u9aa8\u67b6";
  if (stage === "aligning_motion") return "\u52a8\u4f5c\u5bf9\u9f50\u4e0e\u8bc4\u5206";
  if (stage === "rendering_outputs") return "\u751f\u6210\u5bf9\u6bd4\u8f93\u51fa";
  if (stage === "packaging_results") return "\u6574\u7406\u7ed3\u679c";
  if (stage === "completed") return "\u7ed3\u679c\u5df2\u5c31\u7eea";
  if (stage === "failed") return "\u4efb\u52a1\u5931\u8d25";
  return "\u5df2\u5b8c\u6210";
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
  if (!Number.isFinite(num)) return "\u5f85\u5b9a";
  if (num >= 0.8) return "\u9ad8\u53ef\u4fe1";
  if (num >= 0.6) return "\u4e2d\u53ef\u4fe1";
  return "\u4f4e\u53ef\u4fe1";
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

watch(filteredReports, () => {
  alignSelection({ keepSelection: true });
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
}

.report-search-field {
  grid-column: span 1;
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
  grid-template-columns: minmax(0, 1.1fr) minmax(340px, 0.9fr);
  gap: 16px;
}

.report-list,
.detail-stack {
  display: grid;
  gap: 12px;
}

.report-item {
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

.report-item:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(226, 109, 61, 0.18);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.report-item.active {
  border-color: rgba(226, 109, 61, 0.32);
  background: linear-gradient(180deg, rgba(255, 248, 243, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.report-item-head,
.task-item-meta,
.detail-links,
.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.report-item-head strong {
  display: block;
  margin-bottom: 4px;
}

.report-item-head p {
  margin: 0;
}

.summary-stack,
.task-item-grid {
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

@media (max-width: 1180px) {
  .report-layout {
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
  .report-item-head,
  .task-item-meta,
  .detail-links,
  .summary-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
