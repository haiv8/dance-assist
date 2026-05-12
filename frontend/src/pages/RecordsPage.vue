<template>
  <main class="app-page records-page">
    <section class="surface-card page-head records-head">
      <div class="page-head-row">
        <div>
          <h1>分析记录 <InfoHint text="集中查看历史报告、问题片段、练习项目和导出动作。" /></h1>
          <p class="page-subtitle">筛选记录，进入复盘。</p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="loading || issueLoading" @click="refreshWorkspace">
            {{ loading || issueLoading ? "刷新中..." : "刷新记录" }}
          </button>
          <button @click="goToCompare">开始新分析</button>
        </div>
      </div>

      <div class="records-kpi-row">
        <div class="records-kpi-card">
          <span>记录总数</span>
          <strong>{{ records.length }}</strong>
        </div>
        <div class="records-kpi-card">
          <span>进行中</span>
          <strong>{{ runningCount }}</strong>
        </div>
        <div class="records-kpi-card">
          <span>已完成</span>
          <strong>{{ completedCount }}</strong>
        </div>
        <div class="records-kpi-card emphasis">
          <span>问题片段</span>
          <strong>{{ issueItems.length }}</strong>
        </div>
      </div>

    </section>

    <section class="surface-card records-toolbar">
      <div class="records-toolbar-main">
        <div class="tab-row">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="tab-chip secondary-button"
            :class="{ active: activeTab === tab.key }"
            @click="setTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="records-toolbar-grid">
          <div class="field-block">
            <label class="field-label">检索</label>
            <input
              v-model.trim="search"
              type="text"
              :placeholder="activeTab === 'issues' ? '报告名称或问题摘要' : activeTab === 'projects' ? '教师视频或项目名称' : '记录名称或任务 ID'"
            />
          </div>

          <div class="field-block" v-if="activeTab !== 'issues' && activeTab !== 'projects'">
            <label class="field-label">状态</label>
            <select v-model="statusFilter">
              <option value="all">全部状态</option>
              <option value="pending">等待中</option>
              <option value="running">分析中</option>
              <option value="done">已完成</option>
              <option value="failed">失败</option>
              <option value="canceled">已取消</option>
            </select>
          </div>

          <div class="field-block" v-else-if="activeTab === 'issues'">
            <label class="field-label">问题类型</label>
            <select v-model="issueTypeFilter">
              <option value="all">全部类型</option>
              <option value="pose_error">动作误差</option>
              <option value="tempo">节奏异常</option>
              <option value="confidence">可信度风险</option>
              <option value="tracking_bad">跟踪问题</option>
            </select>
          </div>

          <div class="field-block" v-else>
            <label class="field-label">聚合方式</label>
            <div class="counter-value">按教师视频</div>
          </div>

          <div class="field-block compact-counter">
            <label class="field-label">结果数</label>
            <div class="counter-value">{{ activeTab === "issues" ? filteredIssues.length : activeTab === "projects" ? filteredProjects.length : filteredRecords.length }}</div>
          </div>
        </div>
      </div>

      <div class="records-export-strip">
        <div>
          <strong>导出</strong>
          <span class="helper-text">{{ exportCenterHint }}</span>
        </div>
        <div class="export-actions">
          <button class="secondary-button" :disabled="exportingCsv" @click="exportRecordsCsv">
            {{ exportingCsv ? "导出中..." : "记录 CSV" }}
          </button>
          <button class="secondary-button" :disabled="!selectedExportPipelineId || copyingId === selectedExportPipelineId" @click="copySelectedPipelineId">
            {{ copyingId === selectedExportPipelineId ? "已复制" : "复制 pipeline_id" }}
          </button>
          <a
            v-if="selectedReportUrl"
            class="secondary-button link-button"
            :href="selectedReportUrl"
            target="_blank"
            rel="noreferrer"
          >
            report.json
          </a>
          <button v-else class="secondary-button" type="button" disabled>report.json</button>
          <button class="secondary-button" type="button" :disabled="!markdownCommand || copyingMarkdownCommand" @click="copyMarkdownCommand">
            {{ copyingMarkdownCommand ? "已复制" : "Markdown 命令" }}
          </button>
        </div>
        <code v-if="markdownCommand" class="export-command">{{ markdownCommand }}</code>
      </div>
    </section>

    <section class="surface-card records-workspace">
      <div class="records-table-head project-table-head" v-if="activeTab === 'projects'">
        <span>练习项目</span>
        <span>次数</span>
        <span>最近 / 最高</span>
        <span>平均 / 问题</span>
        <span>最近完成</span>
      </div>

      <div class="records-table-head" v-else-if="activeTab !== 'issues'">
        <span></span>
        <span></span>
        <span>记录</span>
        <span>状态</span>
        <span>得分 / 可信度</span>
        <span>更新时间</span>
      </div>

      <div class="records-table-head issue-table-head" v-else>
        <span></span>
        <span>问题片段</span>
        <span>优先级</span>
        <span>时间点</span>
        <span>所属记录</span>
      </div>

      <div v-if="visiblePipelineIds.length" class="bulk-action-bar">
        <label class="bulk-select">
          <input
            type="checkbox"
            :checked="allVisibleSelected"
            :indeterminate.prop="someVisibleSelected && !allVisibleSelected"
            @change="toggleSelectAllVisible"
          />
          <span>{{ selectedVisibleDeletablePipelineIds.length ? `已选 ${selectedVisibleDeletablePipelineIds.length} 条可删除记录` : "多选记录" }}</span>
        </label>
        <div class="action-row">
          <button class="secondary-button" type="button" :disabled="!selectedPipelineIds.size || bulkDeleting" @click="clearSelection">取消选择</button>
          <button class="ghost-button danger-button" type="button" :disabled="!selectedVisibleDeletablePipelineIds.length || bulkDeleting" @click="deleteSelectedPipelines">
            {{ bulkDeleting ? "批量删除中..." : "删除所选" }}
          </button>
        </div>
      </div>

      <div v-if="error || (activeTab === 'projects' && projectError)" class="feedback-inline">{{ error || projectError }}</div>

      <div v-else-if="activeTab === 'issues' && issueLoading" class="feedback-state" data-tone="loading">
        <strong class="feedback-state-title">问题片段整理中</strong>
        <span class="feedback-state-copy">正在生成可回放片段...</span>
      </div>

      <EmptyState
        v-else-if="activeTab === 'issues' && !filteredIssues.length"
        title="暂无可回放问题"
        copy="完成一次分析后会显示问题片段。"
      >
        <template #actions>
          <button class="secondary-button" type="button" @click="goToCompare">去开始分析</button>
        </template>
      </EmptyState>

      <div v-else-if="activeTab === 'projects' && projectLoading" class="feedback-state" data-tone="loading">
        <strong class="feedback-state-title">练习项目整理中</strong>
        <span class="feedback-state-copy">正在聚合趋势和历史练习...</span>
      </div>

      <EmptyState
        v-else-if="activeTab === 'projects' && !filteredProjects.length"
        title="趋势样本不足"
        copy="同一教师示范至少完成两次练习后生成趋势。"
      >
        <template #actions>
          <button class="secondary-button" type="button" @click="goToCompare">继续分析一次</button>
        </template>
      </EmptyState>

      <EmptyState
        v-else-if="activeTab !== 'issues' && !filteredRecords.length"
        :title="records.length ? '筛选无结果' : '还没有分析记录'"
        :copy="records.length ? '切换筛选或清空搜索。' : '开始第一次分析后生成报告和问题片段。'"
      >
        <template #actions>
          <button class="secondary-button" type="button" @click="goToCompare">
            {{ records.length ? "开始新分析" : "开始第一次分析" }}
          </button>
        </template>
      </EmptyState>

      <IssueList
        v-else-if="activeTab === 'issues'"
        :issues="filteredIssues"
        :selected-issue-id="selectedIssueId"
        :selected-pipeline-ids="selectedPipelineIds"
        :bulk-deleting="bulkDeleting"
        :deleting-id="deletingId"
        :can-delete-pipeline-id="canDeletePipelineId"
        @toggle-issue="toggleIssue"
        @toggle-selection="togglePipelineSelection"
        @open-record="openIssueRecord"
        @jump-compare="jumpIssueToCompare"
        @delete-pipeline="deletePipeline"
      />

      <div v-else-if="activeTab === 'projects'" class="project-list">
        <article v-for="project in filteredProjects" :key="project.teacher_video_id" class="project-card">
          <button type="button" class="project-row" :class="{ active: selectedProjectId === project.teacher_video_id }" @click="toggleProject(project.teacher_video_id)">
            <div class="project-main">
              <strong>{{ project.teacher_filename || project.teacher_video_id }}</strong>
              <p class="helper-text">{{ project.analysis_count }} 次练习，展开查看趋势。</p>
            </div>
            <div class="project-metric">
              <span>最近分</span>
              <strong>{{ scoreText(project.latest_score) }}</strong>
            </div>
            <div class="project-metric">
              <span>最高分</span>
              <strong>{{ scoreText(project.best_score) }}</strong>
            </div>
            <div class="project-metric">
              <span>平均 / 问题</span>
              <strong>{{ scoreText(project.avg_score) }} / {{ project.issue_total }}</strong>
            </div>
            <div class="project-metric">
              <span>最近完成</span>
              <strong>{{ formatDate(project.latest_finished_at) }}</strong>
            </div>
          </button>

          <div v-if="selectedProjectId === project.teacher_video_id" class="project-detail">
            <div v-if="projectDetailLoading" class="feedback-state" data-tone="loading">
              <strong class="feedback-state-title">项目详情加载中</strong>
              <span class="feedback-state-copy">正在读取历史记录...</span>
            </div>
            <template v-else-if="projectDetail">
              <PracticeTrendCard :trend="projectDetail.trend" />
              <div class="project-records">
                <button
                  v-for="record in projectDetail.records"
                  :key="record.pipeline_id"
                  type="button"
                  class="project-record-row"
                  @click="openProjectRecord(record.pipeline_id)"
                >
                  <span>{{ record.pair_name || compactPipelineId(record.pipeline_id) }}</span>
                  <strong>{{ scoreText(record.score_total) }}</strong>
                  <small>{{ confidenceText(record.confidence_score) }} / {{ record.issue_count }} 个问题</small>
                  <small>{{ formatDate(record.finished_at || record.updated_at) }}</small>
                </button>
              </div>
            </template>
          </div>
        </article>
      </div>

      <div v-else class="records-list dense-list">
        <div v-for="item in filteredRecords" :key="item.pipeline_id" class="record-shell">
          <div class="record-row-wrap">
            <label class="row-check" :class="{ disabled: !canDeletePipelineId(item.pipeline_id) }" @click.stop>
              <input
                type="checkbox"
                :checked="selectedPipelineIds.has(item.pipeline_id)"
                :disabled="!canDeletePipelineId(item.pipeline_id) || bulkDeleting || deletingId === item.pipeline_id"
                @change="togglePipelineSelection(item.pipeline_id)"
              />
            </label>
            <button
              type="button"
              class="record-star-button"
              :class="{ active: item.starred }"
              :disabled="flagSavingId === item.pipeline_id"
              :title="item.starred ? '取消重点' : '标为重点'"
              @click.stop="toggleRecordStar(item)"
            >
              {{ item.starred ? "★" : "☆" }}
            </button>
            <button
              type="button"
              class="record-row dense-row"
              :class="{ active: selectedRecordId === item.pipeline_id }"
              @click="toggleRecord(item.pipeline_id)"
            >
              <div class="dense-col primary-col">
                <strong>{{ item.pair_name || compactPipelineId(item.pipeline_id) }}</strong>
                <p class="helper-text">{{ recordLead(item) }}</p>
              </div>
              <div class="dense-col">
                <span class="tag" :class="statusTone(item.status)">{{ statusText(item.status) }}</span>
                <span class="helper-text">{{ stageText(item.stage, item.status) }}</span>
              </div>
              <div class="dense-col">
                <strong>{{ scoreText(item.score_total) }}</strong>
                <span class="helper-text">{{ confidenceText(item.confidence_score) }}</span>
              </div>
              <div class="dense-col">
                <strong class="mono-col">{{ formatDate(item.updated_at || item.finished_at || item.started_at || item.queued_at) }}</strong>
                <span class="helper-text">{{ item.status === "failed" ? failedRecordMeta(item) : `执行器：${item.executor || "--"}` }}</span>
              </div>
            </button>
          </div>

          <div v-if="selectedRecordId === item.pipeline_id" ref="detailPanelRef" class="record-detail-slot">
            <RecordDetailPanel
              :item="item"
              :detail="detail"
              :detail-loading="detailLoading"
              :detail-error="detailError"
              :issues="detailIssues"
              :ai-coach="aiCoach"
              :ai-coach-error="aiCoachError"
              :ai-coach-loading="aiCoachLoading"
              :ai-coach-source-text="aiCoachSourceText"
              :ai-coach-fallback-hint="aiCoachFallbackHint"
              :can-cancel="canCancelSelectedRecord"
              :can-delete="canDeleteSelectedRecord"
              :can-open-compare="canOpenSelectedInCompare"
              :copying="copyingId === item.pipeline_id"
              :deleting="deletingId === item.pipeline_id"
              :canceling="cancelingId === item.pipeline_id"
              @cancel="cancelSelectedRecord"
              @delete="deletePipeline(item.pipeline_id)"
              @copy="copyPipelineId(item.pipeline_id)"
              @load-ai="loadDetailAiCoach(item.pipeline_id)"
              @open-compare="openSelectedInCompare"
              @jump-issue="jumpIssueToCompare"
              :note-draft="noteDraft"
              :flag-saving="flagSavingId === item.pipeline_id"
              @toggle-star="toggleRecordStar(item)"
              @save-note="saveRecordNote(item.pipeline_id)"
              @update-note-draft="noteDraft = $event"
            />
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import EmptyState from "../components/EmptyState.vue";
import InfoHint from "../components/InfoHint.vue";
import IssueList from "../components/records/IssueList.vue";
import PracticeTrendCard from "../components/records/PracticeTrendCard.vue";
import RecordDetailPanel from "../components/records/RecordDetailPanel.vue";
import { useRecordsPage } from "../composables/useRecordsPage";

