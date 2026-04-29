import { computed, ref } from "vue";
import { getRecordsWorkspace } from "../api/records";
import { friendlyError } from "../utils/errors";
import type { IssueReplayItem, RecordWorkspaceIssueItem, RecordWorkspaceItem } from "../types/video";

export function mapIssueItems(items: RecordWorkspaceIssueItem[]): IssueReplayItem[] {
  return items.map((item) => ({
    id: item.id,
    pipelineId: item.pipeline_id,
    pairName: item.pair_name,
    teacherVideoId: item.teacher_video_id,
    userVideoId: item.user_video_id,
    type: item.type,
    severity: item.severity,
    sec: item.sec,
    frame: item.frame,
    summary: item.summary,
    action: item.action,
    finishedAt: item.finished_at,
    scoreTotal: item.score_total,
    confidenceScore: item.confidence_score,
  }));
}

export function mapWorkspaceIssues(items: RecordWorkspaceIssueItem[]): Record<string, IssueReplayItem[]> {
  const nextMap: Record<string, IssueReplayItem[]> = {};
  for (const mapped of mapIssueItems(items)) {
    if (!nextMap[mapped.pipelineId]) {
      nextMap[mapped.pipelineId] = [];
    }
    nextMap[mapped.pipelineId].push(mapped);
  }
  return nextMap;
}

export function useRecordsWorkspace() {
  const records = ref<RecordWorkspaceItem[]>([]);
  const loading = ref(false);
  const issueLoading = ref(false);
  const error = ref("");
  const issueMap = ref<Record<string, IssueReplayItem[]>>({});

  const issueItems = computed(() =>
    Object.values(issueMap.value)
      .flat()
      .sort((a, b) => `${b.finishedAt || ""}`.localeCompare(`${a.finishedAt || ""}`) || a.sec - b.sec),
  );

  async function loadWorkspace(limit = 100) {
    loading.value = true;
    issueLoading.value = true;
    error.value = "";
    try {
      const workspace = await getRecordsWorkspace(limit);
      records.value = workspace.items;
      issueMap.value = mapWorkspaceIssues(workspace.issues);
    } catch (err: any) {
      error.value = friendlyError(err, "记录中心加载失败");
    } finally {
      loading.value = false;
      issueLoading.value = false;
    }
  }

  function removePipeline(pipelineId: string) {
    records.value = records.value.filter((item) => item.pipeline_id !== pipelineId);
    const nextMap = { ...issueMap.value };
    delete nextMap[pipelineId];
    issueMap.value = nextMap;
  }

  return {
    records,
    loading,
    issueLoading,
    error,
    issueMap,
    issueItems,
    loadWorkspace,
    removePipeline,
  };
}
