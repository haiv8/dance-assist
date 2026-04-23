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
            :placeholder="activeTab === 'issues' ? '按报告名称或问题摘要搜索' : '按记录名称或任务 ID 搜索'"
          />
        </div>

        <div class="field-block" v-if="activeTab !== 'issues'">
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

        <div class="field-block" v-else>
          <label class="field-label">问题类型</label>
          <select v-model="issueTypeFilter">
            <option value="all">全部类型</option>
            <option value="pose_error">动作误差</option>
            <option value="tempo">节奏异常</option>
            <option value="confidence">可信度风险</option>
            <option value="tracking_bad">跟踪问题</option>
          </select>
        </div>

        <div class="field-block compact-counter">
          <label class="field-label">结果数</label>
          <div class="counter-value">{{ activeTab === "issues" ? filteredIssues.length : filteredRecords.length }}</div>
        </div>
      </div>
    </section>

    <section class="surface-card records-workspace">
      <div class="records-table-head" v-if="activeTab !== 'issues'">
        <span>记录</span>
        <span>状态</span>
        <span>得分 / 可信度</span>
        <span>更新时间</span>
      </div>

      <div class="records-table-head issue-table-head" v-else>
        <span>问题片段</span>
        <span>优先级</span>
        <span>时间点</span>
        <span>所属记录</span>
      </div>

      <div v-if="error" class="feedback-inline">{{ error }}</div>

      <div v-else-if="activeTab === 'issues' && issueLoading" class="feedback-state" data-tone="loading">
        <strong class="feedback-state-title">问题片段整理中</strong>
        <span class="feedback-state-copy">正在从已完成分析中提取问题标记和可信度风险，请稍候。</span>
      </div>

      <div v-else-if="activeTab === 'issues' && !filteredIssues.length" class="feedback-state" data-tone="empty">
        <strong class="feedback-state-title">当前筛选下没有问题片段</strong>
        <span class="feedback-state-copy">可以放宽筛选条件，或先回到开始分析页生成新的结果。</span>
      </div>

      <div v-else-if="activeTab !== 'issues' && !filteredRecords.length" class="feedback-state" data-tone="empty">
        <strong class="feedback-state-title">当前筛选下没有分析记录</strong>
        <span class="feedback-state-copy">可以切换状态筛选，或发起一轮新的动作分析。</span>
      </div>

      <div v-else-if="activeTab === 'issues'" class="records-list dense-list">
        <div v-for="item in filteredIssues" :key="item.id" class="record-shell">
          <button
            type="button"
            class="record-row dense-row issue-dense-row"
            :class="{ active: selectedIssueId === item.id }"
            @click="toggleIssue(item.id)"
          >
            <div class="dense-col primary-col">
              <strong>{{ issueTypeText(item.type) }}</strong>
              <p class="helper-text">{{ item.summary }}</p>
            </div>
            <div class="dense-col">
              <span class="tag" :class="severityTone(item.severity)">{{ severityText(item.severity) }}</span>
            </div>
            <div class="dense-col mono-col">{{ timeText(item.sec) }}</div>
            <div class="dense-col">
              <strong class="dense-name">{{ item.pairName }}</strong>
              <span class="helper-text">{{ formatDate(item.finishedAt) }}</span>
            </div>
          </button>

          <div
            v-if="selectedIssueId === item.id"
            ref="detailPanelRef"
            class="inline-detail"
          >
            <div class="panel-head compact-head">
              <div>
                <h2>问题回放</h2>
                <p class="helper-text">这里保留最短路径操作，方便你马上回到所属记录或动作分析页。</p>
              </div>
              <div class="action-row">
                <button class="secondary-button" type="button" @click="openIssueRecord(item)">打开所属记录</button>
                <button class="secondary-button" type="button" @click="jumpIssueToCompare(item)">定位到动作分析</button>
                <button class="ghost-button danger-button" type="button" :disabled="deletingId === item.pipelineId" @click="deletePipeline(item.pipelineId)">
                  {{ deletingId === item.pipelineId ? "删除中..." : "删除记录" }}
                </button>
              </div>
            </div>

            <div class="metric-row compact-stats">
              <div class="metric-chip"><strong>问题类型</strong><span>{{ issueTypeText(item.type) }}</span></div>
              <div class="metric-chip"><strong>定位时间</strong><span>{{ timeText(item.sec) }}</span></div>
              <div class="metric-chip"><strong>优先级</strong><span>{{ severityText(item.severity) }}</span></div>
            </div>

            <div class="list-item-card">
              <strong>问题摘要</strong>
              <span class="helper-text">{{ item.summary }}</span>
            </div>

            <div class="list-item-card" v-if="item.action">
              <strong>处理建议</strong>
              <span class="helper-text">{{ item.action }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="records-list dense-list">
        <div v-for="item in filteredRecords" :key="item.pipeline_id" class="record-shell">
          <button
            type="button"
            class="record-row dense-row"
            :class="{ active: selectedRecordId === item.pipeline_id }"
            @click="toggleRecord(item.pipeline_id)"
          >
            <div class="dense-col primary-col">
              <strong>{{ item.pair_name || item.pipeline_id }}</strong>
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
              <span class="helper-text">{{ item.error_type ? `异常：${item.error_type}` : `执行器：${item.executor || "--"}` }}</span>
            </div>
          </button>

          <div
            v-if="selectedRecordId === item.pipeline_id"
            ref="detailPanelRef"
            class="inline-detail"
          >
            <div class="panel-head compact-head">
              <div>
                <h2>记录详情</h2>
                <p class="helper-text">主要动作集中在这里，避免为同一条记录切换多个菜单。</p>
              </div>
              <div class="action-row">
                <button class="ghost-button" :disabled="!canCancelSelectedRecord || cancelingId === item.pipeline_id" @click="cancelSelectedRecord">
                  {{ cancelingId === item.pipeline_id ? "取消中..." : "取消任务" }}
                </button>
                <button class="ghost-button danger-button" :disabled="!canDeleteSelectedRecord || deletingId === item.pipeline_id" @click="deletePipeline(item.pipeline_id)">
                  {{ deletingId === item.pipeline_id ? "删除中..." : "删除记录" }}
                </button>
                <button class="secondary-button" :disabled="copyingId === item.pipeline_id" @click="copyPipelineId(item.pipeline_id)">
                  {{ copyingId === item.pipeline_id ? "已复制" : "复制任务 ID" }}
                </button>
                <button class="secondary-button" :disabled="!canOpenSelectedInCompare" @click="openSelectedInCompare">打开动作分析</button>
              </div>
            </div>

            <div v-if="detailLoading" class="feedback-state" data-tone="loading">
              <strong class="feedback-state-title">详情加载中</strong>
              <span class="feedback-state-copy">正在读取本条记录的摘要、输出文件和问题片段。</span>
            </div>

            <div v-else-if="detailError" class="feedback-state" data-tone="error">
              <strong class="feedback-state-title">详情加载失败</strong>
              <span class="feedback-state-copy">{{ detailError }}</span>
            </div>

            <div v-else-if="detail" class="detail-stack">
              <div class="metric-row compact-stats">
                <div class="metric-chip"><strong>状态</strong><span>{{ statusText(detail.status) }}</span></div>
                <div class="metric-chip"><strong>阶段</strong><span>{{ stageText(detail.stage, detail.status) }}</span></div>
                <div class="metric-chip"><strong>进度</strong><span>{{ progressPercent(detail.progress) }}%</span></div>
              </div>

              <div class="metric-row compact-stats">
                <div class="metric-chip"><strong>总分</strong><span>{{ scoreText(detail.report?.score_0_100 ?? detail.report?.scores?.score_total ?? detail.score_total) }}</span></div>
                <div class="metric-chip"><strong>动作</strong><span>{{ scoreText(detail.report?.scores?.score_pose ?? detail.score_pose) }}</span></div>
                <div class="metric-chip"><strong>节奏</strong><span>{{ scoreText(detail.report?.scores?.score_tempo ?? detail.score_tempo) }}</span></div>
              </div>

              <div class="metric-row compact-stats">
                <div class="metric-chip"><strong>可信度</strong><span>{{ detailConfidenceText }}</span></div>
                <div class="metric-chip"><strong>开始时间</strong><span>{{ formatDate(detail.started_at || detail.queued_at) }}</span></div>
                <div class="metric-chip"><strong>完成时间</strong><span>{{ formatDate(detail.finished_at || detail.updated_at) }}</span></div>
              </div>

              <div class="detail-columns">
                <div class="detail-column">
                  <div class="list-item-card" v-if="detailLeadText">
                    <strong>整体摘要</strong>
                    <span class="helper-text">{{ detailLeadText }}</span>
                  </div>

                  <div class="list-item-card" v-if="detailConfidenceSummaryText">
                    <strong>可信度说明</strong>
                    <span class="helper-text">{{ detailConfidenceSummaryText }}</span>
                  </div>

                  <div class="list-item-card" v-if="topJointSummary">
                    <strong>重点关节</strong>
                    <span class="helper-text">{{ topJointSummary }}</span>
                  </div>
                </div>

                <div class="detail-column">
                  <div class="list-item-card" v-if="detailIssues.length">
                    <strong>问题片段</strong>
                    <div class="issue-chip-list">
                      <button
                        v-for="issue in detailIssues.slice(0, 6)"
                        :key="issue.id"
                        type="button"
                        class="issue-chip"
                        @click="jumpIssueToCompare(issue)"
                      >
                        {{ issueTypeText(issue.type) }} · {{ timeText(issue.sec) }}
                      </button>
                    </div>
                  </div>

                  <div class="list-item-card" v-if="detailLinks.length">
                    <strong>输出文件</strong>
                    <div class="detail-links">
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
                </div>
              </div>
            </div>
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
import {
  cancelPipeline,
  deletePipelineTask,
  getAnalysisReport,
  getPipelineResultSummary,
  listAnalysisReports,
  listPipelineTasks,
} from "../api/pipelines";
import { normalizedConfidenceIssues, normalizedConfidenceSummary } from "../utils/confidence";
import { focusDetailPanel } from "../utils/detailPanel";
import type {
  AnalysisReportDetailResponse,
  AnalysisReportItem,
  PipelineResultSummaryResponse,
  PipelineStatusType,
  PipelineTaskListItem,
} from "../types/video";

type WorkspaceTab = "all" | "running" | "completed" | "issues";

type RecordItem = PipelineTaskListItem & Partial<AnalysisReportItem> & {
  hasReport: boolean;
};

type IssueSeverity = "high" | "medium" | "low";

type IssueReplayItem = {
  id: string;
  pipelineId: string;
  pairName: string;
  teacherVideoId?: string | null;
  userVideoId?: string | null;
  type: string;
  severity: IssueSeverity;
  sec: number;
  frame?: number | null;
  summary: string;
  action?: string;
  finishedAt?: string | null;
  scoreTotal?: number | null;
  confidenceScore?: number | null;
};

type DetailLinkItem = {
  label: string;
  url: string;
};

const router = useRouter();
const route = useRoute();

const tabs: Array<{ key: WorkspaceTab; label: string }> = [
  { key: "all", label: "全部记录" },
  { key: "running", label: "进行中" },
  { key: "completed", label: "已完成" },
  { key: "issues", label: "问题片段" },
];

const records = ref<RecordItem[]>([]);
const loading = ref(false);
const issueLoading = ref(false);
const error = ref("");
const activeTab = ref<WorkspaceTab>("all");
const search = ref("");
const statusFilter = ref<PipelineStatusType | "all">("all");
const issueTypeFilter = ref("all");

const selectedRecordId = ref("");
const selectedIssueId = ref("");
const detail = ref<PipelineResultSummaryResponse | null>(null);
const detailLoading = ref(false);
const detailError = ref("");
const detailPanelRef = ref<HTMLElement | null>(null);
const issueMap = ref<Record<string, IssueReplayItem[]>>({});
const issueSourceKey = ref("");

const copyingId = ref("");
const deletingId = ref("");
const cancelingId = ref("");

const runningCount = computed(() => records.value.filter((item) => item.status === "pending" || item.status === "running").length);
const completedCount = computed(() => records.value.filter((item) => item.status === "done").length);
const completedRecords = computed(() => records.value.filter((item) => item.status === "done"));

const filteredRecords = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return records.value.filter((item) => {
    const text = `${item.pair_name || ""} ${item.pipeline_id}`.toLowerCase();
    const matchesKeyword = !keyword || text.includes(keyword);

    if (activeTab.value === "running" && item.status !== "pending" && item.status !== "running") return false;
    if (activeTab.value === "completed" && item.status !== "done") return false;
    if (statusFilter.value !== "all" && item.status !== statusFilter.value) return false;

    return matchesKeyword;
  });
});

