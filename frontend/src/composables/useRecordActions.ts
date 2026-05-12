import { ref, type Ref } from "vue";
import { appConfig } from "../config/appConfig";
import { cancelPipeline, deletePipelineTask } from "../api/pipelines";
import { isRunningPipelineStatus } from "../services/pipelineStatus";
import { friendlyError, runningTaskDeleteMessage } from "../utils/errors";
import type { PipelineStatusResponse, RecordWorkspaceItem } from "../types/video";

export function isRunningTaskStatus(status?: string | null) {
  return isRunningPipelineStatus(status);
}

export function useRecordActions(records: Ref<RecordWorkspaceItem[]>) {
  const copyingId = ref("");
  const deletingId = ref("");
  const cancelingId = ref("");
  const bulkDeleting = ref(false);
  const actionError = ref("");

  function canDeletePipelineId(pipelineId: string) {
    const item = records.value.find((record) => record.pipeline_id === pipelineId);
    return !item || !isRunningTaskStatus(item.status);
  }

  async function copyPipelineId(pipelineId: string) {
    try {
      await navigator.clipboard.writeText(pipelineId);
      copyingId.value = pipelineId;
      window.setTimeout(() => {
        if (copyingId.value === pipelineId) copyingId.value = "";
      }, appConfig.clipboardResetMs);
    } catch {
      actionError.value = "复制失败，请手动复制任务 ID。";
    }
  }

  async function cancelPipelineRecord(pipelineId: string): Promise<PipelineStatusResponse | null> {
    if (!pipelineId) return null;
    cancelingId.value = pipelineId;
    actionError.value = "";
    try {
      return await cancelPipeline(pipelineId);
    } catch (err: any) {
      actionError.value = friendlyError(err, "取消任务失败");
      return null;
    } finally {
      cancelingId.value = "";
    }
  }

  async function deletePipelineRecord(pipelineId: string) {
    const record = records.value.find((item) => item.pipeline_id === pipelineId);
    if (record && isRunningTaskStatus(record.status)) {
      actionError.value = runningTaskDeleteMessage();
      return false;
    }

    deletingId.value = pipelineId;
    actionError.value = "";
    try {
      await deletePipelineTask(pipelineId);
      return true;
    } catch (err: any) {
      actionError.value = friendlyError(err, "删除记录失败");
      return false;
    } finally {
      deletingId.value = "";
    }
  }

  return {
    copyingId,
    deletingId,
    cancelingId,
    bulkDeleting,
    actionError,
    canDeletePipelineId,
    copyPipelineId,
    cancelPipelineRecord,
    deletePipelineRecord,
  };
}
