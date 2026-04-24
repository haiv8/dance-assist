<template>
  <main class="app-page compare-page compare-workbench">
    <section class="surface-card page-head compare-head">
      <div class="page-head-row">
        <div>
          <h1>动作分析</h1>
          <p class="page-subtitle">把这页收成一个主工作区：左边配置，右边对照舞台，下方结果与复盘。</p>
        </div>
        <button class="secondary-button" :disabled="loading" @click="loadList">
          {{ loading ? "刷新中..." : "同步素材库" }}
        </button>
      </div>

      <div class="compare-kpi-row">
        <div class="compare-kpi-card">
          <span>流程状态</span>
          <strong>{{ pipelineStatusText }}</strong>
        </div>
        <div class="compare-kpi-card">
          <span>问题点</span>
          <strong>{{ markerDots.length }}</strong>
        </div>
        <div class="compare-kpi-card">
          <span>当前总分</span>
          <strong>{{ result ? overallScore.toFixed(1) : "--" }}</strong>
        </div>
        <div class="compare-kpi-card emphasis">
          <span>流程提示</span>
          <strong>{{ analysisFeedbackText }}</strong>
        </div>
      </div>
    </section>

    <section class="surface-card workflow-stepper" aria-label="分析流程">
      <article
        v-for="step in workflowSteps"
        :key="step.key"
        class="workflow-step-item"
        :class="step.state"
      >
        <span class="workflow-step-index">{{ step.index }}</span>
        <div>
          <strong>{{ step.title }}</strong>
          <p>{{ step.copy }}</p>
        </div>
      </article>
    </section>

    <section class="analysis-workbench">
      <aside class="analysis-rail">
        <article class="surface-card analysis-config-card">
          <div class="panel-head compact-head">
            <div>
              <h2>分析配置</h2>
              <p class="helper-text">先确认本轮对照素材，再发起分析任务。</p>
            </div>
          </div>

          <div class="field-grid">
            <div class="field-block">
              <label class="field-label">教师视频</label>
              <select v-model="teacherId">
                <option value="">请选择教师示范视频</option>
                <option v-for="item in teacherItems" :key="item.video_id" :value="item.video_id">
                  {{ item.filename }}
                </option>
              </select>
            </div>

            <div class="field-block">
              <label class="field-label">学员视频</label>
              <select v-model="userId">
                <option value="">请选择学员练习视频</option>
                <option v-for="item in userItems" :key="item.video_id" :value="item.video_id">
                  {{ item.filename }}
                </option>
              </select>
            </div>
          </div>

          <label class="simple-check">
            <input type="checkbox" v-model="overwrite" />
            <span class="check-mark" aria-hidden="true"></span>
            <span>覆盖历史结果</span>
          </label>

          <div class="action-row rail-actions">
            <button :disabled="!teacherId || !userId || analyzing" @click="startAnalysis">
              {{ analyzing ? "分析进行中..." : "发起分析" }}
            </button>
            <button class="ghost-button" :disabled="!canCancelCurrentPipeline || cancelingPipeline" @click="cancelCurrentPipeline">
              {{ cancelingPipeline ? "取消中..." : "取消当前任务" }}
            </button>
          </div>

          <div v-if="error" class="feedback-inline">{{ error }}</div>
        </article>

        <article class="surface-card analysis-session-card">
          <div class="panel-head compact-head">
            <div>
              <h2>当前组合</h2>
              <p class="helper-text">这里保留本轮素材和任务摘要，避免视线来回跳。</p>
            </div>
          </div>

          <div v-if="loading && !items.length" class="feedback-state" data-tone="loading">
            <strong class="feedback-state-title">素材库同步中</strong>
            <span class="feedback-state-copy">正在读取教师与学员素材，完成后会自动补齐默认组合。</span>
          </div>

          <div v-else class="summary-stack compact-summary">
            <div class="summary-row">
              <span>教师素材</span>
              <strong>{{ selectedTeacherLabel }}</strong>
            </div>
            <div class="summary-row">
              <span>学员素材</span>
              <strong>{{ selectedUserLabel }}</strong>
            </div>
            <div class="summary-row">
              <span>任务 ID</span>
              <strong>{{ pipelineId || "尚未创建任务" }}</strong>
            </div>
          </div>

          <div v-if="pipelineId" class="progress-card">
            <div class="progress-head">
              <strong>{{ pipelineStageText }}</strong>
              <span>{{ pipelineProgressPercent }}%</span>
            </div>
            <div class="progress-track"><div class="progress-fill" :style="{ width: `${pipelineProgressPercent}%` }"></div></div>
            <p class="helper-text progress-copy">{{ pipelineMessage || analysisHint }}</p>
          </div>
        </article>
      </aside>

      <section class="surface-card analysis-stage-card">
        <div class="panel-head compact-head">
          <div>
            <h2>对照舞台</h2>
            <p class="helper-text">播放器和时间轴都收在同一块，方便边看边定位问题点。</p>
          </div>
        </div>

        <div class="video-compare-grid">
          <article class="video-panel compact-stage-panel">
            <div class="panel-head compact-head">
              <div>
                <h3>教师示范</h3>
                <p class="helper-text">{{ selectedTeacherLabel }}</p>
              </div>
            </div>
            <div class="player-frame">
              <video
                v-if="displayTeacherUrl"
                ref="teacherRef"
                :src="displayTeacherUrl"
                :muted="teacherMuted"
                controls
                class="player"
                @loadedmetadata="refreshDuration"
                @timeupdate="onTeacherTimeUpdate"
                @play="onTeacherPlay"
                @pause="onTeacherPause"
              ></video>
              <div v-else class="empty-panel">
                <div class="feedback-state" data-tone="empty">
                  <strong class="feedback-state-title">教师示范尚未就绪</strong>
                  <span class="feedback-state-copy">先选择教师示范视频，左侧播放器才会进入对照状态。</span>
                </div>
              </div>
            </div>
          </article>

          <article class="video-panel compact-stage-panel">
            <div class="panel-head compact-head">
              <div>
                <h3>学员练习</h3>
                <p class="helper-text">{{ selectedUserLabel }}</p>
              </div>
            </div>
            <div class="player-frame">
              <video
                v-if="displayUserUrl"
                ref="userRef"
                :src="displayUserUrl"
                :muted="userMuted"
                controls
                class="player"
                @loadedmetadata="refreshDuration"
              ></video>
              <div v-else class="empty-panel">
                <div class="feedback-state" data-tone="empty">
                  <strong class="feedback-state-title">学员练习尚未就绪</strong>
                  <span class="feedback-state-copy">选择学员练习视频后，系统会自动准备双视频对照。</span>
                </div>
              </div>
            </div>
          </article>
        </div>

        <div class="stage-timeline" v-if="displayTeacherUrl && displayUserUrl">
          <div class="stage-timeline-head">
            <strong>同步时间轴</strong>
            <span>{{ currentTime.toFixed(2) }}s / {{ duration.toFixed(2) }}s</span>
          </div>

          <div class="timeline-actions compact-timeline-actions">
            <button class="secondary-button" @click="togglePlay">{{ playing ? "暂停" : "播放" }}</button>
            <button class="secondary-button" @click="stepBy(-1)">-1s</button>
            <button class="secondary-button" @click="stepBy(1)">+1s</button>
            <button class="secondary-button" :disabled="!markerDots.length" @click="jumpPrevMarker">上一处问题</button>
            <button class="secondary-button" :disabled="!markerDots.length" @click="jumpNextMarker">下一处问题</button>
            <button class="ghost-button" @click="toggleTeacherMute">{{ teacherMuted ? "取消教师静音" : "教师静音" }}</button>
            <button class="ghost-button" @click="toggleUserMute">{{ userMuted ? "取消学员静音" : "学员静音" }}</button>
            <button class="ghost-button" @click="toggleAllMute">{{ allMuted ? "取消全部静音" : "全部静音" }}</button>
          </div>

          <div class="timeline-track" @click="onTrackClick">
            <div class="timeline-fill" :style="{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }"></div>
            <button
              v-for="marker in markerDots"
              :key="`track_${marker.frame}_${marker.type}`"
              class="track-marker"
              :class="markerClass(marker.type)"
              :style="{ left: `${marker.leftPct}%` }"
              :title="`${markerLabel(marker.type)} ${marker.sec.toFixed(2)}s${marker.severity ? ` | ${severityText(marker.severity)}` : ''}`"
              @click.stop="seekToMarker(marker.sec, marker.frame)"
            >
              ·
            </button>
          </div>
        </div>
      </section>
    </section>

    <section class="result-card analysis-results" v-if="result || analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running'">
      <div class="panel-head compact-head">
        <div>
          <h2>分析结果</h2>
          <p class="helper-text">{{ result?.pair_name || "本轮分析完成后，结果会显示在这里。" }}</p>
        </div>
        <div class="mode-switch" v-if="result">
          <button class="secondary-button" :disabled="aiCoachLoading || !pipelineId" @click="loadAiCoach">
            {{ aiCoachLoading ? "AI生成中..." : "AI助教解读" }}
          </button>
          <button class="secondary-button" :class="{ activeMode: analysisMode === 'overall' }" @click="analysisMode = 'overall'">概览</button>
          <button class="secondary-button" :class="{ activeMode: analysisMode === 'local' }" :disabled="!hasFrameAnalysis" @click="analysisMode = 'local'">当前时刻</button>
        </div>
      </div>

      <template v-if="!result">
        <div class="feedback-state" :data-tone="analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running' ? 'loading' : 'empty'">
          <strong class="feedback-state-title">{{ analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running' ? '分析任务正在执行' : '暂时还没有分析结果' }}</strong>
          <span class="feedback-state-copy">{{ analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running' ? analysisFeedbackText : '选择教师示范和学员练习后，点击发起分析即可生成结果。' }}</span>
        </div>
      </template>

      <template v-else-if="analysisMode === 'overall'">
        <div class="metric-row compact-stats result-metrics">
          <div class="metric-chip"><strong>总分</strong><span>{{ overallScore.toFixed(2) }}</span></div>
          <div class="metric-chip"><strong>动作</strong><span>{{ poseScore.toFixed(2) }}</span></div>
          <div class="metric-chip"><strong>节奏</strong><span>{{ tempoScore.toFixed(2) }}</span></div>
          <div class="metric-chip"><strong>可信度</strong><span>{{ confidenceScoreText }}</span></div>
        </div>

        <article class="surface-card sub-card simple-card ai-coach-card" v-if="aiCoach || aiCoachError">
          <div class="result-section-head">
            <h3>AI助教</h3>
            <span v-if="aiCoach" class="tag neutral">{{ aiCoachSourceText }}</span>
          </div>
          <p v-if="aiCoachError" class="feedback-inline">{{ aiCoachError }}</p>
          <template v-if="aiCoach">
            <p class="helper-text focus-copy">{{ aiCoach.summary }}</p>
            <div class="ai-coach-grid">
              <div class="list-item-card" v-for="issue in aiCoach.priority_issues.slice(0, 3)" :key="`${issue.title}_${issue.time_hint}`">
                <strong>{{ issue.title }}</strong>
                <span class="helper-text">{{ issue.time_hint ? `${issue.time_hint} · ` : "" }}{{ issue.reason }}</span>
                <span class="helper-text">练法：{{ issue.practice_tip }}</span>
              </div>
            </div>
            <div class="ai-plan-list" v-if="aiCoach.practice_plan.length">
              <div class="summary-row" v-for="step in aiCoach.practice_plan" :key="step.title">
                <span>{{ step.title }} · {{ step.duration_min }}分钟</span>
                <strong>{{ step.success_criteria }}</strong>
              </div>
            </div>
            <p class="helper-text" v-if="aiCoach.setup_hint">{{ aiCoach.setup_hint }}</p>
          </template>
        </article>

        <div class="analysis-result-grid">
          <article class="surface-card sub-card simple-card">
            <div class="result-section-head">
              <h3>整体判断</h3>
              <span class="tag" :class="confidenceTone">{{ confidenceLevelText }}</span>
            </div>
            <p class="helper-text focus-copy">{{ overallAdvice }}</p>

            <div class="summary-stack compact-summary">
              <div class="summary-row">
                <span>高误差关节</span>
                <strong>{{ topJointSummary }}</strong>
              </div>
              <div class="summary-row">
                <span>节奏区间</span>
                <strong>{{ tempoSegmentSummary }}</strong>
              </div>
            </div>

            <div class="list-item-card" v-if="confidenceSummaryText">
              <strong>可信度说明</strong>
              <span class="helper-text">{{ confidenceSummaryText }}</span>
            </div>
          </article>

          <article class="surface-card sub-card simple-card">
            <div class="result-section-head">
              <h3>问题聚焦</h3>
              <button v-if="problemHighlights.length" class="secondary-button" type="button" @click="restoreNormalPlayback">恢复 1.0x</button>
            </div>

            <div v-if="problemHighlights.length" class="focus-marker-list compact-marker-list">
              <button
                v-for="marker in problemHighlights"
                :key="`focus_${marker.frame}_${marker.type}`"
                type="button"
                class="focus-marker-item"
                @click="focusMarker(marker)"
              >
                <strong>{{ markerLabel(marker.type) }} · {{ Number(marker.sec).toFixed(2) }}s</strong>
                <span class="helper-text">{{ markerFocusCopy(marker) }}</span>
              </button>
            </div>

            <ul v-if="confidenceIssues.length" class="list-clean confidence-list">
              <li v-for="issue in confidenceIssues" :key="issue.code || issue.message" class="list-item-card">
                <strong>{{ issue.message }}</strong>
                <span class="helper-text">{{ issue.suggestion }}</span>
              </li>
            </ul>
          </article>
        </div>

        <article class="surface-card sub-card simple-card compact-training-card" v-if="result.report?.beginner_report?.summary || result.report?.teaching_report?.summary">
          <h3>训练建议</h3>
          <p class="helper-text" v-if="result.report?.beginner_report?.summary">学员反馈：{{ result.report.beginner_report.summary }}</p>
          <p class="helper-text" v-if="result.report?.teaching_report?.summary">教学建议：{{ result.report.teaching_report.summary }}</p>
        </article>
      </template>

      <template v-else>
        <div v-if="!currentFrameInfo && frameDetailLoading" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">当前帧详情加载中</strong>
          <span class="feedback-state-copy">系统正在补充这一帧的详细分析，请稍候。</span>
        </div>

        <div v-else-if="currentFrameInfo" class="surface-card sub-card simple-card">
          <div class="metric-row compact-stats local-frame-grid">
            <div class="metric-chip"><strong>帧号</strong><span>{{ currentFrameInfo.frame }}</span></div>
            <div class="metric-chip"><strong>时间</strong><span>{{ Number(currentFrameInfo.sec).toFixed(2) }}s</span></div>
            <div class="metric-chip"><strong>误差</strong><span>{{ Number(currentFrameInfo.frame_error ?? 0).toFixed(4) }}</span></div>
            <div class="metric-chip"><strong>节奏偏差</strong><span>{{ timingOffsetText(currentFrameInfo.timing_offset_sec) }}</span></div>
            <div class="metric-chip"><strong>匹配帧</strong><span>{{ currentFrameInfo.matched_user_frame ?? "--" }}</span></div>
            <div class="metric-chip"><strong>匹配时间</strong><span>{{ formatSecondsMaybe(currentFrameInfo.matched_user_sec) }}</span></div>
          </div>
          <p class="helper-text focus-copy frame-advice">{{ currentFrameInfo.advice }}</p>
        </div>

        <div v-else class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">暂停后查看局部细节</strong>
          <span class="feedback-state-copy">先把视频停在要复盘的位置，再切换到当前时刻。</span>
        </div>
      </template>

      <div class="download-grid simple-downloads" v-if="result?.files">
        <a v-if="result.files.teacher_overlay_url" :href="absMediaUrl(result.files.teacher_overlay_url)" target="_blank">教师骨架视频</a>
        <a v-if="result.files.user_overlay_url" :href="absMediaUrl(result.files.user_overlay_url)" target="_blank">学员骨架视频</a>
        <a v-if="result.files.report_url" :href="absMediaUrl(result.files.report_url)" target="_blank">分析报告 JSON</a>
        <a v-if="result.files.timeline_json_url" :href="absMediaUrl(result.files.timeline_json_url)" target="_blank">时间轴 JSON</a>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { getAiCoachReport } from "../api/ai";
import { absMediaUrl } from "../api/http";
import {
  cancelPipeline,
  getPipelineFrameDetail,
  getPipelineFrameRange,
  getPipelineResult,
  getPipelineResultSummary,
  getPipelineStatus,
  runPipeline,
} from "../api/pipelines";
import { normalizedConfidenceIssues, normalizedConfidenceSummary } from "../utils/confidence";
import { friendlyError } from "../utils/errors";
import { listVideos } from "../api/videos";
import type {
  AiCoachResponse,
  PipelineFrameRangeResponse,
  PipelineResultResponse,
  PipelineRunResponse,
  PipelineStatusResponse,
  PipelineStatusType,
  VideoItem,
} from "../types/video";

type WorkflowStepState = "done" | "active" | "locked";

const route = useRoute();

const loading = ref(false);
const error = ref("");
const items = ref<VideoItem[]>([]);
const teacherId = ref("");
const userId = ref("");
const overwrite = ref(false);
const analyzing = ref(false);
const pipelineId = ref("");
const pipelineStatus = ref<PipelineStatusType | "">("");
const pipelineStage = ref("");
const pipelineProgress = ref(0);
const pipelineMessage = ref("");
const cancelRequested = ref(false);
const cancelingPipeline = ref(false);
const result = ref<PipelineResultResponse | null>(null);
const aiCoach = ref<AiCoachResponse | null>(null);
const aiCoachLoading = ref(false);
const aiCoachError = ref("");
const analysisMode = ref<"overall" | "local">("overall");
const frameDetailCache = ref<Record<number, Record<string, any>>>({});
const frameDetailLoading = ref(false);
const FRAME_WINDOW_RADIUS = 12;
const REVIEW_PLAYBACK_RATE = 0.5;
let pollTimer: number | null = null;

const teacherItems = computed(() => items.value.filter((item) => item.role === "teacher"));
const userItems = computed(() => items.value.filter((item) => item.role === "user"));
const selectedTeacher = computed(() => teacherItems.value.find((item) => item.video_id === teacherId.value));
const selectedUser = computed(() => userItems.value.find((item) => item.video_id === userId.value));
const selectedTeacherLabel = computed(() => selectedTeacher.value?.filename ?? "尚未选择教师视频");
const selectedUserLabel = computed(() => selectedUser.value?.filename ?? "尚未选择学员视频");
const teacherUrl = computed(() => (selectedTeacher.value ? absMediaUrl(selectedTeacher.value.url) : ""));
const userUrl = computed(() => (selectedUser.value ? absMediaUrl(selectedUser.value.url) : ""));
const pipelineStatusText = computed(() => pipelineStatusToText(pipelineStatus.value));
const pipelineStageText = computed(() => stageToText(pipelineStage.value, pipelineStatus.value));
const pipelineProgressPercent = computed(() => Math.round(Math.max(0, Math.min(1, pipelineProgress.value || 0)) * 100));
const canCancelCurrentPipeline = computed(() => {
  if (!pipelineId.value) return false;
  return (pipelineStatus.value === "pending" || pipelineStatus.value === "running") && !cancelRequested.value;
});
const analysisHint = computed(() => {
  if (!teacherId.value || !userId.value) return "先选择教师和学员素材";
  if (analyzing.value || pipelineStatus.value === "pending" || pipelineStatus.value === "running") return "分析进行中，结果会自动刷新";
  if (!result.value) return "当前组合已就绪，可以开始分析";
  return "结果已生成，可以回放并定位问题点";
});
const analysisFeedbackText = computed(() => {
  if (error.value) return error.value;
  if (analyzing.value || pipelineStatus.value === "pending" || pipelineStatus.value === "running") {
    const stage = pipelineStageText.value;
    const message = pipelineMessage.value?.trim();
    if (message) return `${stage} - ${message}`;
    return `${stage} - ${pipelineProgressPercent.value}%`;
  }
  return analysisHint.value;
});
const hasSelectedPair = computed(() => Boolean(teacherId.value && userId.value));
const hasActivePipeline = computed(() => analyzing.value || pipelineStatus.value === "pending" || pipelineStatus.value === "running");
const workflowSteps = computed<Array<{ key: string; index: string; title: string; copy: string; state: WorkflowStepState }>>(() => {
  const selectDone = hasSelectedPair.value;
  const runDone = Boolean(result.value);
  const runActive = selectDone && !runDone;
  const reviewActive = Boolean(result.value);

  return [
    {
      key: "select",
      index: "01",
      title: "选择素材",
      copy: selectDone ? "教师与学员素材已就绪" : "先选择一组教师示范和学员练习",
      state: selectDone ? "done" : "active",
    },
    {
      key: "run",
      index: "02",
      title: "确认并分析",
      copy: hasActivePipeline.value ? analysisFeedbackText.value : pipelineId.value ? "任务已创建，可继续查看进度" : "确认组合后发起动作分析",
      state: runDone ? "done" : runActive ? "active" : "locked",
    },
    {
      key: "review",
      index: "03",
      title: "复盘结果",
      copy: result.value ? "查看分数、可信度、问题片段和 AI 建议" : "分析完成后自动开放结果复盘",
      state: reviewActive ? "active" : "locked",
    },
  ];
});

const displayTeacherUrl = computed(() => {
  const url = result.value?.files?.teacher_overlay_url;
  if (!url) return teacherUrl.value;
  const version = pipelineId.value || "";
  const separator = url.includes("?") ? "&" : "?";
  return absMediaUrl(`${url}${version ? `${separator}v=${encodeURIComponent(version)}` : ""}`);
});
const displayUserUrl = computed(() => {
  const url = result.value?.files?.user_overlay_url;
  if (!url) return userUrl.value;
  const version = pipelineId.value || "";
  const separator = url.includes("?") ? "&" : "?";
  return absMediaUrl(`${url}${version ? `${separator}v=${encodeURIComponent(version)}` : ""}`);
});

const markers = computed(() => {
  const list = result.value?.report?.markers;
  if (!Array.isArray(list)) return [];
  return list as Array<{ frame: number; sec: number; type: string; severity?: string }>;
});
const markerDots = computed(() =>
  markers.value.map((item) => ({
    ...item,
    leftPct: duration.value > 1e-6 ? Math.max(0, Math.min(100, (item.sec / duration.value) * 100)) : 0,
  })),
);
const problemHighlights = computed(() => {
  const severityRank: Record<string, number> = { severe: 3, clear: 2, mild: 1 };
  return [...markerDots.value]
    .sort((a, b) => {
      const severityDelta = (severityRank[String(b.severity ?? "")] ?? 0) - (severityRank[String(a.severity ?? "")] ?? 0);
      if (severityDelta !== 0) return severityDelta;
      return Number(a.sec) - Number(b.sec);
    })
    .slice(0, 6);
});

const mapUserSecArr = computed<number[]>(() =>
  Array.isArray(result.value?.timeline?.map_user_sec) ? result.value.timeline.map_user_sec.map((value: any) => Number(value)) : [],
);
const teacherToUserArr = computed<number[]>(() =>
  Array.isArray(result.value?.timeline?.teacher_to_user) ? result.value.timeline.teacher_to_user.map((value: any) => Number(value)) : [],
);
const fpsTeacher = computed<number>(() => {
  const value = Number(result.value?.timeline?.fps_teacher ?? result.value?.report?.fps_teacher ?? 30);
  return Number.isFinite(value) && value > 0 ? value : 30;
});
const fpsUser = computed<number>(() => {
  const value = Number(result.value?.timeline?.fps_user ?? result.value?.report?.fps_user ?? 30);
  return Number.isFinite(value) && value > 0 ? value : 30;
});

const frameAnalysisCount = computed<number>(() => {
  const count = Number(result.value?.report?.frame_analysis_count);
  if (Number.isFinite(count) && count > 0) return Math.floor(count);
  return Array.isArray(result.value?.report?.frame_analysis) ? result.value.report.frame_analysis.length : 0;
});
const currentFrameIndex = computed<number | null>(() => {
  if (frameAnalysisCount.value <= 0) return null;
  const index = Math.round(currentTime.value * fpsTeacher.value);
  return Math.max(0, Math.min(frameAnalysisCount.value - 1, index));
});
const hasFrameAnalysis = computed(() => frameAnalysisCount.value > 0);
const currentFrameInfo = computed(() => {
  const index = currentFrameIndex.value;
  if (index === null) return null;
  if (Array.isArray(result.value?.report?.frame_analysis) && result.value.report.frame_analysis.length > 0) {
    return result.value.report.frame_analysis[index] ?? null;
  }
  return frameDetailCache.value[index] ?? null;
});

const overallScore = computed(() => Number(result.value?.report?.score_0_100 ?? result.value?.report?.scores?.score_total ?? 0));
const poseScore = computed(() => Number(result.value?.report?.scores?.score_pose ?? 0));
const tempoScore = computed(() => Number(result.value?.report?.scores?.score_tempo ?? 0));
const overallAdvice = computed(() => result.value?.report?.recommendations?.overall ?? "保持身体主干稳定，优先修正误差最大的关节动作。");
const topJointSummary = computed(() => {
  const joints = result.value?.report?.top_joints;
  if (!Array.isArray(joints) || joints.length === 0) return "分析完成后会在这里显示本轮最需要优先处理的关节。";
  return joints.slice(0, 3).map((item: any) => `${item[0]} (${Number(item[1]).toFixed(3)})`).join("、");
});
const tempoSegmentSummary = computed(() => {
  const list = result.value?.report?.tempo_segments;
  if (!Array.isArray(list) || list.length === 0) return "暂无明显节奏异常区间。";
  return `共 ${list.length} 段需要重点复盘的节奏异常片段。`;
});
const confidenceData = computed<Record<string, any> | null>(() => {
  const confidence = result.value?.report?.confidence;
  return confidence && typeof confidence === "object" ? confidence : null;
});
const confidenceLevelText = computed(() => {
  const level = String(confidenceData.value?.level ?? "");
  if (level === "high") return "高";
  if (level === "medium") return "中";
  if (level === "low") return "低";
  return "--";
});
const confidenceScoreText = computed(() => {
  const score = Number(confidenceData.value?.score);
  if (!Number.isFinite(score)) return "--";
  return `${Math.round(score * 100)}%`;
});
const confidenceSummaryText = computed(() => normalizedConfidenceSummary(confidenceData.value));
const confidenceIssues = computed<any[]>(() => normalizedConfidenceIssues(confidenceData.value));
const aiCoachSourceText = computed(() => {
  if (!aiCoach.value) return "";
  if (aiCoach.value.generated_by === "aliyun") return aiCoach.value.model || "阿里云百炼";
  if (aiCoach.value.generated_by === "openai") return aiCoach.value.model || "OpenAI";
  return "本地兜底";
});
const confidenceTone = computed(() => {
  const level = String(confidenceData.value?.level ?? "");
  if (level === "high") return "ok";
  if (level === "medium") return "warn";
  if (level === "low") return "danger";
  return "neutral";
});

const teacherRef = ref<HTMLVideoElement | null>(null);
const userRef = ref<HTMLVideoElement | null>(null);
const playing = ref(false);
const duration = ref(0);
const currentTime = ref(0);
const pendingSeekSec = ref<number | null>(null);
const routeSeekSec = ref<number | null>(null);
const teacherMuted = ref(false);
const userMuted = ref(false);
const allMuted = computed(() => teacherMuted.value && userMuted.value);
let syncTimer: number | null = null;
let lastSeekAtMs = 0;
let filteredDiff = 0;

const SYNC_SEEK_THRESHOLD_SEC = 0.45;
const SYNC_SEEK_COOLDOWN_MS = 650;
const SYNC_RATE_DEADZONE_SEC = 0.06;
const SYNC_RATE_MIN = 0.97;
const SYNC_RATE_MAX = 1.03;
const SYNC_RATE_GAIN = 0.12;

function getSeekableEnd(video: HTMLVideoElement | null): number {
  if (!video) return 0;
  try {
    if (video.seekable?.length) return Number(video.seekable.end(video.seekable.length - 1)) || 0;
  } catch {
    return 0;
  }
  return 0;
}

function getSeekableStart(video: HTMLVideoElement | null): number {
  if (!video) return 0;
  try {
    if (video.seekable?.length) return Number(video.seekable.start(0)) || 0;
  } catch {
    return 0;
  }
  return 0;
}

function formatSecondsMaybe(value: unknown) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return `${num.toFixed(2)}s`;
}

function timingOffsetText(value: unknown) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  const abs = Math.abs(num);
  if (abs < 0.02) return "已对齐";
  return num > 0 ? `慢 ${abs.toFixed(2)}s` : `快 ${abs.toFixed(2)}s`;
}

function markerLabel(type: string) {
  if (type === "pose_error") return "动作误差";
  if (type === "tempo") return "节奏异常";
  if (type === "tracking_bad") return "跟踪问题";
  return "标记";
}

function markerClass(type: string) {
  if (type === "pose_error") return "m-pose";
  if (type === "tempo") return "m-tempo";
  if (type === "tracking_bad") return "m-track";
  return "";
}

function pipelineStatusToText(status?: string) {
  if (status === "pending") return "等待中";
  if (status === "running") return "分析中";
  if (status === "done") return "已完成";
  if (status === "failed") return "失败";
  if (status === "canceled") return "已取消";
  return status || "未开始";
}

function stageToText(stage?: string, status?: string) {
  if (stage === "queued") return "已进入队列";
  if (stage === "preparing_inputs") return "准备素材";
  if (stage === "extracting_pose") return "提取骨架";
  if (stage === "aligning_motion") return "动作对齐与评分";
  if (stage === "rendering_outputs") return "生成对比输出";
  if (stage === "packaging_results") return "整理结果";
  if (stage === "completed") return "结果已就绪";
  if (stage === "failed") return "任务失败";
  if (stage === "canceled") return "任务已取消";
  return pipelineStatusToText(status);
}

function severityText(severity?: string) {
  if (severity === "mild") return "轻微";
  if (severity === "clear") return "明显";
  if (severity === "severe") return "严重";
  return severity || "-";
}

function markerFocusCopy(marker: { sec: number; frame: number; type: string; severity?: string }) {
  return `${markerLabel(marker.type)} | ${severityText(marker.severity)} | 跳转到 ${Number(marker.sec).toFixed(2)}s 并以 0.5x 回放`;
}

function applyPlaybackRates(rate: number) {
  if (teacherRef.value) teacherRef.value.playbackRate = rate;
  if (userRef.value) userRef.value.playbackRate = rate;
}

function restoreNormalPlayback() {
  applyPlaybackRates(1);
}

function stopSyncTimer() {
  if (syncTimer !== null) {
    window.clearInterval(syncTimer);
    syncTimer = null;
  }
}

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

function applyPipelineMeta(meta?: Partial<PipelineRunResponse & PipelineStatusResponse & PipelineResultResponse> | null) {
  if (!meta) return;
  if (meta.status) pipelineStatus.value = meta.status;
  pipelineStage.value = meta.stage ?? pipelineStage.value;
  if (typeof meta.progress === "number" && Number.isFinite(meta.progress)) {
    pipelineProgress.value = Math.max(0, Math.min(1, meta.progress));
  }
  if (typeof meta.message === "string") {
    pipelineMessage.value = meta.message;
  }
  if (typeof meta.cancel_requested === "boolean") {
    cancelRequested.value = meta.cancel_requested;
  }
}

function mapUserSec(teacherSec: number): number {
  if (teacherToUserArr.value.length) {
    const teacherIndex = Math.max(0, Math.min(teacherToUserArr.value.length - 1, Math.round(teacherSec * fpsTeacher.value)));
    const userFrame = Number(teacherToUserArr.value[teacherIndex]);
    if (Number.isFinite(userFrame)) return Math.max(0, userFrame / Math.max(1e-6, fpsUser.value));
  }
  if (!mapUserSecArr.value.length) return teacherSec;
  const index = Math.max(0, Math.min(mapUserSecArr.value.length - 1, teacherSec * fpsTeacher.value));
  const lower = Math.floor(index);
  const upper = Math.min(mapUserSecArr.value.length - 1, lower + 1);
  const fraction = index - lower;
  const start = Number(mapUserSecArr.value[lower]);
  const end = Number(mapUserSecArr.value[upper]);
  if (!Number.isFinite(start) || !Number.isFinite(end)) return teacherSec;
  return start * (1 - fraction) + end * fraction;
}

function syncLoop() {
  const teacher = teacherRef.value;
  const user = userRef.value;
  if (!teacher || !user) return;
  const baseRate = teacher.playbackRate > 0 ? teacher.playbackRate : 1;
  const targetUserSec = mapUserSec(teacher.currentTime);
  const diff = targetUserSec - user.currentTime;
  filteredDiff = 0.7 * filteredDiff + 0.3 * diff;
  const now = Date.now();
  const absDiff = Math.abs(filteredDiff);

  if (absDiff > SYNC_SEEK_THRESHOLD_SEC && now - lastSeekAtMs >= SYNC_SEEK_COOLDOWN_MS) {
    user.currentTime = targetUserSec;
    user.playbackRate = baseRate;
    lastSeekAtMs = now;
  } else if (absDiff <= SYNC_RATE_DEADZONE_SEC) {
    user.playbackRate = baseRate;
  } else {
    const nextRate = baseRate * (1 + SYNC_RATE_GAIN * filteredDiff);
    user.playbackRate = Math.max(baseRate * SYNC_RATE_MIN, Math.min(baseRate * SYNC_RATE_MAX, nextRate));
  }

  currentTime.value = teacher.currentTime;
}

function refreshDuration() {
  const teacher = teacherRef.value;
  const user = userRef.value;
  if (!teacher) return;
  const teacherDuration = Number.isFinite(teacher.duration) ? teacher.duration : 0;
  const userDuration = user && Number.isFinite(user.duration) ? user.duration : 0;
  const teacherEnd = teacherDuration > 0 ? teacherDuration : getSeekableEnd(teacher);
  const userEnd = user ? (userDuration > 0 ? userDuration : getSeekableEnd(user)) : 0;
  duration.value = Math.max(0, Math.min(teacherEnd || 0, userEnd || teacherEnd || 0));
  if (pendingSeekSec.value !== null && duration.value > 0) {
    const nextSec = pendingSeekSec.value;
    pendingSeekSec.value = null;
    seekBoth(nextSec);
  }
}

function onTeacherTimeUpdate() {
  if (teacherRef.value) currentTime.value = teacherRef.value.currentTime;
}

async function onTeacherPlay() {
  playing.value = true;
  analysisMode.value = "overall";
  if (userRef.value) {
    userRef.value.currentTime = mapUserSec(teacherRef.value?.currentTime ?? 0);
    userRef.value.playbackRate = teacherRef.value?.playbackRate || 1;
    try {
      await userRef.value.play();
    } catch {
      // ignore
    }
  }
  filteredDiff = 0;
  stopSyncTimer();
  syncTimer = window.setInterval(syncLoop, 100);
}

function onTeacherPause() {
  playing.value = false;
  analysisMode.value = "local";
  if (userRef.value) {
    userRef.value.pause();
    userRef.value.playbackRate = 1;
  }
  stopSyncTimer();
}

async function togglePlay() {
  if (!teacherRef.value) return;
  if (teacherRef.value.paused) {
    try {
      await teacherRef.value.play();
    } catch {
      // ignore
    }
  } else {
    teacherRef.value.pause();
  }
}

function seekBoth(target: number) {
  const teacher = teacherRef.value;
  if (!teacher) {
    pendingSeekSec.value = Math.max(0, Number(target) || 0);
    return;
  }
  const teacherDuration = Number.isFinite(teacher.duration) && teacher.duration > 0 ? teacher.duration : (getSeekableEnd(teacher) || duration.value);
  if (!(teacherDuration > 0)) {
    pendingSeekSec.value = Math.max(0, Number(target) || 0);
    return;
  }
  const start = getSeekableStart(teacher);
  const end = getSeekableEnd(teacher) || teacherDuration;
  const teacherSec = Math.max(start, Math.min(end, Number(target)));
  teacher.currentTime = teacherSec;
  if (userRef.value) {
    userRef.value.currentTime = mapUserSec(teacherSec);
    userRef.value.playbackRate = teacher.playbackRate || 1;
    if (!teacher.paused) void userRef.value.play().catch(() => {});
  }
  lastSeekAtMs = Date.now();
  currentTime.value = teacherSec;
  analysisMode.value = "local";
}

function applyMuteState() {
  if (teacherRef.value) teacherRef.value.muted = teacherMuted.value;
  if (userRef.value) userRef.value.muted = userMuted.value;
}

function toggleTeacherMute() {
  teacherMuted.value = !teacherMuted.value;
  applyMuteState();
}

function toggleUserMute() {
  userMuted.value = !userMuted.value;
  applyMuteState();
}

function toggleAllMute() {
  const nextValue = !allMuted.value;
  teacherMuted.value = nextValue;
  userMuted.value = nextValue;
  applyMuteState();
}

function onTrackClick(event: MouseEvent) {
  const durationValue = duration.value > 0 ? duration.value : (teacherRef.value ? Number(teacherRef.value.duration || getSeekableEnd(teacherRef.value)) : 0);
  if (!(durationValue > 0)) return;
  const element = event.currentTarget as HTMLElement | null;
  if (!element) return;
  const rect = element.getBoundingClientRect();
  const ratio = Math.max(0, Math.min(1, rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0));
  seekBoth(ratio * durationValue);
}

function seekToMarker(sec: number, frame?: number) {
  if (Number.isFinite(Number(frame))) {
    seekBoth(Number(frame) / Math.max(1e-6, fpsTeacher.value));
    return;
  }
  seekBoth(sec);
}

async function focusMarker(marker: { sec: number; frame: number; type: string; severity?: string }) {
  const targetFrame = Number.isFinite(Number(marker.frame)) ? Number(marker.frame) : Math.round(Number(marker.sec) * fpsTeacher.value);
  seekToMarker(marker.sec, marker.frame);
  analysisMode.value = "local";
  await ensureFrameWindow(targetFrame, FRAME_WINDOW_RADIUS);
  applyPlaybackRates(REVIEW_PLAYBACK_RATE);
  if (teacherRef.value?.paused) {
    try {
      await teacherRef.value.play();
    } catch {
      // ignore
    }
  }
}

function jumpPrevMarker() {
  const list = markerDots.value.map((item) => Number(item.sec)).filter((sec) => Number.isFinite(sec)).sort((a, b) => a - b);
  if (!list.length) return;
  let target = list[0];
  for (const sec of list) {
    if (sec < currentTime.value - 0.05) target = sec;
    else break;
  }
  seekToMarker(target);
}

function jumpNextMarker() {
  const list = markerDots.value.map((item) => Number(item.sec)).filter((sec) => Number.isFinite(sec)).sort((a, b) => a - b);
  if (!list.length) return;
  let target = list[list.length - 1];
  for (const sec of list) {
    if (sec > currentTime.value + 0.05) {
      target = sec;
      break;
    }
  }
  seekToMarker(target);
}

function stepBy(delta: number) {
  seekBoth(currentTime.value + delta);
}

function routeQueryValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

async function hydrateFromRoute() {
  const teacherQuery = routeQueryValue(route.query.teacher);
  const userQuery = routeQueryValue(route.query.user);
  const pipelineQuery = routeQueryValue(route.query.pipeline);
  const secQuery = Number(routeQueryValue(route.query.sec));
  const modeQuery = routeQueryValue(route.query.mode);

  if (teacherQuery && teacherItems.value.some((item) => item.video_id === teacherQuery)) {
    teacherId.value = teacherQuery;
  }
  if (userQuery && userItems.value.some((item) => item.video_id === userQuery)) {
    userId.value = userQuery;
  }
  routeSeekSec.value = Number.isFinite(secQuery) ? Math.max(0, secQuery) : null;

  if (!pipelineQuery) {
    if (modeQuery === "local") analysisMode.value = "local";
    return;
  }

  pipelineId.value = pipelineQuery;
  try {
    result.value = await getPipelineResultSummary(pipelineQuery);
  } catch {
    try {
      result.value = await getPipelineResult(pipelineQuery);
    } catch {
      return;
    }
  }
  applyPipelineMeta(result.value);
  analysisMode.value = modeQuery === "local" ? "local" : "overall";
  if (routeSeekSec.value !== null) {
    pendingSeekSec.value = routeSeekSec.value;
  }
}

async function loadList() {
  loading.value = true;
  error.value = "";
  try {
    const data = await listVideos("all");
    items.value = data.items;
    await hydrateFromRoute();
    if (!teacherId.value && teacherItems.value.length > 0) teacherId.value = teacherItems.value[0].video_id;
    if (!userId.value && userItems.value.length > 0) userId.value = userItems.value[0].video_id;
  } catch (e: any) {
    error.value = friendlyError(e, "视频列表加载失败");
  } finally {
    loading.value = false;
  }
}

async function pollStatus(id: string) {
  try {
    const status = await getPipelineStatus(id);
    applyPipelineMeta(status);
    if (status.status === "done" || status.status === "failed" || status.status === "canceled") {
      stopPolling();
      analyzing.value = false;
      try {
        result.value = await getPipelineResultSummary(id);
      } catch {
        result.value = await getPipelineResult(id);
      }
      applyPipelineMeta(result.value);
      analysisMode.value = "overall";
      aiCoach.value = null;
      aiCoachError.value = "";
    }
  } catch (e: any) {
    stopPolling();
    analyzing.value = false;
    error.value = friendlyError(e, "流程状态查询失败");
  }
}

async function startAnalysis() {
  if (!teacherId.value || !userId.value) return;
  analyzing.value = true;
  result.value = null;
  aiCoach.value = null;
  aiCoachError.value = "";
  frameDetailCache.value = {};
  frameDetailLoading.value = false;
  pipelineMessage.value = "";
  pipelineStage.value = "queued";
  pipelineProgress.value = 0;
  cancelRequested.value = false;
  error.value = "";
  try {
    const response = await runPipeline({
      teacher_video_id: teacherId.value,
      user_video_id: userId.value,
      overwrite: overwrite.value,
    });
    pipelineId.value = response.pipeline_id;
    applyPipelineMeta(response);
    stopPolling();
    pollTimer = window.setInterval(() => {
      void pollStatus(response.pipeline_id);
    }, 2000);
    await pollStatus(response.pipeline_id);
  } catch (e: any) {
    analyzing.value = false;
    error.value = friendlyError(e, "流程启动失败");
  }
}

async function loadAiCoach() {
  if (!pipelineId.value) return;
  aiCoachLoading.value = true;
  aiCoachError.value = "";
  try {
    aiCoach.value = await getAiCoachReport(pipelineId.value);
  } catch (e: any) {
    aiCoachError.value = friendlyError(e, "AI助教生成失败");
  } finally {
    aiCoachLoading.value = false;
  }
}

async function cancelCurrentPipeline() {
  if (!pipelineId.value || !canCancelCurrentPipeline.value) return;
  cancelingPipeline.value = true;
  error.value = "";
  try {
    const status = await cancelPipeline(pipelineId.value);
    applyPipelineMeta(status);
    if (status.status === "canceled") {
      analyzing.value = false;
      stopPolling();
    }
  } catch (e: any) {
    error.value = friendlyError(e, "取消任务失败");
  } finally {
    cancelingPipeline.value = false;
  }
}

async function ensureFrameWindow(frame: number | null, radius = FRAME_WINDOW_RADIUS) {
  if (frame === null || !pipelineId.value || frameAnalysisCount.value <= 0) return;
  if (Array.isArray(result.value?.report?.frame_analysis)) return;

  const start = Math.max(0, frame - radius);
  const end = Math.min(frameAnalysisCount.value - 1, frame + radius);
  let needsLoad = false;
  for (let index = start; index <= end; index += 1) {
    if (!frameDetailCache.value[index]) {
      needsLoad = true;
      break;
    }
  }
  if (!needsLoad) return;

  frameDetailLoading.value = true;
  try {
    const range: PipelineFrameRangeResponse = await getPipelineFrameRange(pipelineId.value, {
      start_frame: start,
      end_frame: end,
    });
    const nextCache = { ...frameDetailCache.value };
    for (const item of range.items) {
      if (item.frame_analysis) nextCache[item.frame] = item.frame_analysis;
    }
    frameDetailCache.value = nextCache;
  } finally {
    frameDetailLoading.value = false;
  }
}

async function ensureFrameDetail(frame: number | null) {
  if (frame === null) return;
  if (frameDetailCache.value[frame]) return;
  await ensureFrameWindow(frame, 2);
  if (frameDetailCache.value[frame] || !pipelineId.value || Array.isArray(result.value?.report?.frame_analysis)) return;
  frameDetailLoading.value = true;
  try {
    const detail = await getPipelineFrameDetail(pipelineId.value, frame);
    if (detail.frame_analysis) {
      frameDetailCache.value = { ...frameDetailCache.value, [frame]: detail.frame_analysis };
    }
  } finally {
    frameDetailLoading.value = false;
  }
}

onMounted(() => {
  void loadList();
});

watch([displayTeacherUrl, displayUserUrl], () => {
  playing.value = false;
  currentTime.value = 0;
  duration.value = 0;
  pendingSeekSec.value = null;
  filteredDiff = 0;
  restoreNormalPlayback();
  stopSyncTimer();
});

watch([teacherMuted, userMuted], applyMuteState);

watch([teacherId, userId], () => {
  result.value = null;
  aiCoach.value = null;
  aiCoachError.value = "";
  analysisMode.value = "overall";
  frameDetailCache.value = {};
  frameDetailLoading.value = false;
  pipelineId.value = "";
  pipelineStatus.value = "";
  pipelineStage.value = "";
  pipelineProgress.value = 0;
  pipelineMessage.value = "";
  cancelRequested.value = false;
  routeSeekSec.value = null;
});

watch([analysisMode, currentFrameIndex, result], ([mode, frame]) => {
  if (mode !== "local") return;
  void ensureFrameWindow(frame);
  void ensureFrameDetail(frame);
});

watch(
  () => [route.query.teacher, route.query.user, route.query.pipeline, route.query.sec, route.query.mode],
  () => {
    if (!items.value.length) return;
    void hydrateFromRoute();
  },
);

watch([duration, result], ([nextDuration, nextResult]) => {
  if (!nextResult || !(nextDuration > 0) || routeSeekSec.value === null) return;
  seekBoth(routeSeekSec.value);
  analysisMode.value = "local";
  routeSeekSec.value = null;
});

onBeforeUnmount(() => {
  stopSyncTimer();
  stopPolling();
});
</script>

<style scoped>
.compare-workbench,
.workflow-stepper,
.analysis-workbench,
.analysis-rail,
.analysis-stage-card,
.analysis-results,
.analysis-result-grid,
.compact-summary,
.compact-marker-list {
  display: grid;
  gap: 16px;
}

.compare-head {
  gap: 18px;
}

.compare-workbench {
  gap: 14px;
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas:
    "head"
    "workflow"
    "workbench"
    "result";
  align-items: stretch;
}

.compare-workbench > .compare-head {
  grid-area: head;
}

.compare-workbench > .workflow-stepper {
  grid-area: workflow;
}

.compare-workbench > .analysis-workbench {
  grid-area: workbench;
}

.compare-workbench > .analysis-results {
  grid-area: result;
}

.compare-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.compare-kpi-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(255, 255, 255, 0.92);
}

.compare-kpi-card span {
  color: var(--muted);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.compare-kpi-card strong {
  font-family: var(--font-display);
  font-size: 1.2rem;
  line-height: 1.2;
}

.compare-kpi-card.emphasis {
  background: linear-gradient(180deg, rgba(255, 247, 241, 0.98) 0%, rgba(255, 243, 235, 0.94) 100%);
  border-color: rgba(226, 109, 61, 0.18);
}

.workflow-stepper {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 12px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96) 0%, rgba(244, 251, 255, 0.92) 100%),
    radial-gradient(circle at 10% 20%, rgba(56, 189, 248, 0.1), transparent 32%);
}