const issueItems = computed(() =>
  Object.values(issueMap.value)
    .flat()
    .sort((a, b) => `${b.finishedAt || ""}`.localeCompare(`${a.finishedAt || ""}`) || a.sec - b.sec),
);

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

const selectedRecord = computed(() => records.value.find((item) => item.pipeline_id === selectedRecordId.value) ?? null);
const selectedIssue = computed(() => filteredIssues.value.find((item) => item.id === selectedIssueId.value) ?? null);
const canCancelSelectedRecord = computed(() => {
  const item = detail.value ?? selectedRecord.value;
  return Boolean(item && (item.status === "pending" || item.status === "running") && !item.cancel_requested);
});
const canDeleteSelectedRecord = computed(() => {
  const item = detail.value ?? selectedRecord.value;
  return Boolean(item && item.status !== "pending" && item.status !== "running");
});
const canOpenSelectedInCompare = computed(() => Boolean(selectedRecord.value?.teacher_video_id && selectedRecord.value?.user_video_id));
const detailConfidenceText = computed(() => confidenceText(detail.value?.report?.confidence?.score ?? detail.value?.confidence_score));
const detailConfidenceSummaryText = computed(() =>
  normalizedConfidenceSummary(detail.value?.report?.confidence, detail.value?.report?.confidence?.summary || detail.value?.confidence_summary),
);
const topJointSummary = computed(() => {
  const joints = detail.value?.report?.top_joints ?? detail.value?.top_joints;
  if (!Array.isArray(joints) || !joints.length) return "";
  return joints.slice(0, 3).map((item: any) => `${item[0]} (${Number(item[1]).toFixed(3)})`).join("、");
});
const detailLeadText = computed(() => {
  return (
    detail.value?.report?.recommendations?.overall ||
    detail.value?.overall_advice ||
    detail.value?.report?.beginner_report?.summary ||
    detail.value?.beginner_summary ||
    detail.value?.report?.teaching_report?.summary ||
    detail.value?.teaching_summary ||
    ""
  );
});
const detailLinks = computed<DetailLinkItem[]>(() => {
  const files = detail.value?.files || {};
  const links = [
    { label: "报告 JSON", url: files.report_url },
    { label: "摘要 JSON", url: files.summary_url },
    { label: "教师骨架视频", url: files.teacher_overlay_url },
    { label: "学员骨架视频", url: files.user_overlay_url },
    { label: "时间轴 JSON", url: files.timeline_json_url },
  ];
  return links.filter((item) => item.url).map((item) => ({ label: item.label, url: absMediaUrl(item.url) }));
});
const detailIssues = computed(() => (detail.value ? extractIssues(detail.value) : []));

