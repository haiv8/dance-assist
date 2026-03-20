<template>
  <main class="app-page compare-page">
    <section class="surface-card page-head">
      <div class="page-head-row">
        <div>
          <h1>动作分析</h1>
          <p class="page-subtitle">选择教师示范与学员练习，系统会生成同步回放和问题摘要。</p>
        </div>
        <button class="secondary-button" :disabled="loading" @click="loadList">
          {{ loading ? '刷新中...' : '同步素材库' }}
        </button>
      </div>
      <div class="status-strip analysis-strip">
        <div class="status-cell">
          <span class="status-caption">流程状态</span>
          <strong class="status-main">{{ pipelineStatusText }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">问题点</span>
          <strong class="status-main">{{ markerDots.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">当前总分</span>
          <strong class="status-main">{{ result ? overallScore.toFixed(1) : '--' }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">流程提示</span>
          <strong class="status-main">{{ analysisFeedbackText }}</strong>
        </div>
      </div>
    </section>

    <section class="selection-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>分析配置</h2>
            <p class="helper-text">先确认本轮对照素材，再发起分析任务。</p>
          </div>
        </div>

        <div class="field-grid two-col-fields">
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
          <span>覆盖历史结果</span>
        </label>

        <div class="action-row" style="margin-top: 16px;">
          <button :disabled="!teacherId || !userId || analyzing" @click="startAnalysis">
            {{ analyzing ? '分析进行中...' : '发起分析' }}
          </button>
        </div>

        <div v-if="error" class="feedback-inline" style="margin-top: 12px;">{{ error }}</div>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>本轮组合</h2>
            <p class="helper-text">发起前再次确认本轮分析对象。</p>
          </div>
        </div>

        <div v-if="loading && !items.length" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">素材库正在同步</strong>
          <span class="feedback-state-copy">系统正在读取教师与学员素材，完成后会自动补齐默认组合。</span>
        </div>

        <div v-else class="summary-stack">
          <div class="summary-row">
            <span>&#25945;&#24072;&#32032;&#26448;</span>
            <strong>{{ selectedTeacherLabel }}</strong>
          </div>
          <div class="summary-row">
            <span>&#23398;&#21592;&#32032;&#26448;</span>
            <strong>{{ selectedUserLabel }}</strong>
          </div>
          <div class="summary-row">
            <span>&#20219;&#21153; ID</span>
            <strong>{{ pipelineId || '&#23578;&#26410;&#21019;&#24314;&#20219;&#21153;' }}</strong>
          </div>
          <div v-if="pipelineId" class="progress-card">
            <div class="progress-head">
              <strong>{{ pipelineStageText }}</strong>
              <span>{{ pipelineProgressPercent }}%</span>
            </div>
            <div class="progress-track"><div class="progress-fill" :style="{ width: `${pipelineProgressPercent}%` }"></div></div>
            <p class="helper-text progress-copy">{{ pipelineMessage || analysisHint }}</p>
          </div>
        </div>
      </article>
    </section>

    <section class="players-grid">
      <article class="video-panel">
        <div class="panel-head compact-head">
          <div>
            <h2>教师示范</h2>
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
              <span class="feedback-state-copy">先选择教师示范视频，左侧播放器才会进入同步回放区状态。</span>
            </div>
          </div>
        </div>
      </article>

      <article class="video-panel">
        <div class="panel-head compact-head">
          <div>
            <h2>学员练习</h2>
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
              <strong class="feedback-state-title">学员练习未就绪</strong>
              <span class="feedback-state-copy">选择学员练习视频后，系统会自动准备双视频对照。</span>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="timeline-card" v-if="displayTeacherUrl && displayUserUrl">
      <div class="panel-head compact-head">
        <div>
          <h2>同步回放区</h2>
          <p class="helper-text">{{ currentTime.toFixed(2) }}s / {{ duration.toFixed(2) }}s</p>
        </div>
      </div>

      <div class="timeline-actions">
        <button class="secondary-button" @click="togglePlay">{{ playing ? '暂停' : '播放' }}</button>
        <button class="secondary-button" @click="stepBy(-1)">-1s</button>
        <button class="secondary-button" @click="stepBy(1)">+1s</button>
        <button class="secondary-button" :disabled="!markerDots.length" @click="jumpPrevMarker">定位上一处问题</button>
        <button class="secondary-button" :disabled="!markerDots.length" @click="jumpNextMarker">定位下一处问题</button>
        <button class="ghost-button" @click="toggleTeacherMute">{{ teacherMuted ? '取消教师音轨静音' : '教师音轨静音' }}</button>
        <button class="ghost-button" @click="toggleUserMute">{{ userMuted ? '取消学员音轨静音' : '学员音轨静音' }}</button>
        <button class="ghost-button" @click="toggleAllMute">{{ allMuted ? '取消全部静音' : '全部静音' }}</button>
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
          •
        </button>
      </div>
    </section>

    <section class="result-card" v-if="result || analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running'">
      <div class="panel-head compact-head">
        <div>
          <h2>分析结果</h2>
          <p class="helper-text">{{ result?.pair_name || '本轮分析完成后，结果会展示在这里。' }}</p>
        </div>
        <div class="mode-switch" v-if="result">
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
          <div class="metric-chip"><strong>&#24635;&#20998;</strong><span>{{ overallScore.toFixed(2) }}</span></div>
          <div class="metric-chip"><strong>&#21160;&#20316;</strong><span>{{ poseScore.toFixed(2) }}</span></div>
          <div class="metric-chip"><strong>&#33410;&#22863;</strong><span>{{ tempoScore.toFixed(2) }}</span></div>
          <div class="metric-chip"><strong>&#21487;&#20449;&#24230;</strong><span>{{ confidenceScoreText }}</span></div>
        </div>

        <div class="selection-grid" style="margin-top: 16px;">
          <article class="surface-card sub-card simple-card">
            <h3>&#25972;&#20307;&#24314;&#35758;</h3>
            <p class="helper-text focus-copy">{{ overallAdvice }}</p>
          </article>

          <article class="surface-card sub-card simple-card">
            <div class="confidence-head">
              <h3>Analysis &#21487;&#20449;&#24230;</h3>
              <span class="tag" :class="confidenceTone">{{ confidenceLevelText }}</span>
            </div>
            <p class="helper-text focus-copy">{{ confidenceSummaryText }}</p>
            <ul v-if="confidenceIssues.length" class="list-clean confidence-list">
              <li v-for="issue in confidenceIssues" :key="issue.code || issue.message" class="list-item-card">
                <strong>{{ issue.message }}</strong>
                <span class="helper-text">{{ issue.suggestion }}</span>
              </li>
            </ul>
          </article>
        </div>

        <div class="selection-grid" style="margin-top: 16px;">
          <article class="surface-card sub-card simple-card">
            <h3>&#37325;&#28857;&#21457;&#29616;</h3>
            <ul class="list-clean">
              <li class="list-item-card"><strong>&#39640;&#35823;&#24046;&#20851;&#33410;</strong><span class="helper-text">{{ topJointSummary }}</span></li>
              <li class="list-item-card"><strong>&#33410;&#22863; windows</strong><span class="helper-text">{{ tempoSegmentSummary }}</span></li>
            </ul>
          </article>
        </div>

        <article class="surface-card sub-card simple-card" v-if="result.report?.beginner_report?.summary || result.report?.teaching_report?.summary" style="margin-top: 16px;">
          <h3>&#35757;&#32451;&#24314;&#35758;</h3>
          <p class="helper-text" v-if="result.report?.beginner_report?.summary">&#23398;&#21592;&#21453;&#39304;&#65306; {{ result.report.beginner_report.summary }}</p>
          <p class="helper-text" v-if="result.report?.teaching_report?.summary">&#25945;&#23398;&#24314;&#35758;&#65306; {{ result.report.teaching_report.summary }}</p>
        </article>
      </template>

      <template v-else>
        <div v-if="!currentFrameInfo && frameDetailLoading" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">当前帧详情加载中</strong>
          <span class="feedback-state-copy">系统正在补充这一帧的详细分析，请稍候。</span>
        </div>

        <div v-else-if="currentFrameInfo" class="surface-card sub-card simple-card">
          <div class="metric-row compact-stats">
            <div class="metric-chip"><strong>帧号</strong><span>{{ currentFrameInfo.frame }}</span></div>
            <div class="metric-chip"><strong>时间</strong><span>{{ Number(currentFrameInfo.sec).toFixed(2) }}s</span></div>
            <div class="metric-chip"><strong>误差</strong><span>{{ Number(currentFrameInfo.frame_error ?? 0).toFixed(4) }}</span></div>
          </div>
          <p class="helper-text focus-copy" style="margin-top: 16px;">{{ currentFrameInfo.advice }}</p>
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
import { absMediaUrl } from "../api/http";
import { getPipelineFrameDetail, getPipelineResult, getPipelineResultSummary, getPipelineStatus, runPipeline } from "../api/pipelines";
import { listVideos } from "../api/videos";
import type { PipelineResultResponse, PipelineRunResponse, PipelineStatusResponse, PipelineStatusType, VideoItem } from "../types/video";

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
const result = ref<PipelineResultResponse | null>(null);
const analysisMode = ref<"overall" | "local">("overall");
const frameDetailCache = ref<Record<number, Record<string, any>>>({});
const frameDetailLoading = ref(false);
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
const analysisHint = computed(() => {
  if (!teacherId.value || !userId.value) return "\u5148\u9009\u62e9\u6559\u5e08\u548c\u5b66\u5458\u7d20\u6750";
  if (analyzing.value || pipelineStatus.value === "pending" || pipelineStatus.value === "running") return "\u5206\u6790\u8fdb\u884c\u4e2d\uff0c\u7ed3\u679c\u4f1a\u81ea\u52a8\u5237\u65b0";
  if (!result.value) return "\u5f53\u524d\u7ec4\u5408\u5df2\u5c31\u7eea\uff0c\u53ef\u4ee5\u5f00\u59cb\u5206\u6790";
  return "\u7ed3\u679c\u5df2\u751f\u6210\uff0c\u53ef\u56de\u653e\u5e76\u5b9a\u4f4d\u95ee\u9898\u70b9";
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
const markerDots = computed(() => markers.value.map((item) => ({ ...item, leftPct: duration.value > 1e-6 ? Math.max(0, Math.min(100, (item.sec / duration.value) * 100)) : 0 })));

const mapUserSecArr = computed<number[]>(() => Array.isArray(result.value?.timeline?.map_user_sec) ? result.value!.timeline!.map_user_sec.map((value: any) => Number(value)) : []);
const teacherToUserArr = computed<number[]>(() => Array.isArray(result.value?.timeline?.teacher_to_user) ? result.value!.timeline!.teacher_to_user.map((value: any) => Number(value)) : []);
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
  return Array.isArray(result.value?.report?.frame_analysis) ? result.value!.report!.frame_analysis.length : 0;
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
  if (!Array.isArray(list) || list.length === 0) return "\u6682\u65e0\u660e\u663e\u8282\u594f\u5f02\u5e38\u533a\u95f4\u3002";
  return `\u5171 ${list.length} \u6bb5\u9700\u8981\u91cd\u70b9\u590d\u76d8\u7684\u8282\u594f\u5f02\u5e38\u7247\u6bb5\u3002`;
});
const confidenceData = computed<Record<string, any> | null>(() => {
  const confidence = result.value?.report?.confidence;
  return confidence && typeof confidence === "object" ? confidence : null;
});
const confidenceLevelText = computed(() => {
  const level = String(confidenceData.value?.level ?? "");
  if (level === "high") return "\u9ad8";
  if (level === "medium") return "\u4e2d";
  if (level === "low") return "\u4f4e";
  return "--";
});
const confidenceScoreText = computed(() => {
  const score = Number(confidenceData.value?.score);
  if (!Number.isFinite(score)) return "--";
  return `${Math.round(score * 100)}%`;
});
const confidenceSummaryText = computed(() => confidenceData.value?.summary ?? "&#21487;&#20449;&#24230; is estimated from tracking quality, alignment stability, and tempo reliability.");
const confidenceIssues = computed<any[]>(() => {
  const issues = confidenceData.value?.issues;
  return Array.isArray(issues) ? issues : [];
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
  if (status === "pending") return "\u7b49\u5f85\u4e2d";
  if (status === "running") return "\u5206\u6790\u4e2d";
  if (status === "done") return "\u5df2\u5b8c\u6210";
  if (status === "failed") return "\u5931\u8d25";
  return status || "\u672a\u5f00\u59cb";
}

function stageToText(stage?: string, status?: string) {
  if (stage === "queued") return "\u5df2\u8fdb\u5165\u961f\u5217";
  if (stage === "preparing_inputs") return "\u51c6\u5907\u7d20\u6750";
  if (stage === "extracting_pose") return "\u63d0\u53d6\u9aa8\u67b6";
  if (stage === "aligning_motion") return "\u52a8\u4f5c\u5bf9\u9f50\u4e0e\u8bc4\u5206";
  if (stage === "rendering_outputs") return "\u751f\u6210\u5bf9\u6bd4\u8f93\u51fa";
  if (stage === "packaging_results") return "\u6574\u7406\u7ed3\u679c";
  if (stage === "completed") return "\u7ed3\u679c\u5df2\u5c31\u7eea";
  if (stage === "failed") return "\u4efb\u52a1\u5931\u8d25";
  return pipelineStatusToText(status);
}

function statusTagClass(status?: string) {
  if (status === "done") return "ok";
  if (status === "failed") return "danger";
  if (status === "running" || status === "pending") return "warn";
  return "";
}

function severityText(severity?: string) {
  if (severity === "mild") return "轻度";
  if (severity === "clear") return "明显";
  if (severity === "severe") return "严重";
  return severity || "-";
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
  const targetUserSec = mapUserSec(teacher.currentTime);
  const diff = targetUserSec - user.currentTime;
  filteredDiff = 0.7 * filteredDiff + 0.3 * diff;
  const now = Date.now();
  const absDiff = Math.abs(filteredDiff);

  if (absDiff > SYNC_SEEK_THRESHOLD_SEC && now - lastSeekAtMs >= SYNC_SEEK_COOLDOWN_MS) {
    user.currentTime = targetUserSec;
    user.playbackRate = 1;
    lastSeekAtMs = now;
  } else if (absDiff <= SYNC_RATE_DEADZONE_SEC) {
    user.playbackRate = 1;
  } else {
    user.playbackRate = Math.max(SYNC_RATE_MIN, Math.min(SYNC_RATE_MAX, 1 + SYNC_RATE_GAIN * filteredDiff));
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
    userRef.value.playbackRate = 1;
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
    userRef.value.playbackRate = 1;
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
    error.value = e?.response?.data?.detail ?? e?.message ?? "视频列表加载失败";
  } finally {
    loading.value = false;
  }
}

async function pollStatus(id: string) {
  try {
    const status = await getPipelineStatus(id);
    applyPipelineMeta(status);
    if (status.status === "done" || status.status === "failed") {
      stopPolling();
      analyzing.value = false;
      try {
        result.value = await getPipelineResultSummary(id);
      } catch {
        result.value = await getPipelineResult(id);
      }
      applyPipelineMeta(result.value);
      analysisMode.value = "overall";
    }
  } catch (e: any) {
    stopPolling();
    analyzing.value = false;
    error.value = e?.response?.data?.detail ?? e?.message ?? "流程状态查询失败";
  }
}

async function startAnalysis() {
  if (!teacherId.value || !userId.value) return;
  analyzing.value = true;
  result.value = null;
  frameDetailCache.value = {};
  frameDetailLoading.value = false;
  pipelineMessage.value = "";
  pipelineStage.value = "queued";
  pipelineProgress.value = 0;
  error.value = "";
  try {
    const response = await runPipeline({ teacher_video_id: teacherId.value, user_video_id: userId.value, overwrite: overwrite.value });
    pipelineId.value = response.pipeline_id;
    applyPipelineMeta(response);
    stopPolling();
    pollTimer = window.setInterval(() => { void pollStatus(response.pipeline_id); }, 2000);
    await pollStatus(response.pipeline_id);
  } catch (e: any) {
    analyzing.value = false;
    error.value = e?.response?.data?.detail ?? e?.message ?? "流程启动失败";
  }
}

async function ensureFrameDetail(frame: number | null) {
  if (frame === null || !pipelineId.value || frameDetailCache.value[frame]) return;
  if (Array.isArray(result.value?.report?.frame_analysis)) return;
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
  stopSyncTimer();
});
watch([teacherMuted, userMuted], applyMuteState);
watch([teacherId, userId], () => {
  result.value = null;
  analysisMode.value = "overall";
  frameDetailCache.value = {};
  frameDetailLoading.value = false;
  pipelineId.value = "";
  pipelineStatus.value = "";
  pipelineStage.value = "";
  pipelineProgress.value = 0;
  pipelineMessage.value = "";
  routeSeekSec.value = null;
});
watch([analysisMode, currentFrameIndex, result], ([mode, frame]) => {
  if (mode !== "local") return;
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
.analysis-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-stack {
  display: grid;
  gap: 12px;
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
  transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}

.summary-row:hover {
  transform: translateY(-1px);
  background: rgba(255, 250, 247, 0.92);
  border-color: rgba(226, 109, 61, 0.14);
}

.summary-row span {
  color: var(--muted);
}

.summary-row strong {
  max-width: 70%;
  text-align: right;
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
.confidence-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.progress-head strong,
.confidence-head h3 {
  margin: 0;
}

.progress-head span {
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

.result-metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.confidence-list {
  margin-top: 14px;
}

.tag.neutral {
  background: rgba(15, 23, 42, 0.06);
  color: var(--text);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.compact-head {
  margin-bottom: 16px;
}

.panel-head h2,
.panel-head h3 {
  margin: 0;
}

.two-col-fields,
.compact-stats {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.simple-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  color: var(--text);
  font-weight: 600;
}

.simple-check input {
  width: auto;
}

.compare-page .sub-card {
  box-shadow: none;
  background: rgba(255, 255, 255, 0.76);
}

.simple-card {
  border-style: solid;
}

.focus-copy {
  color: var(--text);
  font-size: 1rem;
}

.timeline-track {
  position: relative;
  margin: 18px 0 0;
  height: 16px;
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
  top: -2px;
  transform: translateX(-50%);
  border: 0;
  background: transparent;
  padding: 0;
  box-shadow: none;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: transform 0.16s ease, opacity 0.16s ease;
}

.track-marker:hover {
  transform: translateX(-50%) scale(1.16);
}

.mode-switch {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.activeMode {
  background: linear-gradient(135deg, var(--accent) 0%, #eb8d56 100%);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 8px 18px rgba(226, 109, 61, 0.18);
}

.simple-downloads {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px 16px;
  margin-top: 20px;
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
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}

.simple-downloads a:hover {
  transform: translateY(-1px);
  border-color: rgba(226, 109, 61, 0.14);
  background: rgba(255, 250, 247, 0.92);
}

.m-pose {
  color: #972b21;
}

.m-tempo {
  color: #9a6510;
}

.m-track {
  color: #45556f;
}

@media (max-width: 1024px) {
  .compact-stats,
  .two-col-fields,
  .simple-downloads,
  .analysis-strip {
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
  .panel-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