const page = useRecordsPage();
const {
  tabs,
  records,
  loading,
  issueLoading,
  error,
  issueItems,
  aiCoach,
  aiCoachLoading,
  aiCoachError,
  aiCoachSourceText,
  aiCoachFallbackHint,
  copyingId,
  deletingId,
  cancelingId,
  bulkDeleting,
  canDeletePipelineId,
  activeTab,
  search,
  statusFilter,
  issueTypeFilter,
  projects,
  projectLoading,
  projectError,
  selectedProjectId,
  projectDetail,
  projectDetailLoading,
  exportingCsv,
  copyingMarkdownCommand,
  flagSavingId,
  noteDraft,
  selectedRecordId,
  selectedIssueId,
  detail,
  detailLoading,
  detailError,
  detailPanelRef,
  selectedPipelineIds,
  runningCount,
  completedCount,
  filteredProjects,
  filteredRecords,
  filteredIssues,
  visiblePipelineIds,
  visibleDeletablePipelineIds,
  selectedVisibleDeletablePipelineIds,
  allVisibleSelected,
  someVisibleSelected,
  selectedRecord,
  selectedIssue,
  selectedExportRecord,
  selectedExportPipelineId,
  selectedReportUrl,
  markdownCommand,
  exportCenterHint,
  canCancelSelectedRecord,
  canDeleteSelectedRecord,
  canOpenSelectedInCompare,
  detailIssues,
  setSelectedPipelineIds,
  clearSelection,
  togglePipelineSelection,
  toggleSelectAllVisible,
  parseTab,
  routeQueryString,
  setTab,
  goToCompare,
  refreshWorkspace,
  csvExportStatus,
  exportRecordsCsv,
  loadProjects,
  loadWorkspace,
  hydrateSelectionFromRoute,
  openRecord,
  applyRecordFlags,
  toggleRecordStar,
  saveRecordNote,
  closeRecordDetail,
  toggleRecord,
  openProject,
  closeProject,
  toggleProject,
  openProjectRecord,
  openIssue,
  closeIssueDetail,
  toggleIssue,
  copyPipelineId,
  copySelectedPipelineId,
  copyMarkdownCommand,
  loadDetailAiCoach,
  cancelSelectedRecord,
  deletePipeline,
  deleteSelectedPipelines,
  openSelectedInCompare,
  openIssueRecord,
  jumpIssueToCompare,
  recordLead,
  failedRecordMeta,
  statusText,
  statusTone,
  errorTypeText,
  stageText,
  confidenceText,
  scoreText,
  formatDate,
} = page;
</script>

