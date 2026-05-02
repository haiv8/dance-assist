<template>
  <main class="app-page records-page">
    <section class="surface-card page-head records-head">
      <div class="page-head-row">
        <div>
          <h1>分析记录</h1>
          <p class="page-subtitle">把任务、报告和问题片段合并到一处，减少切页，把主要操作收回到记录本身。</p>
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

      <div class="export-center">
        <div>
          <strong>导出中心</strong>
          <p class="helper-text">{{ exportCenterHint }}</p>
        </div>
        <div class="export-actions">
          <button class="secondary-button" :disabled="exportingCsv" @click="exportRecordsCsv">
            {{ exportingCsv ? "导出中..." : "导出记录 CSV" }}
          </button>
          <button class="secondary-button" :disabled="!selectedExportPipelineId || copyingId === selectedExportPipelineId" @click="copySelectedPipelineId">
            {{ copyingId === selectedExportPipelineId ? "已复制" : "复制当前 pipeline_id" }}
          </button>
          <a
            v-if="selectedReportUrl"
            class="secondary-button link-button"
            :href="selectedReportUrl"
            target="_blank"
            rel="noreferrer"
          >
            打开当前 report.json
          </a>
          <button v-else class="secondary-button" type="button" disabled>打开当前 report.json</button>
          <button class="secondary-button" type="button" :disabled="!markdownCommand || copyingMarkdownCommand" @click="copyMarkdownCommand">
            {{ copyingMarkdownCommand ? "已复制命令" : "复制 Markdown 导出命令" }}
          </button>
        </div>
        <code v-if="markdownCommand" class="export-command">{{ markdownCommand }}</code>
      </div>
    </section>

    <section class="surface-card records-toolbar">
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
            :placeholder="activeTab === 'issues' ? '按报告名称或问题摘要搜索' : activeTab === 'projects' ? '按教师视频或项目名称搜索' : '按记录名称或任务 ID 搜索'"
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
        <span class="feedback-state-copy">正在从已完成分析中提取问题标记和可信度风险，请稍候。</span>
      </div>

      <EmptyState
        v-else-if="activeTab === 'issues' && !filteredIssues.length"
        title="当前没有可回放的问题片段"
        copy="当前没有可回放的问题片段，可能是分析未完成或报告没有生成 issues。"
      >
        <template #actions>
          <button class="secondary-button" type="button" @click="goToCompare">去开始分析</button>
        </template>
      </EmptyState>

      <div v-else-if="activeTab === 'projects' && projectLoading" class="feedback-state" data-tone="loading">
        <strong class="feedback-state-title">练习项目整理中</strong>
        <span class="feedback-state-copy">正在按教师视频聚合同一舞蹈片段下的多次分析记录。</span>
      </div>

      <EmptyState
        v-else-if="activeTab === 'projects' && !filteredProjects.length"
        title="至少需要两次分析才能观察趋势"
        copy="围绕同一段教师示范完成两次或更多练习分析后，这里会显示练习项目和进步变化。"
      >
        <template #actions>
          <button class="secondary-button" type="button" @click="goToCompare">继续分析一次</button>
        </template>
      </EmptyState>

      <EmptyState
        v-else-if="activeTab !== 'issues' && !filteredRecords.length"
        :title="records.length ? '当前筛选下没有分析记录' : '还没有分析记录'"
        :copy="records.length ? '可以切换状态筛选，或清空搜索条件。' : '完成一次分析后，这里会显示报告和问题片段。'"
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
              <p class="helper-text">同一教师示范下的练习记录：{{ project.analysis_count }} 次</p>
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
              <span class="feedback-state-copy">正在读取该教师视频下的历史练习记录。</span>
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

          <div v-if="selectedRecordId === item.pipeline_id" ref="detailPanelRef">
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
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { absMediaUrl } from "../api/http";
import { deletePipelineTask, getPipelineResultSummary } from "../api/pipelines";
import { downloadRecordsCsv, getPracticeProject, getPracticeProjects, updateRecordFlags } from "../api/records";
import EmptyState from "../components/EmptyState.vue";
import IssueList from "../components/records/IssueList.vue";
import PracticeTrendCard from "../components/records/PracticeTrendCard.vue";
import RecordDetailPanel from "../components/records/RecordDetailPanel.vue";
import { useAiCoach } from "../composables/useAiCoach";
import { isRunningTaskStatus, useRecordActions } from "../composables/useRecordActions";
import { mapIssueItems, useRecordsWorkspace } from "../composables/useRecordsWorkspace";
import { normalizedConfidenceSummary } from "../utils/confidence";
import { focusDetailPanel } from "../utils/detailPanel";
import { compactPipelineId } from "../utils/display";
import { friendlyError } from "../utils/errors";
import type {
  IssueReplayItem,
  PipelineResultSummaryResponse,
  PipelineStatusType,
  PracticeProjectDetailResponse,
  PracticeProjectItem,
  RecordWorkspaceItem,
} from "../types/video";