function parseTab(value: unknown): WorkspaceTab {
  if (value === "running" || value === "completed" || value === "issues" || value === "all") return value;
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

async function loadWorkspace() {
  loading.value = true;
  error.value = "";
  try {
    const [taskData, reportData] = await Promise.all([
      listPipelineTasks({ limit: 100 }),
      listAnalysisReports({ limit: 100 }),
    ]);

    const taskMap = new Map(taskData.items.map((item) => [item.pipeline_id, item]));
    const reportMap = new Map(reportData.items.map((item) => [item.pipeline_id, item]));
    const ids = new Set<string>([...taskMap.keys(), ...reportMap.keys()]);

    const merged = Array.from(ids).map<RecordItem>((pipelineId) => {
      const task = taskMap.get(pipelineId);
      const report = reportMap.get(pipelineId);
      return {
        pipeline_id: pipelineId,
        pair_name: task?.pair_name || report?.pair_name || pipelineId,
        status: task?.status || report?.status || "done",
        stage: task?.stage || report?.stage || null,
        progress: task?.progress ?? null,
        message: task?.message || null,
        teacher_video_id: task?.teacher_video_id || report?.teacher_video_id || null,
        user_video_id: task?.user_video_id || report?.user_video_id || null,
        executor: task?.executor || report?.executor || null,
        attempt_count: task?.attempt_count ?? null,
        retry_count: task?.retry_count ?? null,
        error_type: task?.error_type ?? null,
        queued_at: task?.queued_at || report?.queued_at || null,
        started_at: task?.started_at || report?.started_at || null,
        finished_at: task?.finished_at || report?.finished_at || null,
        updated_at: task?.updated_at || report?.updated_at || null,
        score_total: task?.score_total ?? report?.score_total ?? null,
        confidence_score: task?.confidence_score ?? report?.confidence_score ?? null,
        cancel_requested: task?.cancel_requested ?? null,
        cancel_requested_at: task?.cancel_requested_at ?? null,
        timeout_sec: task?.timeout_sec ?? null,
        timeout_at: task?.timeout_at ?? null,
        score_pose: report?.score_pose ?? null,
        score_tempo: report?.score_tempo ?? null,
        confidence_level: report?.confidence_level ?? null,
        overall_advice: report?.overall_advice ?? null,
        confidence_summary: report?.confidence_summary ?? null,
        beginner_summary: report?.beginner_summary ?? null,
        teaching_summary: report?.teaching_summary ?? null,
        top_joints: report?.top_joints ?? [],
        files: report?.files ?? null,
        hasReport: Boolean(report),
      };
    });

    merged.sort((a, b) => latestTime(b).localeCompare(latestTime(a)));
    records.value = merged;

    await hydrateSelectionFromRoute();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? "记录中心加载失败";
  } finally {
    loading.value = false;
  }
}

async function hydrateSelectionFromRoute() {
  const tab = parseTab(route.query.tab);
  activeTab.value = tab;

  const pipelineId = routeQueryString(route.query.pipeline);
  const sec = Number(routeQueryString(route.query.sec));

  if (tab === "issues") {
    await ensureIssueMapLoaded();
    if (pipelineId) {
      const hit = filteredIssues.value.find((item) => item.pipelineId === pipelineId && (!Number.isFinite(sec) || Math.abs(item.sec - sec) < 0.11));
      if (hit) {
        await openIssue(hit.id);
      }
    }
    return;
  }

  if (pipelineId && records.value.some((item) => item.pipeline_id === pipelineId)) {
    await openRecord(pipelineId);
  }
}

async function ensureIssueMapLoaded() {
  const sourceKey = completedRecords.value.map((item) => item.pipeline_id).join(",");
  if (!sourceKey) {
    issueMap.value = {};
    issueSourceKey.value = "";
    return;
  }
  if (issueLoading.value || issueSourceKey.value === sourceKey) return;

  issueLoading.value = true;
  try {
    const details = await Promise.all(
      completedRecords.value.map(async (item) => {
        try {
          return await getAnalysisReport(item.pipeline_id);
        } catch {
          return null;
        }
      }),
    );

    const nextMap: Record<string, IssueReplayItem[]> = {};
    for (const detailItem of details) {
      if (!detailItem) continue;
      nextMap[detailItem.pipeline_id] = extractIssues(detailItem);
    }
    issueMap.value = nextMap;
    issueSourceKey.value = sourceKey;
  } finally {
    issueLoading.value = false;
  }
}

async function openRecord(pipelineId: string) {
  selectedRecordId.value = pipelineId;
  selectedIssueId.value = "";
  detailLoading.value = true;
  detailError.value = "";
  try {
    detail.value = await getPipelineResultSummary(pipelineId);
    focusDetailPanel(detailPanelRef, { forceScroll: true });
  } catch (err: any) {
    detail.value = null;
    detailError.value = err?.response?.data?.detail ?? err?.message ?? "记录详情加载失败";
  } finally {
    detailLoading.value = false;
  }
}

function closeRecordDetail() {
  selectedRecordId.value = "";
  detail.value = null;
  detailError.value = "";
}

async function toggleRecord(pipelineId: string) {
  if (pipelineId === selectedRecordId.value && detail.value) {
    closeRecordDetail();
    return;
  }
  await openRecord(pipelineId);
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
  try {
    await navigator.clipboard.writeText(pipelineId);
    copyingId.value = pipelineId;
    window.setTimeout(() => {
      if (copyingId.value === pipelineId) copyingId.value = "";
    }, 1400);
  } catch {
    detailError.value = "复制失败，请手动复制任务 ID。";
  }
}

async function cancelSelectedRecord() {
  const pipelineId = selectedRecordId.value;
  if (!pipelineId || !canCancelSelectedRecord.value) return;

  cancelingId.value = pipelineId;
  detailError.value = "";
  try {
    const status = await cancelPipeline(pipelineId);
    records.value = records.value.map((item) => (item.pipeline_id === pipelineId ? { ...item, ...status } : item));
    detail.value = detail.value ? { ...detail.value, ...status } : detail.value;
  } catch (err: any) {
    detailError.value = err?.response?.data?.detail ?? err?.message ?? "取消任务失败";
  } finally {
    cancelingId.value = "";
  }
}

async function deletePipeline(pipelineId: string) {
  const record = records.value.find((item) => item.pipeline_id === pipelineId);
  const label = record?.pair_name || pipelineId;
  const confirmed = window.confirm(`确认删除“${label}”吗？相关任务、报告和问题片段会一起移除。`);
  if (!confirmed) return;

  deletingId.value = pipelineId;
  try {
    await deletePipelineTask(pipelineId);
    records.value = records.value.filter((item) => item.pipeline_id !== pipelineId);
    const nextMap = { ...issueMap.value };
    delete nextMap[pipelineId];
    issueMap.value = nextMap;
    if (selectedRecordId.value === pipelineId) closeRecordDetail();
    if (selectedIssue.value?.pipelineId === pipelineId) closeIssueDetail();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? "删除记录失败";
  } finally {
    deletingId.value = "";
  }
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

function latestTime(item: Partial<RecordItem>) {
  return `${item.updated_at || item.finished_at || item.started_at || item.queued_at || ""}`;
}

function recordLead(item: Partial<RecordItem>) {
  if (item.status === "pending" || item.status === "running") {
    return item.message || `${stageText(item.stage, item.status)}，这条记录仍在处理中。`;
  }
  if (item.status === "failed") {
    return item.message || "本条分析未成功完成，请先查看异常信息或尝试重新处理。";
  }
  return (
    item.overall_advice ||
    item.beginner_summary ||
    item.teaching_summary ||
    normalizedConfidenceSummary(null, item.confidence_summary) ||
    "本条记录已完成，可展开查看摘要、输出文件和问题片段。"
  );
}

function extractIssues(report: Partial<AnalysisReportDetailResponse | PipelineResultSummaryResponse>): IssueReplayItem[] {
  const result: IssueReplayItem[] = [];
  const pairName = report.pair_name || report.pipeline_id || "未命名记录";
  const markers = Array.isArray(report.report?.markers) ? report.report?.markers : [];

  for (const marker of markers) {
    const sec = Number((marker as any)?.sec);
    if (!Number.isFinite(sec)) continue;
    result.push({
      id: `${report.pipeline_id}_marker_${(marker as any)?.frame ?? sec}_${(marker as any)?.type || "unknown"}`,
      pipelineId: String(report.pipeline_id || ""),
      pairName,
      teacherVideoId: report.teacher_video_id,
      userVideoId: report.user_video_id,
      type: String((marker as any)?.type || "pose_error"),
      severity: markerSeverity((marker as any)?.severity),
      sec,
      frame: Number((marker as any)?.frame),
      summary: `${issueTypeText(String((marker as any)?.type || "pose_error"))}，${timeText(sec)}，${(marker as any)?.severity ? severityText(markerSeverity((marker as any)?.severity)) : "需要关注"}`,
      action: "建议跳回动作分析页，结合双视频和时间轴对照这一段。",
      finishedAt: report.finished_at || report.updated_at,
      scoreTotal: report.score_total,
      confidenceScore: report.confidence_score,
    });
  }

  const tempoSegments = Array.isArray(report.report?.tempo_segments) ? report.report?.tempo_segments : [];
  for (let index = 0; index < tempoSegments.length; index += 1) {
    const segment = tempoSegments[index] as any;
    const sec = Number(segment?.start_sec ?? segment?.sec ?? segment?.t0);
    if (!Number.isFinite(sec)) continue;
    result.push({
      id: `${report.pipeline_id}_tempo_${index}`,
      pipelineId: String(report.pipeline_id || ""),
      pairName,
      teacherVideoId: report.teacher_video_id,
      userVideoId: report.user_video_id,
      type: "tempo",
      severity: "medium",
      sec,
      frame: null,
      summary: `第 ${index + 1} 段节奏异常，建议对照拍点和动作转场。`,
      action: "可先聚焦这一段的拍点、重心转移和动作发力节奏。",
      finishedAt: report.finished_at || report.updated_at,
      scoreTotal: report.score_total,
      confidenceScore: report.confidence_score,
    });
  }

  const confidenceSummary = normalizedConfidenceSummary(report.report?.confidence, report.confidence_summary);
  const confidenceIssues = normalizedConfidenceIssues(report.report?.confidence);
  for (let index = 0; index < confidenceIssues.length; index += 1) {
    const issue = confidenceIssues[index] as any;
    const markerSec = Number(markers.find((item: any) => Number.isFinite(Number(item?.sec)))?.sec);
    result.push({
      id: `${report.pipeline_id}_confidence_${index}`,
      pipelineId: String(report.pipeline_id || ""),
      pairName,
      teacherVideoId: report.teacher_video_id,
      userVideoId: report.user_video_id,
      type: "confidence",
      severity: "high",
      sec: Number.isFinite(markerSec) ? markerSec : 0,
      frame: null,
      summary: String(issue?.message || confidenceSummary || "本轮分析存在可信度风险。"),
      action: String(issue?.suggestion || "建议先改善拍摄视角或跟踪质量，再重新复测。"),
      finishedAt: report.finished_at || report.updated_at,
      scoreTotal: report.score_total,
      confidenceScore: report.confidence_score,
    });
  }

  return result.sort((a, b) => a.sec - b.sec);
}

function markerSeverity(value?: string): IssueSeverity {
  if (value === "severe" || value === "clear") return "high";
  if (value === "mild") return "medium";
  return "medium";
}

function progressPercent(progress?: number | null) {
  const value = Number(progress ?? 0);
  if (!Number.isFinite(value)) return 0;
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
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

function issueTypeText(value?: string) {
  if (value === "pose_error") return "动作误差";
  if (value === "tempo") return "节奏异常";
  if (value === "confidence") return "可信度风险";
  if (value === "tracking_bad") return "跟踪问题";
  return value || "待定";
}

function severityText(value?: string) {
  if (value === "high") return "高优先级";
  if (value === "medium") return "中优先级";
  return "低优先级";
}

function severityTone(value?: string) {
  if (value === "high") return "danger";
  if (value === "medium") return "warn";
  return "ok";
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

function timeText(sec?: number | null) {
  const num = Number(sec);
  if (!Number.isFinite(num)) return "--";
  return `${num.toFixed(2)}s`;
}

function formatDate(value?: string | null) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

watch(
  () => route.query.tab,
  async (value) => {
    const nextTab = parseTab(value);
    activeTab.value = nextTab;
    if (nextTab === "issues") {
      await ensureIssueMapLoaded();
    }
  },
);

watch(
  () => [route.query.pipeline, route.query.sec, route.query.tab],
  async () => {
    if (!records.value.length) return;
    await hydrateSelectionFromRoute();
  },
);

watch(activeTab, async (value) => {
  if (value === "issues") {
    await ensureIssueMapLoaded();
  }
});

onMounted(async () => {
  activeTab.value = parseTab(route.query.tab);
  await loadWorkspace();
  if (activeTab.value === "issues") {
    await ensureIssueMapLoaded();
  }
});
</script>

<style scoped>
.records-page,
.records-toolbar,
.records-workspace,
.records-list,
.record-shell,
.inline-detail,
.detail-stack,
.detail-column,
.detail-columns,
.issue-chip-list {
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
  grid-template-columns: minmax(0, 1.7fr) 160px 180px 220px;
  gap: 12px;
  padding: 0 14px 8px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  color: var(--muted);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.issue-table-head {
  grid-template-columns: minmax(0, 1.8fr) 140px 120px 220px;
}

.dense-list {
  gap: 10px;
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

.issue-dense-row {
  grid-template-columns: minmax(0, 1.8fr) 140px 120px 220px;
}

.dense-row:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(226, 109, 61, 0.18);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.04);
}

.dense-row.active {
  border-color: rgba(226, 109, 61, 0.28);
  background: linear-gradient(180deg, rgba(255, 248, 243, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
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

.inline-detail {
  padding: 18px 20px 20px;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.compact-stats {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.detail-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.issue-chip-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.issue-chip {
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.94);
  color: var(--text);
  padding: 0.78rem 0.88rem;
  box-shadow: none;
  text-transform: none;
  letter-spacing: 0;
  font-size: 0.86rem;
  font-weight: 700;
}

.danger-button {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.22);
}

.danger-button:hover:not(:disabled) {
  border-color: rgba(180, 35, 24, 0.4);
  background: rgba(180, 35, 24, 0.08);
}

@media (max-width: 1180px) {
  .records-kpi-row,
  .records-toolbar-grid,
  .records-table-head,
  .dense-row,
  .issue-dense-row,
  .detail-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1024px) {
  .compact-stats,
  .issue-chip-list {
    grid-template-columns: 1fr;
  }
}
</style>
