import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { absMediaUrl } from "../api/http";
import { deletePipelineTask, getPipelineResultSummary } from "../api/pipelines";
import { downloadRecordsCsv, getPracticeProject, getPracticeProjects, updateRecordFlags } from "../api/records";
import { useAiCoach } from "../composables/useAiCoach";
import { isRunningTaskStatus, useRecordActions } from "../composables/useRecordActions";
import { mapIssueItems, useRecordsWorkspace } from "../composables/useRecordsWorkspace";
import {
  pipelineStageText,
  pipelineStatusText,
  pipelineStatusTone,
} from "../services/pipelineStatus";
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

export function useRecordsPage() {
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
    if (!record) return "先选择一条已完成记录，或直接导出列表。";
    if (record.status !== "done") return "记录未完成，结束后开放 Markdown 导出。";
    return "可复制 ID、打开 JSON 或生成论文整理命令。";
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
      return item.message || `${stageText(item.stage, item.status)}，可等待或取消。`;
    }
    if (item.status === "failed") {
      return item.error_message || item.message || "分析失败，查看异常后重试。";
    }
    return (
      item.overall_advice ||
      item.beginner_summary ||
      item.teaching_summary ||
      normalizedConfidenceSummary(null, item.confidence_summary) ||
      "展开详情查看摘要、文件和问题片段。"
    );
  }

  function failedRecordMeta(item: Partial<RecordItem>) {
    const message = item.error_message || item.message || errorTypeText(item.error_type);
    return `失败：${message || "请查看详情"}`;
  }

  function statusText(status?: string | null) {
    return pipelineStatusText(status);
  }

  function statusTone(status?: string | null) {
    return pipelineStatusTone(status);
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
    return pipelineStageText(stage, status);
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

  return {
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
  };
}