<style scoped>
.records-page,
.records-toolbar,
.records-workspace,
.records-list,
.record-shell {
  display: grid;
  gap: 14px;
}

.records-head {
  gap: 18px;
}

.records-head .page-head-row {
  align-items: start;
}

.records-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.records-kpi-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(255, 255, 255, 0.92);
}

.records-kpi-card span {
  color: var(--muted);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.records-kpi-card strong {
  font-family: var(--font-display);
  font-size: 1.6rem;
  line-height: 1;
}

.records-kpi-card.emphasis {
  background: linear-gradient(180deg, rgba(255, 247, 241, 0.98) 0%, rgba(255, 243, 235, 0.94) 100%);
  border-color: rgba(226, 109, 61, 0.18);
}

.export-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.export-command {
  display: block;
  grid-column: 1 / -1;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(15, 23, 42, 0.05);
  color: var(--text);
  overflow-x: auto;
  white-space: nowrap;
}

.records-toolbar {
  position: sticky;
  top: 12px;
  z-index: 8;
  gap: 12px;
  padding: 14px;
  border-color: rgba(15, 23, 42, 0.1);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(248, 250, 252, 0.92) 100%);
  backdrop-filter: blur(14px);
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
}

.records-toolbar-main,
.records-export-strip {
  display: grid;
  gap: 12px;
}

