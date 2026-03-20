<template>
  <main class="app-page task-page">
    <section class="surface-card page-head">
      <div class="page-head-row">
        <div>
          <h1>&#20219;&#21153;&#20013;&#24515;</h1>
          <p class="page-subtitle">&#38598;&#20013;&#26597;&#30475;&#20998;&#26512;&#20219;&#21153;&#30340;&#29366;&#24577;&#12289;&#36827;&#24230;&#12289;&#24471;&#20998;&#19982;&#21487;&#20449;&#24230;&#65292;&#35753;&#21382;&#21490;&#20219;&#21153;&#21644;&#24403;&#21069;&#25191;&#34892;&#19968;&#30446;&#20102;&#28982;&#12290;</p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="loading" @click="refreshTasks">
            {{ loading ? "\u5237\u65b0\u4e2d..." : "\u5237\u65b0\u4efb\u52a1" }}
          </button>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell">
          <span class="status-caption">&#20219;&#21153;&#24635;&#25968;</span>
          <strong class="status-main">{{ tasks.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">&#36827;&#34892;&#20013;</span>
          <strong class="status-main">{{ runningCount }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">&#24050;&#23436;&#25104;</span>
          <strong class="status-main">{{ doneCount }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">&#24179;&#22343;&#24471;&#20998;</span>
          <strong class="status-main">{{ averageScoreText }}</strong>
        </div>
      </div>
    </section>

    <section class="selection-grid task-summary-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#31579;&#36873;&#19982;&#35828;&#26126;</h2>
            <p class="helper-text">&#20808;&#25353;&#29366;&#24577;&#36807;&#28388;&#65292;&#20877;&#36827;&#20837;&#20219;&#21153;&#35814;&#24773;&#26597;&#30475;&#26412;&#36718;&#25688;&#35201;&#21644;&#36755;&#20986;&#25991;&#20214;&#12290;</p>
          </div>
        </div>

        <div class="field-grid two-col-fields">
          <div class="field-block">
            <label class="field-label">&#20219;&#21153;&#29366;&#24577;</label>
            <select v-model="statusFilter">
              <option value="all">&#20840;&#37096;&#29366;&#24577;</option>
              <option value="pending">&#31561;&#24453;&#20013;</option>
              <option value="running">&#20998;&#26512;&#20013;</option>
              <option value="done">&#24050;&#23436;&#25104;</option>
              <option value="failed">&#22833;&#36133;</option>
              <option value="canceled">&#24050;&#21462;&#28040;</option>
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
        <p v-else class="helper-text task-note">&#20219;&#21153;&#20013;&#24515;&#20248;&#20808;&#23637;&#31034;&#26368;&#26032;&#35760;&#24405;&#12290;&#28857;&#20987;&#21491;&#20391;&#35814;&#24773;&#21518;&#65292;&#21487;&#20197;&#32487;&#32493;&#26597;&#30475;&#26412;&#36718;&#24471;&#20998;&#12289;&#21487;&#20449;&#24230;&#21644;&#36755;&#20986;&#25991;&#20214;&#12290;</p>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#24403;&#21069;&#28966;&#28857;</h2>
            <p class="helper-text">&#40664;&#35748;&#32858;&#28966;&#26368;&#36817;&#19968;&#26465;&#20219;&#21153;&#65292;&#20063;&#21487;&#20197;&#20174;&#24038;&#20391;&#21015;&#34920;&#20999;&#25442;&#26597;&#30475;&#12290;</p>
          </div>
        </div>

        <div v-if="selectedTask" class="summary-stack">
          <div class="summary-row">
            <span>&#20219;&#21153;&#21517;&#31216;</span>
            <strong>{{ selectedTask.pair_name }}</strong>
          </div>
          <div class="summary-row">
            <span>&#29366;&#24577;</span>
            <strong>{{ statusText(selectedTask.status) }}</strong>
          </div>
          <div class="summary-row">
            <span>&#38454;&#27573;</span>
            <strong>{{ stageText(selectedTask.stage, selectedTask.status) }}</strong>
          </div>
          <div class="summary-row">
            <span>&#20219;&#21153; ID</span>
            <strong>{{ selectedTask.pipeline_id }}</strong>
          </div>
        </div>
        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#36824;&#27809;&#26377;&#21487;&#23637;&#31034;&#30340;&#20219;&#21153;</strong>
          <span class="feedback-state-copy">&#20808;&#22312;&#21160;&#20316;&#20998;&#26512;&#39029;&#21457;&#36215;&#20219;&#21153;&#65292;&#36825;&#37324;&#20250;&#33258;&#21160;&#21516;&#27493;&#26368;&#26032;&#29366;&#24577;&#19982;&#32467;&#26524;&#25688;&#35201;&#12290;</span>
        </div>
      </article>
    </section>

    <section class="task-layout">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#20219;&#21153;&#21015;&#34920;</h2>
            <p class="helper-text">&#25353;&#26356;&#26032;&#26102;&#38388;&#20502;&#24207;&#23637;&#31034;&#65292;&#36866;&#21512;&#24555;&#36895;&#23450;&#20301;&#21018;&#23436;&#25104;&#25110;&#21018;&#22833;&#36133;&#30340;&#20219;&#21153;&#12290;</p>
          </div>
          <span class="tag">{{ statusFilter === "all" ? "\u5168\u90e8" : statusText(statusFilter) }}</span>
        </div>

        <div v-if="loading && !tasks.length" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">&#20219;&#21153;&#21015;&#34920;&#21152;&#36733;&#20013;</strong>
          <span class="feedback-state-copy">&#27491;&#22312;&#21516;&#27493;&#26368;&#36817;&#30340;&#20998;&#26512;&#20219;&#21153;&#65292;&#35831;&#31245;&#20505;&#12290;</span>
        </div>
        <div v-else-if="!tasks.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#24403;&#21069;&#31579;&#36873;&#19979;&#27809;&#26377;&#20219;&#21153;</strong>
          <span class="feedback-state-copy">&#20320;&#21487;&#20197;&#20999;&#25442;&#29366;&#24577;&#31579;&#36873;&#65292;&#25110;&#22238;&#21040;&#21160;&#20316;&#20998;&#26512;&#39029;&#21457;&#36215;&#26032;&#30340;&#20998;&#26512;&#20219;&#21153;&#12290;</span>
        </div>
        <div v-else class="task-list">
          <button
            v-for="task in tasks"
            :key="task.pipeline_id"
            type="button"
            class="task-item"
            :class="{ active: selectedTaskId === task.pipeline_id }"
            @click="openTask(task.pipeline_id)"
          >
            <div class="task-item-head">
              <div>
                <strong>{{ task.pair_name }}</strong>
                <p class="helper-text">{{ task.pipeline_id }}</p>
              </div>
              <span class="tag" :class="statusTagClass(task.status)">{{ statusText(task.status) }}</span>
            </div>

            <div class="task-item-grid">
              <div class="metric-chip"><strong>&#38454;&#27573;</strong><span>{{ stageText(task.stage, task.status) }}</span></div>
              <div class="metric-chip"><strong>&#24635;&#20998;</strong><span>{{ scoreText(task.score_total) }}</span></div>
              <div class="metric-chip"><strong>&#21487;&#20449;&#24230;</strong><span>{{ confidenceText(task.confidence_score) }}</span></div>
            </div>

            <div class="mini-progress" v-if="task.status === 'pending' || task.status === 'running'">
              <div class="progress-head">
                <strong>&#24403;&#21069;&#36827;&#24230;</strong>
                <span>{{ progressPercent(task.progress) }}%</span>
              </div>
              <div class="progress-track"><div class="progress-fill" :style="{ width: `${progressPercent(task.progress)}%` }"></div></div>
            </div>

            <div class="task-item-meta">
              <span>&#26356;&#26032;&#26102;&#38388;&#65306;{{ formatDate(task.updated_at || task.finished_at || task.started_at || task.queued_at) }}</span>
              <span v-if="task.error_type">&#24322;&#24120;&#65306;{{ task.error_type }}</span>
              <span v-else>&#25191;&#34892;&#22120;&#65306;{{ task.executor || '--' }}</span>
            </div>
          </button>
        </div>
      </article>

      <article class="surface-card detail-panel">
        <div class="panel-head compact-head">
          <div>
            <h2>&#20219;&#21153;&#35814;&#24773;</h2>
            <p class="helper-text">&#32858;&#28966;&#24403;&#21069;&#20219;&#21153;&#30340;&#29366;&#24577;&#12289;&#25688;&#35201;&#21644;&#21487;&#30452;&#25509;&#25171;&#24320;&#30340;&#36755;&#20986;&#25991;&#20214;&#12290;</p>
          </div>
          <div class="action-row" v-if="selectedTaskId">
            <button class="ghost-button" :disabled="!canCancelSelectedTask || cancelingTask" @click="cancelSelectedTask">
              {{ cancelingTask ? "\u53d6\u6d88\u4e2d..." : "\u53d6\u6d88\u4efb\u52a1" }}
            </button>
            <button class="secondary-button" :disabled="copying" @click="copyTaskId">
              {{ copying ? "\u5df2\u590d\u5236" : "\u590d\u5236\u4efb\u52a1 ID" }}
            </button>
            <button class="secondary-button" @click="openReportCenter">
              {{ "\u6253\u5f00\u62a5\u544a\u4e2d\u5fc3" }}
            </button>
            <button class="secondary-button" :disabled="!canReopenInCompare" @click="reopenInCompare">
              {{ "\u56de\u5230\u52a8\u4f5c\u5206\u6790" }}
            </button>
          </div>
        </div>

        <div v-if="detailLoading" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">&#20219;&#21153;&#35814;&#24773;&#21152;&#36733;&#20013;</strong>
          <span class="feedback-state-copy">&#27491;&#22312;&#35835;&#21462;&#20219;&#21153;&#25688;&#35201;&#21644;&#36755;&#20986;&#25991;&#20214;&#65292;&#35831;&#31245;&#20505;&#12290;</span>
        </div>
        <div v-else-if="detailError" class="feedback-state" data-tone="error">
          <strong class="feedback-state-title">&#20219;&#21153;&#35814;&#24773;&#21152;&#36733;&#22833;&#36133;</strong>
          <span class="feedback-state-copy">{{ detailError }}</span>
        </div>
        <div v-else-if="detail" class="detail-stack">
          <div class="metric-row compact-stats">
            <div class="metric-chip"><strong>&#29366;&#24577;</strong><span>{{ statusText(detail.status) }}</span></div>
            <div class="metric-chip"><strong>&#38454;&#27573;</strong><span>{{ stageText(detail.stage, detail.status) }}</span></div>
            <div class="metric-chip"><strong>&#36827;&#24230;</strong><span>{{ progressPercent(detail.progress) }}%</span></div>
          </div>

          <div class="metric-row compact-stats">
            <div class="metric-chip"><strong>&#24635;&#20998;</strong><span>{{ scoreText(detail.report?.score_0_100 ?? detail.report?.scores?.score_total) }}</span></div>
            <div class="metric-chip"><strong>&#21160;&#20316;</strong><span>{{ scoreText(detail.report?.scores?.score_pose) }}</span></div>
            <div class="metric-chip"><strong>&#33410;&#22863;</strong><span>{{ scoreText(detail.report?.scores?.score_tempo) }}</span></div>
          </div>

          <div class="metric-row compact-stats">
            <div class="metric-chip"><strong>&#21487;&#20449;&#24230;</strong><span>{{ detailConfidenceText }}</span></div>
            <div class="metric-chip"><strong>&#24320;&#22987;&#26102;&#38388;</strong><span>{{ formatDate(detail.started_at || detail.queued_at) }}</span></div>
            <div class="metric-chip"><strong>&#32467;&#26463;&#26102;&#38388;</strong><span>{{ formatDate(detail.finished_at || detail.updated_at) }}</span></div>
          </div>

          <div class="list-item-card" v-if="detail.report?.recommendations?.overall">
            <strong>&#25972;&#20307;&#24314;&#35758;</strong>
            <span class="helper-text">{{ detail.report.recommendations.overall }}</span>
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

          <div v-if="detail.files" class="detail-links">
            <a v-if="detail.files.report_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.report_url)" target="_blank">&#25171;&#24320;&#25253;&#21578; JSON</a>
            <a v-if="detail.files.teacher_overlay_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.teacher_overlay_url)" target="_blank">&#25945;&#24072;&#39592;&#26550;&#35270;&#39057;</a>
            <a v-if="detail.files.user_overlay_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.user_overlay_url)" target="_blank">&#23398;&#21592;&#39592;&#26550;&#35270;&#39057;</a>
            <a v-if="detail.files.timeline_json_url" class="link-button secondary-button" :href="absMediaUrl(detail.files.timeline_json_url)" target="_blank">&#26102;&#38388;&#36724; JSON</a>
            <button class="secondary-button" type="button" @click="openReportCenter">&#25171;&#24320;&#25253;&#21578;&#20013;&#24515;</button>
            <button class="secondary-button" type="button" :disabled="!canReopenInCompare" @click="reopenInCompare">&#22238;&#21040;&#21160;&#20316;&#20998;&#26512;</button>
          </div>
        </div>
        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#35831;&#36873;&#25321;&#19968;&#26465;&#20219;&#21153;</strong>
          <span class="feedback-state-copy">&#28857;&#20987;&#24038;&#20391;&#20219;&#21153;&#21345;&#29255;&#21518;&#65292;&#36825;&#37324;&#20250;&#23637;&#31034;&#35813;&#20219;&#21153;&#30340;&#32467;&#26524;&#25688;&#35201;&#21644;&#21487;&#19979;&#36733;&#25991;&#20214;&#12290;</span>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { absMediaUrl } from "../api/http";
import { cancelPipeline, getPipelineResultSummary, listPipelineTasks } from "../api/pipelines";
import type { PipelineResultSummaryResponse, PipelineStatusType, PipelineTaskListItem } from "../types/video";

const router = useRouter();
const route = useRoute();

const tasks = ref<PipelineTaskListItem[]>([]);
const loading = ref(false);
const error = ref("");
const detailLoading = ref(false);
const detailError = ref("");
const detail = ref<PipelineResultSummaryResponse | null>(null);
const selectedTaskId = ref("");
const statusFilter = ref<"all" | PipelineStatusType>("all");
const limit = ref(50);
const copying = ref(false);
const cancelingTask = ref(false);

const selectedTask = computed(() => tasks.value.find((item) => item.pipeline_id === selectedTaskId.value) ?? null);
const runningCount = computed(() => tasks.value.filter((item) => item.status === "pending" || item.status === "running").length);
const doneCount = computed(() => tasks.value.filter((item) => item.status === "done").length);
const averageScoreText = computed(() => {
  const scores = tasks.value.map((item) => Number(item.score_total)).filter((value) => Number.isFinite(value));
  if (!scores.length) return "--";
  const total = scores.reduce((sum, value) => sum + value, 0);
  return (total / scores.length).toFixed(1);
});
const detailConfidenceText = computed(() => {
  const score = Number(detail.value?.report?.confidence?.score);
  if (!Number.isFinite(score)) return "--";
  return `${Math.round(score * 100)}%`;
});
const topJointSummary = computed(() => {
  const joints = detail.value?.report?.top_joints;
  if (!Array.isArray(joints) || !joints.length) return "";
  return joints.slice(0, 3).map((item: any) => `${item[0]} (${Number(item[1]).toFixed(3)})`).join("\u3001");
});
const selectedTaskQuery = computed(() => {
  const task = selectedTask.value;
  if (!task) return null;
  return {
    pipeline: task.pipeline_id,
    teacher: task.teacher_video_id || undefined,
    user: task.user_video_id || undefined,
  };
});
const canReopenInCompare = computed(() => Boolean(selectedTask.value?.teacher_video_id && selectedTask.value?.user_video_id));
const canCancelSelectedTask = computed(() => {
  const task = detail.value ?? selectedTask.value;
  if (!task) return false;
  return (task.status === "pending" || task.status === "running") && !task.cancel_requested;
});
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

async function loadTasks(options?: { openFirst?: boolean; keepSelection?: boolean }) {
  loading.value = true;
  error.value = "";
  try {
    const data = await listPipelineTasks({
      limit: limit.value,
      status: statusFilter.value === "all" ? undefined : statusFilter.value,
    });
    tasks.value = data.items;

    if (!tasks.value.length) {
      selectedTaskId.value = "";
      detail.value = null;
      return;
    }

    const hasSelection = selectedTaskId.value && tasks.value.some((item) => item.pipeline_id === selectedTaskId.value);
    if (options?.openFirst || (!hasSelection && !options?.keepSelection)) {
      await openTask(tasks.value[0].pipeline_id);
    } else if (!hasSelection) {
      selectedTaskId.value = tasks.value[0].pipeline_id;
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? "\u4efb\u52a1\u5217\u8868\u52a0\u8f7d\u5931\u8d25";
  } finally {
    loading.value = false;
  }
}

async function refreshTasks() {
  await loadTasks({ keepSelection: true });
}

async function openTask(pipelineId: string) {
  selectedTaskId.value = pipelineId;
  detailLoading.value = true;
  detailError.value = "";
  try {
    detail.value = await getPipelineResultSummary(pipelineId);
  } catch (err: any) {
    detail.value = null;
    detailError.value = err?.response?.data?.detail ?? err?.message ?? "\u4efb\u52a1\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25";
  } finally {
    detailLoading.value = false;
  }
}

async function copyTaskId() {
  if (!selectedTaskId.value) return;
  try {
    await navigator.clipboard.writeText(selectedTaskId.value);
    copying.value = true;
    window.setTimeout(() => {
      copying.value = false;
    }, 1400);
  } catch {
    detailError.value = "\u590d\u5236\u5931\u8d25\uff0c\u8bf7\u624b\u52a8\u590d\u5236\u4efb\u52a1 ID\u3002";
  }
}

async function cancelSelectedTask() {
  if (!selectedTaskId.value || !canCancelSelectedTask.value) return;
  cancelingTask.value = true;
  detailError.value = "";
  try {
    const status = await cancelPipeline(selectedTaskId.value);
    detail.value = detail.value ? { ...detail.value, ...status } : ({ ...status } as PipelineResultSummaryResponse);
    tasks.value = tasks.value.map((item) =>
      item.pipeline_id === selectedTaskId.value ? { ...item, ...status } : item,
    );
  } catch (err: any) {
    detailError.value = err?.response?.data?.detail ?? err?.message ?? "\u53d6\u6d88\u4efb\u52a1\u5931\u8d25";
  } finally {
    cancelingTask.value = false;
  }
}

function openReportCenter() {
  if (!selectedTaskId.value) return;
  void router.push({ path: "/reports", query: { pipeline: selectedTaskId.value } });
}

function reopenInCompare() {
  const query = selectedTaskQuery.value;
  if (!query?.teacher || !query?.user) return;
  void router.push({ path: "/compare", query });
}

function jumpToIssueMoment() {
  const query = selectedTaskQuery.value;
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

function statusText(status?: string) {
  if (status === "pending") return "\u7b49\u5f85\u4e2d";
  if (status === "running") return "\u5206\u6790\u4e2d";
  if (status === "done") return "\u5df2\u5b8c\u6210";
  if (status === "failed") return "\u5931\u8d25";
  if (status === "canceled") return "\u5df2\u53d6\u6d88";
  return status || "\u672a\u77e5";
}

function stageText(stage?: string | null, status?: string) {
  if (stage === "queued") return "\u5df2\u8fdb\u5165\u961f\u5217";
  if (stage === "preparing_inputs") return "\u51c6\u5907\u7d20\u6750";
  if (stage === "extracting_pose") return "\u63d0\u53d6\u9aa8\u67b6";
  if (stage === "aligning_motion") return "\u52a8\u4f5c\u5bf9\u9f50\u4e0e\u8bc4\u5206";
  if (stage === "rendering_outputs") return "\u751f\u6210\u5bf9\u6bd4\u8f93\u51fa";
  if (stage === "packaging_results") return "\u6574\u7406\u7ed3\u679c";
  if (stage === "completed") return "\u7ed3\u679c\u5df2\u5c31\u7eea";
  if (stage === "failed") return "\u4efb\u52a1\u5931\u8d25";
  if (stage === "canceled") return "\u4efb\u52a1\u5df2\u53d6\u6d88";
  return statusText(status);
}

function statusTagClass(status?: string) {
  if (status === "done") return "ok";
  if (status === "failed") return "danger";
  if (status === "canceled") return "neutral";
  if (status === "pending" || status === "running") return "warn";
  return "neutral";
}

function progressPercent(progress?: number | null) {
  const value = Number(progress ?? 0);
  if (!Number.isFinite(value)) return 0;
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

function scoreText(value?: number | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return num.toFixed(1);
}

function confidenceText(value?: number | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return `${Math.round(num * 100)}%`;
}

function formatDate(value?: string | null) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

watch([statusFilter, limit], () => {
  void loadTasks({ openFirst: true });
});

onMounted(async () => {
  await loadTasks({ openFirst: true });
  const pipelineQuery = typeof route.query.pipeline === "string" ? route.query.pipeline : "";
  if (pipelineQuery) {
    await openTask(pipelineQuery);
  }
});
</script>

<style scoped>
.task-summary-grid {
  align-items: start;
}

.task-note {
  margin-top: 14px;
  line-height: 1.7;
}

.task-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
  gap: 16px;
}

.task-list,
.detail-stack {
  display: grid;
  gap: 12px;
}

.task-item {
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

.task-item:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(226, 109, 61, 0.18);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.task-item.active {
  border-color: rgba(226, 109, 61, 0.32);
  background: linear-gradient(180deg, rgba(255, 248, 243, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.task-item-head,
.task-item-meta,
.detail-links {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.task-item-head strong {
  display: block;
  margin-bottom: 4px;
}

.task-item-head p {
  margin: 0;
}

.task-item-grid,
.summary-stack {
  display: grid;
  gap: 10px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.summary-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.mini-progress {
  display: grid;
  gap: 8px;
}

.progress-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.progress-track {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.08);
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--accent) 0%, #ef8a57 100%);
}

.task-item-meta {
  color: var(--muted);
  font-size: 0.84rem;
}

.detail-panel {
  min-height: 100%;
}

.detail-links {
  margin-top: 4px;
}

@media (max-width: 1180px) {
  .task-layout {
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
  .summary-row,
  .task-item-head,
  .task-item-meta,
  .detail-links {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
