<template>
  <main class="app-page compare-page compare-workbench">
    <section class="surface-card page-head compare-head">
      <div class="page-head-row">
        <div>
          <h1>动作分析 <InfoHint text="选择教师示范和学员练习，发起分析后查看评分、问题片段和复盘建议。" /></h1>
          <p class="page-subtitle">选择素材，开始一次复盘。</p>
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

    <section class="analysis-workbench">
      <section class="surface-card analysis-stage-card">
        <div class="panel-head compact-head">
          <div>
            <h2>对照舞台 <InfoHint text="播放或跳转时间点时，两段视频会尽量同步；问题点会标在时间轴上。" /></h2>
            <p class="helper-text">播放、暂停并定位问题点。</p>
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
                  <span class="feedback-state-copy">请选择教师示范素材。</span>
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
                  <span class="feedback-state-copy">请选择学员练习素材。</span>
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

      <aside class="analysis-rail">
        <article class="surface-card analysis-config-card">
          <div class="panel-head compact-head">
            <div>
              <h2>分析配置 <InfoHint text="选择两段视频后会自动完成质量检查，通过后即可发起分析。" /></h2>
              <p class="helper-text">选择教师和学员视频。</p>
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

          <EmptyState
            v-if="!loading && (!teacherItems.length || !userItems.length)"
            title="素材还不够"
            copy="先上传教师示范和学员练习。"
          >
            <template #actions>
              <RouterLink class="link-button secondary-button" to="/upload">去上传视频</RouterLink>
            </template>
          </EmptyState>

          <EmptyState
            v-else-if="!loading && (!teacherId || !userId)"
            title="等待选择视频"
            copy="选好两段视频后自动质检。"
          />

          <label class="simple-check">
            <input type="checkbox" v-model="overwrite" />
            <span class="check-mark" aria-hidden="true"></span>
            <span>覆盖历史结果</span>
          </label>

          <div v-if="teacherId && userId" class="quality-check-card" :data-level="qualityCheck?.level || 'checking'">
            <div class="quality-check-head">
              <div>
                <span class="quality-check-eyebrow">视频质量检查</span>
                <strong>{{ qualityCheckTitle }}</strong>
              </div>
              <span class="quality-badge">{{ qualityCheckBadge }}</span>
            </div>

            <div v-if="qualityCheckLoading" class="helper-text">正在读取视频元数据...</div>
            <template v-else-if="qualityCheck">
              <div class="quality-meta-grid">
                <div>
                  <span>教师视频</span>
                  <strong>{{ formatQualityMeta(qualityCheck.teacher_meta) }}</strong>
                </div>
                <div>
                  <span>学员视频</span>
                  <strong>{{ formatQualityMeta(qualityCheck.user_meta) }}</strong>
                </div>
              </div>
              <ul class="quality-recommendations">
                <li v-for="item in qualityCheckRecommendations" :key="item">{{ item }}</li>
              </ul>
            </template>
          </div>

          <div class="action-row rail-actions">
            <button :disabled="!canStartAnalysis" @click="startAnalysis">
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
              <h2>当前组合 <InfoHint text="这里展示本轮分析使用的素材和任务 ID，任务进度会在下方同步更新。" /></h2>
              <p class="helper-text">核对素材和任务 ID。</p>
            </div>
          </div>

          <div v-if="loading && !items.length" class="feedback-state" data-tone="loading">
            <strong class="feedback-state-title">素材库同步中</strong>
            <span class="feedback-state-copy">正在加载可用视频...</span>
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
      </aside>
    </section>

    <section class="result-card analysis-results" v-if="result || analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running'">
      <div class="panel-head compact-head">
        <div>
          <h2>分析结果 <InfoHint text="分析完成后展示总分、可信度、问题片段、AI 助教和局部帧详情。" /></h2>
          <p class="helper-text">{{ result?.pair_name || "等待分析结果。" }}</p>
        </div>
        <div class="mode-switch" v-if="result">
          <button class="secondary-button" :disabled="aiCoachLoading || !pipelineId" @click="loadAiCoach">
            {{ aiCoachLoading ? "AI生成中..." : "AI助教解读" }}
          </button>
          <button class="secondary-button" :class="{ activeMode: analysisMode === 'overall' }" @click="analysisMode = 'overall'">概览</button>
          <button class="secondary-button" :class="{ activeMode: analysisMode === 'local' }" :disabled="!hasFrameAnalysis" @click="analysisMode = 'local'">当前时刻</button>
        </div>
      </div>

      <ConfidenceBanner v-if="result" :confidence-score="resultConfidenceScore" />

      <template v-if="!result">
        <div class="feedback-state" :data-tone="analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running' ? 'loading' : 'empty'">
          <strong class="feedback-state-title">{{ analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running' ? '分析任务正在执行' : '暂时还没有分析结果' }}</strong>
          <span class="feedback-state-copy">{{ analyzing || pipelineStatus === 'pending' || pipelineStatus === 'running' ? analysisFeedbackText : '选择视频并发起任务。' }}</span>
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
            <p class="helper-text" v-if="aiCoachFallbackHint">{{ aiCoachFallbackHint }}</p>
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
          <p class="helper-text" v-if="result.report?.beginner_report?.summary">学员建议：{{ result.report.beginner_report.summary }}</p>
          <p class="helper-text" v-if="result.report?.teaching_report?.summary">教师建议：{{ result.report.teaching_report.summary }}</p>
        </article>
      </template>

      <template v-else>
        <div v-if="!currentFrameInfo && frameDetailLoading" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">当前帧详情加载中</strong>
          <span class="feedback-state-copy">正在补齐局部问题和建议...</span>
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
          <span class="feedback-state-copy">暂停到复盘位置后显示帧级细节。</span>
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
import { RouterLink } from "vue-router";
import EmptyState from "../components/EmptyState.vue";
import InfoHint from "../components/InfoHint.vue";
import ConfidenceBanner from "../components/records/ConfidenceBanner.vue";
import { useComparePage } from "../composables/useComparePage";

const page = useComparePage();
const {
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
} = page;
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
    "workbench"
    "result";
  align-items: stretch;
}

.compare-workbench > .compare-head {
  grid-area: head;
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
  grid-template-areas:
    "stage"
    "controls";
  align-items: start;
}

.analysis-workbench > .analysis-stage-card {
  grid-area: stage;
}

.analysis-workbench > .analysis-rail {
  grid-area: controls;
}

.analysis-rail {
  grid-template-columns: minmax(260px, 0.72fr) minmax(320px, 1fr);
  align-items: stretch;
}

.analysis-rail > .workflow-stepper {
  grid-column: 1 / -1;
}

.analysis-rail > .analysis-config-card,
.analysis-rail > .analysis-session-card,
.analysis-rail > .workflow-stepper {
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.04);
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

.quality-check-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.78);
}