type WorkspaceTab = "all" | "starred" | "running" | "completed" | "projects" | "issues";
type RecordItem = RecordWorkspaceItem;

const router = useRouter();
const route = useRoute();

const tabs: Array<{ key: WorkspaceTab; label: string }> = [
  { key: "all", label: "全部记录" },
  { key: "starred", label: "重点记录" },
  { key: "running", label: "进行中" },
  { key: "completed", label: "已完成" },
  { key: "projects", label: "练习项目" },
  { key: "issues", label: "问题片段" },
];

const {
  records,
  loading,
  issueLoading,
  error,
  issueItems,
  loadWorkspace: loadRecordsWorkspace,
  removePipeline,
} = useRecordsWorkspace();
const activeTab = ref<WorkspaceTab>("all");
const search = ref("");
const statusFilter = ref<PipelineStatusType | "all">("all");
const issueTypeFilter = ref("all");
const projects = ref<PracticeProjectItem[]>([]);
const projectLoading = ref(false);
const projectError = ref("");
const selectedProjectId = ref("");
const projectDetail = ref<PracticeProjectDetailResponse | null>(null);
const projectDetailLoading = ref(false);
const exportingCsv = ref(false);
const copyingMarkdownCommand = ref(false);
const flagSavingId = ref("");
const noteDraft = ref("");

const selectedRecordId = ref("");
const selectedIssueId = ref("");
const detail = ref<PipelineResultSummaryResponse | null>(null);
const detailLoading = ref(false);
const detailError = ref("");
const detailPanelRef = ref<HTMLElement | null>(null);

const {
  aiCoach,
  aiCoachLoading,
  aiCoachError,
  aiCoachSourceText,
  aiCoachFallbackHint,
  clearAiCoach,
  loadAiCoach,
} = useAiCoach();
const {
  copyingId,
  deletingId,
  cancelingId,
  bulkDeleting,
  actionError,
  canDeletePipelineId,
  copyPipelineId: copyRecordPipelineId,
  cancelPipelineRecord,
  deletePipelineRecord,
} = useRecordActions(records);
const selectedPipelineIds = ref<Set<string>>(new Set());

const runningCount = computed(() => records.value.filter((item) => item.status === "pending" || item.status === "running").length);
const completedCount = computed(() => records.value.filter((item) => item.status === "done").length);

const filteredProjects = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return projects.value.filter((item) => {
    const text = `${item.teacher_filename || ""} ${item.teacher_video_id || ""} ${item.latest_pipeline_id || ""}`.toLowerCase();
    return !keyword || text.includes(keyword);
  });
});

const filteredRecords = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return records.value.filter((item) => {
    const text = `${item.pair_name || ""} ${item.pipeline_id}`.toLowerCase();
    const matchesKeyword = !keyword || text.includes(keyword);

    if (activeTab.value === "starred" && !item.starred) return false;
    if (activeTab.value === "running" && item.status !== "pending" && item.status !== "running") return false;
    if (activeTab.value === "completed" && item.status !== "done") return false;
    if (statusFilter.value !== "all" && item.status !== statusFilter.value) return false;

    return matchesKeyword;
  });
});

const filteredIssues = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return issueItems.value.filter((item) => {
    const matchesKeyword =
      !keyword ||
      item.pairName.toLowerCase().includes(keyword) ||
      item.summary.toLowerCase().includes(keyword);
    const matchesType = issueTypeFilter.value === "all" || item.type === issueTypeFilter.value;
    return matchesKeyword && matchesType;
  });
});