.records-toolbar-main {
  grid-template-columns: minmax(0, 1.15fr) minmax(420px, 0.85fr);
  align-items: end;
}

.records-export-strip {
  grid-template-columns: minmax(160px, 0.55fr) minmax(0, 1.45fr);
  align-items: center;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(248, 250, 252, 0.76);
}

.records-export-strip > div:first-child {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.records-export-strip strong {
  font-family: var(--font-display);
  font-size: 0.96rem;
}

.tab-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(226, 232, 240, 0.58);
}

.tab-chip {
  min-width: 0;
  min-height: 36px;
  padding: 0 10px;
  border-radius: 8px;
  border-color: transparent;
  background: transparent;
  box-shadow: none;
  font-size: 0.84rem;
}

.tab-chip.active {
  background: #fff;
  color: var(--accent-dark);
  border-color: transparent;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.1);
}

.records-toolbar-grid {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(150px, 0.62fr) 96px;
  gap: 10px;
  align-items: end;
}

.compact-counter {
  min-width: 0;
}

.counter-value {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.95);
  font-weight: 700;
}

.records-workspace {
  gap: 8px;
  padding: 0 0 14px;
  overflow: hidden;
}

.records-table-head {
  display: grid;
  grid-template-columns: 32px 36px minmax(0, 1.7fr) 150px 150px 200px;
  gap: 10px;
  align-items: center;
  min-height: 42px;
  padding: 0 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.88);
  color: var(--muted);
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.issue-table-head {
  grid-template-columns: 36px minmax(0, 1.8fr) 140px 120px 220px;
}