.quality-check-card[data-level="good"] {
  border-color: rgba(21, 128, 61, 0.18);
  background: rgba(240, 253, 244, 0.72);
}

.quality-check-card[data-level="warning"] {
  border-color: rgba(226, 109, 61, 0.24);
  background: rgba(255, 247, 237, 0.72);
}

.quality-check-card[data-level="error"] {
  border-color: rgba(220, 38, 38, 0.22);
  background: rgba(254, 242, 242, 0.72);
}

.quality-check-head,
.quality-meta-grid {
  display: grid;
  gap: 10px;
}

.quality-check-head {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.quality-check-eyebrow,
.quality-meta-grid span {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.quality-check-head strong,
.quality-meta-grid strong {
  display: block;
  margin-top: 3px;
}

.quality-badge {
  padding: 6px 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text);
  font-size: 0.82rem;
  font-weight: 800;
  white-space: nowrap;
}

.quality-meta-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.quality-meta-grid > div {
  min-width: 0;
}

.quality-meta-grid strong {
  overflow-wrap: anywhere;
}

.quality-recommendations {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 18px;
  color: var(--muted);
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

.analysis-results {
  animation: resultReveal 0.24s ease-out;
  scroll-margin-top: 24px;
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

@keyframes resultReveal {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
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

@media (prefers-reduced-motion: reduce) {
  .analysis-results {
    animation: none;
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