.workflow-step-item {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  min-height: 86px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.72);
  color: var(--muted);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.workflow-step-item strong {
  display: block;
  margin-bottom: 6px;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1rem;
}

.workflow-step-item p {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.6;
}

.workflow-step-index {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.92);
  color: var(--muted);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
}

.workflow-step-item.active {
  transform: translateY(-1px);
  border-color: rgba(15, 143, 179, 0.34);
  background: linear-gradient(145deg, rgba(236, 253, 255, 0.94), rgba(255, 255, 255, 0.98));
  box-shadow: 0 16px 36px rgba(15, 143, 179, 0.12);
}

.workflow-step-item.active .workflow-step-index {
  border-color: transparent;
  background: linear-gradient(135deg, var(--accent) 0%, #38bdf8 100%);
  color: #fff;
}

.workflow-step-item.done .workflow-step-index {
  border-color: rgba(22, 163, 74, 0.18);
  background: rgba(220, 252, 231, 0.9);
  color: #15803d;
}

.workflow-step-item.locked {
  opacity: 0.62;
}

.analysis-workbench {
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}

.analysis-rail {
  grid-template-columns: minmax(260px, 0.72fr) minmax(320px, 1fr);
  align-items: stretch;
}

.analysis-config-card,
.analysis-session-card,
.analysis-stage-card {
  overflow: visible;
}

.analysis-config-card .panel-head h2::after,
.analysis-session-card .panel-head h2::after,
.analysis-stage-card .panel-head h2::after {
  content: none !important;
}

.analysis-workbench .panel-head.compact-head > div::after {
  content: none !important;
  display: none !important;
}

.analysis-workbench .panel-head.compact-head > div {
  display: block !important;
  width: auto !important;
}

.analysis-workbench .panel-head.compact-head > div:hover > .helper-text {
  display: none !important;
}

.rail-actions {
  margin-top: 4px;
}

.analysis-config-card .simple-check {
  position: relative;
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 28px;
  margin-top: 2px;
}

.analysis-config-card .simple-check input[type="checkbox"] {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: 0;
  opacity: 0;
  pointer-events: none;
}

.analysis-config-card .check-mark {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.16);
  background: rgba(255, 255, 255, 0.86);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.analysis-config-card .check-mark::after {
  content: "";
  width: 9px;
  height: 5px;
  border-bottom: 2px solid #fff;
  border-left: 2px solid #fff;
  opacity: 0;
  transform: translateY(-1px) rotate(-45deg);
}

.analysis-config-card .simple-check input[type="checkbox"]:checked + .check-mark {
  border-color: transparent;
  background: linear-gradient(135deg, var(--accent) 0%, #38bdf8 100%);
  box-shadow: 0 8px 18px rgba(15, 143, 179, 0.18);
}

.analysis-config-card .simple-check input[type="checkbox"]:checked + .check-mark::after {
  opacity: 1;
}

.analysis-config-card .simple-check:focus-within .check-mark {
  box-shadow: 0 0 0 4px rgba(15, 143, 179, 0.12);
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(250, 251, 253, 0.78);
}

.summary-row span {
  color: var(--muted);
}

.summary-row strong {
  max-width: 68%;
  text-align: right;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.progress-card {
  display: grid;
  gap: 10px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(226, 109, 61, 0.12);
  background: linear-gradient(180deg, rgba(255, 247, 241, 0.92) 0%, rgba(255, 251, 248, 0.96) 100%);
}

.progress-head,
.result-section-head,
.stage-timeline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.progress-head strong,
.result-section-head h3,
.stage-timeline-head strong {
  margin: 0;
}

.progress-head span,
.stage-timeline-head span {
  color: var(--accent-dark);
  font-weight: 700;
}

.progress-track {
  position: relative;
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.08);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent) 0%, #ef9b67 100%);
  transition: width 0.24s ease;
}

.progress-copy {
  margin: 0;
}

.video-compare-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(380px, 1fr));
  gap: 16px;
}