.project-table-head {
  grid-template-columns: minmax(0, 1.8fr) 120px 160px 160px 220px;
}

.bulk-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background:
    radial-gradient(circle at top left, rgba(15, 143, 179, 0.08), transparent 28%),
    rgba(255, 255, 255, 0.82);
}

.bulk-select {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--text);
  font-size: 0.88rem;
  font-weight: 700;
}

.bulk-select input,
.row-check input {
  width: 18px;
  height: 18px;
  min-height: 18px;
  padding: 0;
  accent-color: var(--accent);
}

.dense-list {
  gap: 0;
  padding: 0 10px 10px;
}

.record-row-wrap {
  display: grid;
  grid-template-columns: 32px 36px minmax(0, 1fr);
  gap: 0;
  align-items: stretch;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.row-check {
  display: grid;
  place-items: center;
  min-height: 100%;
  border-radius: 0;
  border: 0;
  border-right: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(248, 250, 252, 0.62);
  cursor: pointer;
}

.row-check:hover:not(.disabled) {
  border-color: rgba(15, 143, 179, 0.28);
  background: rgba(232, 247, 252, 0.72);
}

.row-check.disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.record-star-button {
  display: grid;
  place-items: center;
  min-height: 100%;
  border-radius: 0;
  border: 0;
  border-right: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(248, 250, 252, 0.62);
  color: rgba(100, 116, 139, 0.92);
  box-shadow: none;
  font-size: 1.08rem;
  letter-spacing: 0;
  padding: 0;
}

.record-star-button.active {
  border-color: rgba(226, 109, 61, 0.28);
  background: rgba(255, 247, 237, 0.9);
  color: #d46b2c;
}

.dense-row {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) 150px 150px 200px;
  gap: 10px;
  align-items: center;
  width: 100%;
  min-height: 68px;
  padding: 12px 14px;
  border-radius: 0;
  border: 0;
  background: rgba(255, 255, 255, 0.94);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

.dense-row:hover:not(:disabled) {
  background: rgba(248, 252, 255, 0.98);
  box-shadow: inset 0 0 0 1px rgba(15, 143, 179, 0.12);
}

.dense-row.active {
  box-shadow: inset 4px 0 0 var(--accent);
  background:
    linear-gradient(90deg, rgba(232, 247, 252, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.dense-col {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.primary-col strong,
.dense-name {
  font-size: 1rem;
  line-height: 1.2;
}

.primary-col p,
.dense-col .helper-text {
  margin: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.mono-col {
  font-variant-numeric: tabular-nums;
}

.record-detail-slot {
  margin: 12px 0 16px 68px;
  border-radius: 18px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.1);
}

.danger-button {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.22);
}

.danger-button:hover:not(:disabled) {
  border-color: rgba(180, 35, 24, 0.4);
  background: rgba(180, 35, 24, 0.08);
}

.project-list {
  display: grid;
  gap: 0;
  padding: 0 10px 10px;
}

.project-card {
  display: grid;
  gap: 10px;
}

.project-row {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) 120px 160px 160px 220px;
  gap: 12px;
  align-items: center;
  width: 100%;
  min-height: 70px;
  padding: 12px 14px;
  border-radius: 0;
  border: 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(255, 255, 255, 0.94);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

.project-row:hover:not(:disabled) {
  background: rgba(248, 252, 255, 0.98);
  box-shadow: inset 0 0 0 1px rgba(15, 143, 179, 0.12);
}

.project-row.active {
  box-shadow: inset 4px 0 0 var(--accent);
  background: linear-gradient(90deg, rgba(232, 247, 252, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.project-main,
.project-metric {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.project-main p {
  margin: 0;
}

.project-metric span,
.project-record-row small {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.project-detail {
  display: grid;
  gap: 14px;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid rgba(15, 143, 179, 0.14);
  background: rgba(248, 252, 255, 0.8);
}

.project-records {
  display: grid;
  gap: 8px;
}

.project-record-row {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) 90px 140px 180px;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(255, 255, 255, 0.9);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

@media (max-width: 1180px) {
  .records-kpi-row,
  .records-toolbar-main,
  .records-export-strip,
  .records-toolbar-grid,
  .records-table-head,
  .dense-row,
  .project-row,
  .project-record-row {
    grid-template-columns: 1fr;
  }

  .record-row-wrap {
    grid-template-columns: 32px 38px minmax(0, 1fr);
  }

  .record-detail-slot {
    margin-left: 0;
  }

  .tab-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .bulk-action-bar {
    align-items: stretch;
    flex-direction: column;
  }
}

@media (max-width: 720px) {
  .tab-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .export-actions {
    justify-content: flex-start;
  }
}
</style>