const visiblePipelineIds = computed(() => {
  if (activeTab.value === "projects") return [];
  const ids = activeTab.value === "issues"
    ? filteredIssues.value.map((item) => item.pipelineId)
    : filteredRecords.value.map((item) => item.pipeline_id);
  return Array.from(new Set(ids));
});

const visibleDeletablePipelineIds = computed(() => visiblePipelineIds.value.filter((pipelineId) => canDeletePipelineId(pipelineId)));
const selectedVisibleDeletablePipelineIds = computed(() =>
  visibleDeletablePipelineIds.value.filter((pipelineId) => selectedPipelineIds.value.has(pipelineId)),
);
const allVisibleSelected = computed(() =>
  Boolean(visibleDeletablePipelineIds.value.length && visibleDeletablePipelineIds.value.every((pipelineId) => selectedPipelineIds.value.has(pipelineId))),
);
const someVisibleSelected = computed(() =>
  visibleDeletablePipelineIds.value.some((pipelineId) => selectedPipelineIds.value.has(pipelineId)),
);

const selectedRecord = computed(() => records.value.find((item) => item.pipeline_id === selectedRecordId.value) ?? null);
const selectedIssue = computed(() => filteredIssues.value.find((item) => item.id === selectedIssueId.value) ?? null);
const selectedExportRecord = computed(() => detail.value ?? selectedRecord.value);
const selectedExportPipelineId = computed(() => selectedExportRecord.value?.pipeline_id || selectedRecordId.value || "");
const selectedReportUrl = computed(() => {
  const reportUrl = selectedExportRecord.value?.files?.report_url;
  return reportUrl ? absMediaUrl(reportUrl) : "";
});
const markdownCommand = computed(() => {
  const record = selectedExportRecord.value;
  if (!record || record.status !== "done" || !selectedExportPipelineId.value) return "";
  return `python scripts/export-analysis-report-md.py --pipeline-id ${selectedExportPipelineId.value}`;
});
const exportCenterHint = computed(() => {
  const record = selectedExportRecord.value;
  if (!record) return "可先导出当前记录列表；如需导出单条 Markdown，请先选择一条已完成记录。";
  if (record.status !== "done") return "当前记录还未完成，Markdown 导出命令会在分析完成后可用。";
  return "当前已选择完成记录，可复制任务 ID、打开 report.json，或复制 Markdown 导出命令。";
});
const canCancelSelectedRecord = computed(() => {
  const item = detail.value ?? selectedRecord.value;
  return Boolean(item && isRunningTaskStatus(item.status) && !item.cancel_requested);
});
const canDeleteSelectedRecord = computed(() => {
  const item = detail.value ?? selectedRecord.value;
  return Boolean(item && item.status !== "pending" && item.status !== "running");
});
const canOpenSelectedInCompare = computed(() => Boolean(selectedRecord.value?.teacher_video_id && selectedRecord.value?.user_video_id));
const detailIssues = computed<IssueReplayItem[]>(() => (Array.isArray(detail.value?.issues) ? mapIssueItems(detail.value?.issues || []) : []));

function setSelectedPipelineIds(nextIds: Iterable<string>) {
  selectedPipelineIds.value = new Set(nextIds);
}

function clearSelection() {
  setSelectedPipelineIds([]);
}

function togglePipelineSelection(pipelineId: string) {
  if (!canDeletePipelineId(pipelineId) || bulkDeleting.value) return;
  const next = new Set(selectedPipelineIds.value);
  if (next.has(pipelineId)) {
    next.delete(pipelineId);
  } else {
    next.add(pipelineId);
  }
  setSelectedPipelineIds(next);
}

function toggleSelectAllVisible() {
  const next = new Set(selectedPipelineIds.value);
  if (allVisibleSelected.value) {
    for (const pipelineId of visibleDeletablePipelineIds.value) next.delete(pipelineId);
  } else {
    for (const pipelineId of visibleDeletablePipelineIds.value) next.add(pipelineId);
  }
  setSelectedPipelineIds(next);
}

function parseTab(value: unknown): WorkspaceTab {
  if (value === "starred" || value === "running" || value === "completed" || value === "projects" || value === "issues" || value === "all") return value;
  return "all";
}

