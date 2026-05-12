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
import { usePipelineTaskState } from "./usePipelineTaskState";
import { createPipelinePoller } from "../services/pipelinePolling";
import {
  isRunningPipelineStatus,
  pipelineStageText as formatPipelineStageText,
  pipelineStatusText as formatPipelineStatusText,
} from "../services/pipelineStatus";
import { normalizedConfidenceIssues, normalizedConfidenceSummary } from "../utils/confidence";
import { friendlyError } from "../utils/errors";
import { checkVideoPairQuality, listVideos } from "../api/videos";
import type {
  AiCoachResponse,
  PipelineFrameRangeResponse,
  PipelineResultResponse,
  VideoQualityMeta,
  VideoQualityResponse,
  VideoItem,
} from "../types/video";

export function useComparePage() {
  type WorkflowStepState = "done" | "active" | "locked";

  const route = useRoute();

  const loading = ref(false);
  const error = ref("");
  const items = ref<VideoItem[]>([]);
  const teacherId = ref("");
  const userId = ref("");
  const overwrite = ref(false);
  const analyzing = ref(false);
  const {
    pipelineId,
    pipelineStatus,
    pipelineStage,
    pipelineProgress,
    pipelineMessage,
    cancelRequested,
    pipelineStatusText,
    pipelineStageText,
    pipelineProgressPercent,
    canCancelCurrentPipeline,
    applyPipelineMeta,
    resetPipelineTask,
    preparePipelineTask,
  } = usePipelineTaskState();
  const cancelingPipeline = ref(false);
  const result = ref<PipelineResultResponse | null>(null);
  const aiCoach = ref<AiCoachResponse | null>(null);
  const aiCoachLoading = ref(false);
  const aiCoachError = ref("");
  const analysisMode = ref<"overall" | "local">("overall");
  const frameDetailCache = ref<Record<number, Record<string, any>>>({});
  const frameDetailLoading = ref(false);
  const qualityCheck = ref<VideoQualityResponse | null>(null);
  const qualityCheckLoading = ref(false);
  const FRAME_WINDOW_RADIUS = 12;
  const REVIEW_PLAYBACK_RATE = 0.5;
  let qualityCheckToken = 0;

  const teacherItems = computed(() => items.value.filter((item) => item.role === "teacher"));
  const userItems = computed(() => items.value.filter((item) => item.role === "user"));
  const selectedTeacher = computed(() => teacherItems.value.find((item) => item.video_id === teacherId.value));
  const selectedUser = computed(() => userItems.value.find((item) => item.video_id === userId.value));
  const selectedTeacherLabel = computed(() => selectedTeacher.value?.filename ?? "尚未选择教师视频");
  const selectedUserLabel = computed(() => selectedUser.value?.filename ?? "尚未选择学员视频");
  const teacherUrl = computed(() => (selectedTeacher.value ? absMediaUrl(selectedTeacher.value.url) : ""));
  const userUrl = computed(() => (selectedUser.value ? absMediaUrl(selectedUser.value.url) : ""));
  const analysisHint = computed(() => {
    if (!teacherId.value || !userId.value) return "状态：等待选择。操作：补齐教师和学员素材。反馈：质检自动开始。";
    if (analyzing.value || isRunningPipelineStatus(pipelineStatus.value)) return "状态：分析中。操作：等待或取消任务。反馈：结果会自动刷新。";
    if (!result.value) return "状态：组合就绪。操作：发起分析。反馈：生成评分和问题片段。";
    return "状态：结果已生成。操作：回放问题点。反馈：定位到复盘建议。";
  });
  const analysisFeedbackText = computed(() => {
    if (error.value) return error.value;
    if (analyzing.value || isRunningPipelineStatus(pipelineStatus.value)) {
      const stage = pipelineStageText.value;
      const message = pipelineMessage.value?.trim();
      if (message) return `${stage} - ${message}`;
      return `${stage} - ${pipelineProgressPercent.value}%`;
    }
    return analysisHint.value;
  });
  const hasSelectedPair = computed(() => Boolean(teacherId.value && userId.value));
  const canStartAnalysis = computed(() => {
    if (!teacherId.value || !userId.value || analyzing.value || qualityCheckLoading.value) return false;
    return qualityCheck.value?.level !== "error";
  });
  const qualityCheckTitle = computed(() => {
    if (qualityCheckLoading.value) return "正在检查";
    if (!qualityCheck.value) return "等待检查结果";
    return qualityCheck.value.summary || "检查完成";
  });
  const qualityCheckBadge = computed(() => {
    if (qualityCheckLoading.value) return "检查中";
    if (qualityCheck.value?.level === "good") return "适合分析";
    if (qualityCheck.value?.level === "warning") return "可继续，有提醒";
    if (qualityCheck.value?.level === "error") return "请更换视频";
    return "待检查";
  });
  const qualityCheckRecommendations = computed(() => {
    const list = qualityCheck.value?.recommendations || [];
    return list.length ? list.slice(0, 3) : ["状态：质检通过。操作：发起分析。反馈：评分解释更稳定。"];
  });
  const hasActivePipeline = computed(() => analyzing.value || isRunningPipelineStatus(pipelineStatus.value));
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
        copy: selectDone ? "状态：素材就绪。操作：确认组合。反馈：进入分析。" : "状态：待选择。操作：选教师和学员。反馈：自动质检。",
        state: selectDone ? "done" : "active",
      },
      {
        key: "run",
        index: "02",
        title: "确认并分析",
        copy: hasActivePipeline.value ? analysisFeedbackText.value : pipelineId.value ? "状态：任务已创建。操作：查看进度。反馈：完成后加载结果。" : "状态：可提交。操作：发起分析。反馈：生成结果。",
        state: runDone ? "done" : runActive ? "active" : "locked",
      },
      {
        key: "review",
        index: "03",
        title: "复盘结果",
        copy: result.value ? "状态：结果就绪。操作：查看问题片段。反馈：得到训练建议。" : "状态：等待结果。操作：保持页面。反馈：完成后开放复盘。",
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
    if (!Array.isArray(joints) || joints.length === 0) return "状态：暂无关节排序。操作：完成分析。反馈：显示优先处理部位。";
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
  const resultConfidenceScore = computed(() => confidenceData.value?.score ?? result.value?.report?.confidence_score ?? null);
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
  const aiCoachFallbackHint = computed(() => {
    if (aiCoach.value?.generated_by !== "local_fallback") return "";
    return "状态：云端 AI 不可用。操作：使用本地规则。反馈：复盘流程仍可继续。";
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

  function formatQualityMeta(meta?: VideoQualityMeta | null) {
    if (!meta) return "暂无元信息";
    if (meta.readable === false) return meta.error || "无法读取";
    const durationText = formatSecondsMaybe(meta.duration_sec);
    const width = Number(meta.width);
    const height = Number(meta.height);
    const resolution = Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0 ? `${width}x${height}` : "--";
    const fps = Number(meta.fps);
    const fpsText = Number.isFinite(fps) && fps > 0 ? `${fps.toFixed(1)}fps` : "--";
    return `${durationText} / ${resolution} / ${fpsText}`;
  }

  async function refreshQualityCheck() {
    const teacher = teacherId.value;
    const user = userId.value;
    qualityCheckToken += 1;
    const token = qualityCheckToken;
    qualityCheck.value = null;
    if (!teacher || !user) {
      qualityCheckLoading.value = false;
      return;
    }

    qualityCheckLoading.value = true;
    try {
      const response = await checkVideoPairQuality({
        teacherVideoId: teacher,
        userVideoId: user,
      });
      if (token === qualityCheckToken) {
        qualityCheck.value = response;
      }
    } catch (e: any) {
      if (token === qualityCheckToken) {
        qualityCheck.value = {
          ok: false,
          level: "error",
          summary: friendlyError(e, "视频质量检查失败"),
          checks: [],
          teacher_meta: null,
          user_meta: null,
          recommendations: ["请确认本地后端和 ffprobe 可用，或重新选择视频后再试。"],
        };
      }
    } finally {
      if (token === qualityCheckToken) {
        qualityCheckLoading.value = false;
      }
    }
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
    return formatPipelineStatusText(status);
  }

  function stageToText(stage?: string, status?: string) {
    return formatPipelineStageText(stage, status);
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

  const pipelinePoller = createPipelinePoller({
    getStatus: getPipelineStatus,
    onStatus: applyPipelineMeta,
    onTerminal: handleTerminalPipelineStatus,
    onError(pollError) {
      analyzing.value = false;
      error.value = friendlyError(pollError, "流程状态查询失败");
    },
  });

  function stopPolling() {
    pipelinePoller.stop();
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

  async function handleTerminalPipelineStatus(status: { pipeline_id: string }) {
    const id = status.pipeline_id;
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

  async function pollStatus(id: string) {
    try {
      await pipelinePoller.tick(id);
    } catch (e: any) {
      stopPolling();
      analyzing.value = false;
      error.value = friendlyError(e, "流程状态查询失败");
    }
  }

  async function startAnalysis() {
    if (!teacherId.value || !userId.value) return;
    if (qualityCheck.value?.level === "error") {
      error.value = "视频质量检查未通过，请更换视频后再发起分析。";
      return;
    }
    analyzing.value = true;
    result.value = null;
    aiCoach.value = null;
    aiCoachError.value = "";
    frameDetailCache.value = {};
    frameDetailLoading.value = false;
    preparePipelineTask();
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
      pipelinePoller.start(response.pipeline_id, { immediate: false });
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
    resetPipelineTask();
    routeSeekSec.value = null;
    void refreshQualityCheck();
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

  return {
    loading,
    error,
    items,
    teacherId,
    userId,
    overwrite,
    analyzing,
    pipelineId,
    pipelineStatus,
    pipelineStage,
    pipelineProgress,
    pipelineMessage,
    cancelRequested,
    cancelingPipeline,
    result,
    aiCoach,
    aiCoachLoading,
    aiCoachError,
    analysisMode,
    frameDetailCache,
    frameDetailLoading,
    qualityCheck,
    qualityCheckLoading,
    FRAME_WINDOW_RADIUS,
    REVIEW_PLAYBACK_RATE,
    qualityCheckToken,
    teacherItems,
    userItems,
    selectedTeacher,
    selectedUser,
    selectedTeacherLabel,
    selectedUserLabel,
    teacherUrl,
    userUrl,
    pipelineStatusText,
    pipelineStageText,
    pipelineProgressPercent,
    canCancelCurrentPipeline,
    analysisHint,
    analysisFeedbackText,
    hasSelectedPair,
    canStartAnalysis,
    qualityCheckTitle,
    qualityCheckBadge,
    qualityCheckRecommendations,
    hasActivePipeline,
    workflowSteps,
    displayTeacherUrl,
    displayUserUrl,
    markers,
    markerDots,
    problemHighlights,
    mapUserSecArr,
    teacherToUserArr,
    fpsTeacher,
    fpsUser,
    frameAnalysisCount,
    currentFrameIndex,
    hasFrameAnalysis,
    currentFrameInfo,
    overallScore,
    poseScore,
    tempoScore,
    overallAdvice,
    topJointSummary,
    tempoSegmentSummary,
    confidenceData,
    resultConfidenceScore,
    confidenceLevelText,
    confidenceScoreText,
    confidenceSummaryText,
    confidenceIssues,
    aiCoachSourceText,
    aiCoachFallbackHint,
    confidenceTone,
    teacherRef,
    userRef,
    playing,
    duration,
    currentTime,
    pendingSeekSec,
    routeSeekSec,
    teacherMuted,
    userMuted,
    allMuted,
    lastSeekAtMs,
    filteredDiff,
    SYNC_SEEK_THRESHOLD_SEC,
    SYNC_SEEK_COOLDOWN_MS,
    SYNC_RATE_DEADZONE_SEC,
    SYNC_RATE_MIN,
    SYNC_RATE_MAX,
    SYNC_RATE_GAIN,
    getSeekableEnd,
    getSeekableStart,
    formatSecondsMaybe,
    formatQualityMeta,
    refreshQualityCheck,
    timingOffsetText,
    markerLabel,
    markerClass,
    pipelineStatusToText,
    stageToText,
    severityText,
    markerFocusCopy,
    applyPlaybackRates,
    restoreNormalPlayback,
    stopSyncTimer,
    stopPolling,
    applyPipelineMeta,
    mapUserSec,
    syncLoop,
    refreshDuration,
    onTeacherTimeUpdate,
    onTeacherPlay,
    onTeacherPause,
    togglePlay,
    seekBoth,
    applyMuteState,
    toggleTeacherMute,
    toggleUserMute,
    toggleAllMute,
    onTrackClick,
    seekToMarker,
    focusMarker,
    jumpPrevMarker,
    jumpNextMarker,
    stepBy,
    routeQueryValue,
    hydrateFromRoute,
    loadList,
    pollStatus,
    startAnalysis,
    loadAiCoach,
    cancelCurrentPipeline,
    ensureFrameWindow,
    ensureFrameDetail,
  };
}