.compact-stage-panel {
  display: grid;
  grid-template-rows: auto minmax(clamp(380px, 34vw, 640px), 1fr);
  min-height: 100%;
}

.compact-stage-panel .player {
  width: 100%;
  min-height: clamp(380px, 34vw, 640px);
  max-height: min(70vh, 720px);
  object-fit: contain;
  background: #0f172a;
}

.analysis-stage-card .player-frame {
  min-height: clamp(380px, 34vw, 640px);
  background:
    radial-gradient(circle at 20% 12%, rgba(226, 109, 61, 0.14), transparent 30%),
    linear-gradient(180deg, #111827 0%, #0f172a 100%);
}

.stage-timeline {
  display: grid;
  gap: 14px;
  padding-top: 10px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

.timeline-track {
  position: relative;
  height: 14px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(15, 23, 42, 0.08);
  overflow: hidden;
  cursor: pointer;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.08);
}

.timeline-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #f09b66);
}

.track-marker {
  position: absolute;
  top: -8px;
  transform: translateX(-50%);
  border: 0;
  background: transparent;
  padding: 0;
  box-shadow: none;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.result-metrics,
.local-frame-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.analysis-result-grid {
  grid-template-columns: minmax(0, 1.1fr) minmax(300px, 0.9fr);
}

.ai-coach-card {
  border-color: rgba(36, 87, 214, 0.16);
  background:
    radial-gradient(circle at top right, rgba(36, 87, 214, 0.1), transparent 30%),
    rgba(255, 255, 255, 0.86);
}

.ai-coach-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.ai-plan-list {
  display: grid;
  gap: 10px;
}

.compare-page .sub-card {
  box-shadow: none;
  background: rgba(255, 255, 255, 0.76);
}

.simple-card {
  border-style: solid;
}

.focus-copy,
.frame-advice {
  color: var(--text);
  font-size: 1rem;
}

.confidence-list,
.simple-downloads {
  margin-top: 0;
}

.focus-marker-list {
  display: grid;
  gap: 10px;
}

.focus-marker-item {
  width: 100%;
  text-align: left;
  border: 1px solid rgba(15, 143, 179, 0.18);
  background: rgba(248, 252, 255, 0.92);
  border-radius: 18px;
  padding: 12px 14px;
  display: grid;
  gap: 6px;
}

.simple-downloads {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px 16px;
}

.simple-downloads a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  padding: 0.8rem 1rem;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.06);
  text-decoration: none;
  font-weight: 700;
  text-align: center;
}

.m-pose {
  color: #1d4ed8;
}

.m-tempo {
  color: #0f8fb3;
}

.m-track {
  color: #45556f;
}

.activeMode {
  background: linear-gradient(135deg, var(--accent) 0%, #38bdf8 100%);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 12px 24px rgba(15, 143, 179, 0.22);
}

@media (max-width: 1280px) {
  .analysis-workbench,
  .analysis-result-grid {
    grid-template-columns: 1fr;
  }

  .analysis-rail {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1024px) {
  .compare-kpi-row,
  .workflow-stepper,
  .video-compare-grid,
  .ai-coach-grid,
  .result-metrics,
  .local-frame-grid,
  .simple-downloads {
    grid-template-columns: 1fr;
  }

  .summary-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-row strong {
    max-width: none;
    text-align: left;
  }
}

@media (max-width: 720px) {
  .panel-head,
  .result-section-head,
  .stage-timeline-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