function routeQueryString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function setTab(tab: WorkspaceTab) {
  activeTab.value = tab;
  const nextQuery = { ...route.query, tab };
  void router.replace({ path: "/records", query: nextQuery });
}

function goToCompare() {
  void router.push("/compare");
}

async function refreshWorkspace() {
  await loadWorkspace();
}

function csvExportStatus(): "done" | "failed" | "running" | undefined {
  if (statusFilter.value === "done" || statusFilter.value === "failed" || statusFilter.value === "running") {
    return statusFilter.value;
  }
  if (activeTab.value === "completed") return "done";
  if (activeTab.value === "running") return "running";
  return undefined;
}

async function exportRecordsCsv() {
  if (exportingCsv.value) return;
  exportingCsv.value = true;
  error.value = "";
  try {
    const blob = await downloadRecordsCsv({
      limit: 200,
      starred: activeTab.value === "starred" ? true : undefined,
      status: csvExportStatus(),
    });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    anchor.href = url;
    anchor.download = `dance_assist_records_${date}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  } catch (err: any) {
    error.value = friendlyError(err, "CSV 导出失败");
  } finally {
    exportingCsv.value = false;
  }
}

async function loadProjects() {
  projectLoading.value = true;
  projectError.value = "";
  try {
    const data = await getPracticeProjects(200);
    projects.value = data.items;
  } catch (err: any) {
    projectError.value = friendlyError(err, "练习项目加载失败");
  } finally {
    projectLoading.value = false;
  }
}

async function loadWorkspace() {
  await loadRecordsWorkspace(100);
  await loadProjects();
  if (!error.value) {
    await hydrateSelectionFromRoute();
  }
}

async function hydrateSelectionFromRoute() {
  const tab = parseTab(route.query.tab);
  activeTab.value = tab;

  const pipelineId = routeQueryString(route.query.pipeline);
  const sec = Number(routeQueryString(route.query.sec));
  const projectId = routeQueryString(route.query.project);

  if (tab === "issues") {
    if (pipelineId) {
      const hit = filteredIssues.value.find((item) => item.pipelineId === pipelineId && (!Number.isFinite(sec) || Math.abs(item.sec - sec) < 0.11));
      if (hit) {
        await openIssue(hit.id);
      }
    }
    return;
  }

  if (tab === "projects") {
    if (projectId && projects.value.some((item) => item.teacher_video_id === projectId)) {
      await openProject(projectId);
    }
    return;
  }

  if (pipelineId && records.value.some((item) => item.pipeline_id === pipelineId)) {
    await openRecord(pipelineId);
  }
}

async function openRecord(pipelineId: string) {
  selectedRecordId.value = pipelineId;
  selectedIssueId.value = "";
  noteDraft.value = records.value.find((item) => item.pipeline_id === pipelineId)?.user_note || "";
  detailLoading.value = true;
  detailError.value = "";
  clearAiCoach();
  try {
    detail.value = await getPipelineResultSummary(pipelineId);
    focusDetailPanel(detailPanelRef, { forceScroll: true });
  } catch (err: any) {
    detail.value = null;
    detailError.value = friendlyError(err, "记录详情加载失败");
  } finally {
    detailLoading.value = false;
  }
}

function applyRecordFlags(pipelineId: string, flags: { starred?: boolean; note?: string; updated_at?: string | null }) {
  records.value = records.value.map((item) => (
    item.pipeline_id === pipelineId
      ? {
          ...item,
          starred: Boolean(flags.starred),
          user_note: flags.note || "",
          flag_updated_at: flags.updated_at || item.flag_updated_at || null,
        }
      : item
  ));
}

async function toggleRecordStar(item: RecordItem) {
  if (!item?.pipeline_id || flagSavingId.value) return;
  flagSavingId.value = item.pipeline_id;
  error.value = "";
  detailError.value = "";
  try {
    const next = await updateRecordFlags(item.pipeline_id, {
      starred: !item.starred,
      note: item.user_note || "",
    });
    applyRecordFlags(item.pipeline_id, next);
    if (selectedRecordId.value === item.pipeline_id) {
      noteDraft.value = next.note || "";
    }
  } catch (err: any) {
    const message = friendlyError(err, "重点标记保存失败");
    error.value = message;
    if (selectedRecordId.value === item.pipeline_id) detailError.value = message;
  } finally {
    flagSavingId.value = "";
  }
}

async function saveRecordNote(pipelineId: string) {
  if (!pipelineId || flagSavingId.value) return;
  const item = records.value.find((record) => record.pipeline_id === pipelineId);
  flagSavingId.value = pipelineId;
  error.value = "";
  detailError.value = "";
  try {
    const next = await updateRecordFlags(pipelineId, {
      starred: Boolean(item?.starred),
      note: noteDraft.value,
    });
    applyRecordFlags(pipelineId, next);
    noteDraft.value = next.note || "";
  } catch (err: any) {
    const message = friendlyError(err, "复盘备注保存失败");
    error.value = message;
    detailError.value = message;
  } finally {
    flagSavingId.value = "";
  }
}

function closeRecordDetail() {
  selectedRecordId.value = "";
  detail.value = null;
  detailError.value = "";
  noteDraft.value = "";
  clearAiCoach();
}

async function toggleRecord(pipelineId: string) {
  if (pipelineId === selectedRecordId.value && detail.value) {
    closeRecordDetail();
    return;
  }
  await openRecord(pipelineId);
}

async function openProject(projectId: string) {
  selectedProjectId.value = projectId;
  selectedRecordId.value = "";
  selectedIssueId.value = "";
  projectDetailLoading.value = true;
  projectError.value = "";
  try {
    projectDetail.value = await getPracticeProject(projectId, 200);
  } catch (err: any) {
    projectDetail.value = null;
    projectError.value = friendlyError(err, "练习项目详情加载失败");
  } finally {
    projectDetailLoading.value = false;
  }
}

function closeProject() {
  selectedProjectId.value = "";
  projectDetail.value = null;
}

async function toggleProject(projectId: string) {
  if (projectId === selectedProjectId.value && projectDetail.value) {
    closeProject();
    return;
  }
  void router.replace({ path: "/records", query: { ...route.query, tab: "projects", project: projectId } });
  await openProject(projectId);
}

function openProjectRecord(pipelineId?: string | null) {
  if (!pipelineId) return;
  statusFilter.value = "all";
  void router.replace({ path: "/records", query: { pipeline: pipelineId, tab: "completed" } });
  activeTab.value = "completed";
  void openRecord(pipelineId);
}

async function openIssue(issueId: string) {
  selectedIssueId.value = issueId;
  selectedRecordId.value = "";
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

async function copyPipelineId(pipelineId: string) {
  await copyRecordPipelineId(pipelineId);
  if (actionError.value) detailError.value = actionError.value;
}

async function copySelectedPipelineId() {
  if (!selectedExportPipelineId.value) return;
  await copyPipelineId(selectedExportPipelineId.value);
}

async function copyMarkdownCommand() {
  if (!markdownCommand.value) return;
  copyingMarkdownCommand.value = true;
  detailError.value = "";
  error.value = "";
  try {
    await navigator.clipboard.writeText(markdownCommand.value);
    window.setTimeout(() => {
      copyingMarkdownCommand.value = false;
    }, 1000);
  } catch (err: any) {
    copyingMarkdownCommand.value = false;
    error.value = friendlyError(err, "Markdown 导出命令复制失败");
  }
}

async function loadDetailAiCoach(pipelineId: string) {
  await loadAiCoach(pipelineId);
}

async function cancelSelectedRecord() {
  const pipelineId = selectedRecordId.value;
  if (!pipelineId || !canCancelSelectedRecord.value) return;

  detailError.value = "";
  const status = await cancelPipelineRecord(pipelineId);
  if (!status) {
    detailError.value = actionError.value;
    return;
  }
  records.value = records.value.map((item) => (item.pipeline_id === pipelineId ? { ...item, ...status } : item));
  detail.value = detail.value ? { ...detail.value, ...status } : detail.value;
}

async function deletePipeline(pipelineId: string) {
  const record = records.value.find((item) => item.pipeline_id === pipelineId);
  const label = record?.pair_name || pipelineId;
  const confirmed = window.confirm(`确认删除“${label}”吗？相关任务、报告和问题片段会一起移除。`);
  if (!confirmed) return;

  const ok = await deletePipelineRecord(pipelineId);
  if (!ok) {
    error.value = actionError.value;
    detailError.value = actionError.value;
    return;
  }
  removePipeline(pipelineId);
  void loadProjects();
  const nextSelection = new Set(selectedPipelineIds.value);
  nextSelection.delete(pipelineId);
  setSelectedPipelineIds(nextSelection);
  if (selectedRecordId.value === pipelineId) closeRecordDetail();
  if (selectedIssue.value?.pipelineId === pipelineId) closeIssueDetail();
}

async function deleteSelectedPipelines() {
  const pipelineIds = selectedVisibleDeletablePipelineIds.value;
  if (!pipelineIds.length || bulkDeleting.value) return;

  const confirmed = window.confirm(`确认删除选中的 ${pipelineIds.length} 条记录吗？相关任务、报告和问题片段会一起移除。`);
  if (!confirmed) return;

  bulkDeleting.value = true;
  error.value = "";
  const failed: string[] = [];
  try {
    for (const pipelineId of pipelineIds) {
      deletingId.value = pipelineId;
      try {
        await deletePipelineTask(pipelineId);
        removePipeline(pipelineId);
        if (selectedRecordId.value === pipelineId) closeRecordDetail();
        if (selectedIssue.value?.pipelineId === pipelineId) closeIssueDetail();
      } catch (err: any) {
        failed.push(friendlyError(err, `删除 ${pipelineId} 失败`));
      }
    }
  } finally {
    deletingId.value = "";
    bulkDeleting.value = false;
    const remaining = new Set(selectedPipelineIds.value);
    for (const pipelineId of pipelineIds) {
      if (!failed.length || !records.value.some((item) => item.pipeline_id === pipelineId)) {
        remaining.delete(pipelineId);
      }
    }
    setSelectedPipelineIds(remaining);
  }

  if (failed.length) {
    error.value = `有 ${failed.length} 条记录删除失败：${failed[0]}`;
  }
  void loadProjects();
}

function openSelectedInCompare() {
  const record = selectedRecord.value;
  if (!record?.teacher_video_id || !record?.user_video_id) return;
  void router.push({
    path: "/compare",
    query: {
      pipeline: record.pipeline_id,
      teacher: record.teacher_video_id,
      user: record.user_video_id,
    },
  });
}

function openIssueRecord(issue: IssueReplayItem) {
  void router.replace({ path: "/records", query: { pipeline: issue.pipelineId, tab: "completed" } });
  activeTab.value = "completed";
  void openRecord(issue.pipelineId);
}

function jumpIssueToCompare(issue: IssueReplayItem) {
  if (!issue.teacherVideoId || !issue.userVideoId) return;
  void router.push({
    path: "/compare",
    query: {
      pipeline: issue.pipelineId,
      teacher: issue.teacherVideoId,
      user: issue.userVideoId,
      sec: String(issue.sec),
      mode: "local",
    },
  });
}

function recordLead(item: Partial<RecordItem>) {
  if (isRunningTaskStatus(item.status)) {
    return item.message || `${stageText(item.stage, item.status)}，这条记录仍在处理中。`;
  }
  if (item.status === "failed") {
    return item.error_message || item.message || "本条分析未成功完成，请先查看异常信息或尝试重新处理。";
  }
  return (
    item.overall_advice ||
    item.beginner_summary ||
    item.teaching_summary ||
    normalizedConfidenceSummary(null, item.confidence_summary) ||
    "本条记录已完成，可展开查看摘要、输出文件和问题片段。"
  );
}

function failedRecordMeta(item: Partial<RecordItem>) {
  const message = item.error_message || item.message || errorTypeText(item.error_type);
  return `失败：${message || "请查看详情"}`;
}

function statusText(status?: string | null) {
  if (status === "pending") return "等待中";
  if (status === "running") return "分析中";
  if (status === "done") return "已完成";
  if (status === "failed") return "失败";
  if (status === "canceled") return "已取消";
  return status || "未知";
}

function statusTone(status?: string | null) {
  if (status === "done") return "ok";
  if (status === "failed") return "danger";
  if (status === "canceled") return "neutral";
  if (status === "pending" || status === "running") return "warn";
  return "neutral";
}

function errorTypeText(value?: string | null) {
  const map: Record<string, string> = {
    video_missing: "视频文件不存在",
    video_unreadable: "视频无法读取",
    ffmpeg_missing: "缺少 ffmpeg",
    pose_cache_missing: "姿态缓存缺失",
    model_missing: "模型缺失",
    low_quality_input: "输入质量不足",
    pipeline_internal_error: "内部异常",
    canceled: "用户取消",
    timeout: "任务超时",
  };
  return value ? map[value] || value : "未知原因";
}

function stageText(stage?: string | null, status?: string | null) {
  if (stage === "queued") return "已进入队列";
  if (stage === "preparing_inputs") return "准备素材";
  if (stage === "extracting_pose") return "提取骨架";
  if (stage === "aligning_motion") return "动作对齐与评分";
  if (stage === "rendering_outputs") return "生成对比输出";
  if (stage === "packaging_results") return "整理结果";
  if (stage === "completed") return "结果已就绪";
  if (stage === "failed") return "任务失败";
  if (stage === "canceled") return "任务已取消";
  return statusText(status);
}

function confidenceText(value?: number | string | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return `${Math.round(num * 100)}%`;
}

function scoreText(value?: number | string | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return num.toFixed(1);
}

function formatDate(value?: string | null) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

watch(
  () => route.query.tab,
  (value) => {
    const nextTab = parseTab(value);
    activeTab.value = nextTab;
  },
);

watch(
  () => [route.query.pipeline, route.query.sec, route.query.tab, route.query.project],
  async () => {
    if (!records.value.length) return;
    await hydrateSelectionFromRoute();
  },
);

onMounted(async () => {
  activeTab.value = parseTab(route.query.tab);
  await loadWorkspace();
});
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

.export-center {
  display: grid;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background:
    radial-gradient(circle at top right, rgba(15, 143, 179, 0.1), transparent 28%),
    rgba(255, 255, 255, 0.82);
}

.export-center > div:first-child {
  display: grid;
  gap: 4px;
}

.export-center strong {
  font-family: var(--font-display);
  font-size: 1.05rem;
}

.export-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.export-command {
  display: block;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(15, 23, 42, 0.05);
  color: var(--text);
  overflow-x: auto;
  white-space: nowrap;
}

.records-toolbar {
  gap: 16px;
}

.tab-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tab-chip {
  min-width: 100px;
}

.tab-chip.active {
  background: linear-gradient(135deg, var(--accent) 0%, #eb8d56 100%);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 8px 18px rgba(226, 109, 61, 0.18);
}

.records-toolbar-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(180px, 0.8fr) 120px;
  gap: 12px;
  align-items: end;
}

.compact-counter {
  min-width: 0;
}

.counter-value {
  display: flex;
  align-items: center;
  min-height: 48px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.95);
  font-weight: 700;
}

.records-workspace {
  gap: 10px;
}

.records-table-head {
  display: grid;
  grid-template-columns: 36px minmax(0, 1.7fr) 160px 180px 220px;
  gap: 12px;
  padding: 0 14px 8px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  color: var(--muted);
  font-size: 0.78rem;
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
  gap: 10px;
}

.record-row-wrap {
  display: grid;
  grid-template-columns: 36px 42px minmax(0, 1fr);
  gap: 10px;
  align-items: stretch;
}

.row-check {
  display: grid;
  place-items: center;
  min-height: 100%;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.76);
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
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.76);
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
  grid-template-columns: minmax(0, 1.7fr) 160px 180px 220px;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.98);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

.dense-row:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(15, 143, 179, 0.22);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.04);
}

.dense-row.active {
  border-color: rgba(15, 143, 179, 0.32);
  background:
    radial-gradient(circle at top right, rgba(15, 143, 179, 0.1), transparent 32%),
    linear-gradient(180deg, rgba(248, 252, 255, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.dense-col {
  display: grid;
  gap: 4px;
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
  gap: 10px;
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
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.98);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

.project-row:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(15, 143, 179, 0.22);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.04);
}

.project-row.active {
  border-color: rgba(15, 143, 179, 0.32);
  background:
    radial-gradient(circle at top right, rgba(15, 143, 179, 0.1), transparent 32%),
    linear-gradient(180deg, rgba(248, 252, 255, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
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

  .bulk-action-bar {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
