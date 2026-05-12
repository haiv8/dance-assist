import { computed, ref } from "vue";
import type { PipelineMeta } from "../services/pipelineStatus";
import {
  canCancelPipeline,
  pipelineMetaToPatch,
  pipelineStageText,
  pipelineStatusText,
} from "../services/pipelineStatus";
import type { PipelineStatusType } from "../types/video";

export function usePipelineTaskState() {
  const pipelineId = ref("");
  const pipelineStatus = ref<PipelineStatusType | "">("");
  const pipelineStage = ref("");
  const pipelineProgress = ref(0);
  const pipelineMessage = ref("");
  const cancelRequested = ref(false);

  const pipelineStatusTextValue = computed(() => pipelineStatusText(pipelineStatus.value));
  const pipelineStageTextValue = computed(() => pipelineStageText(pipelineStage.value, pipelineStatus.value));
  const pipelineProgressPercent = computed(() => Math.round(Math.max(0, Math.min(1, pipelineProgress.value || 0)) * 100));
  const canCancelCurrentPipeline = computed(() =>
    Boolean(pipelineId.value && canCancelPipeline(pipelineStatus.value, cancelRequested.value)),
  );

  function applyPipelineMeta(meta?: PipelineMeta | null) {
    const patch = pipelineMetaToPatch(meta);
    if (patch.status) pipelineStatus.value = patch.status;
    if (patch.stage !== undefined) pipelineStage.value = patch.stage;
    if (patch.progress !== undefined) pipelineProgress.value = patch.progress;
    if (patch.message !== undefined) pipelineMessage.value = patch.message;
    if (patch.cancelRequested !== undefined) cancelRequested.value = patch.cancelRequested;
  }

  function resetPipelineTask() {
    pipelineId.value = "";
    pipelineStatus.value = "";
    pipelineStage.value = "";
    pipelineProgress.value = 0;
    pipelineMessage.value = "";
    cancelRequested.value = false;
  }

  function preparePipelineTask(stage = "queued") {
    pipelineStatus.value = "";
    pipelineStage.value = stage;
    pipelineProgress.value = 0;
    pipelineMessage.value = "";
    cancelRequested.value = false;
  }

  return {
    pipelineId,
    pipelineStatus,
    pipelineStage,
    pipelineProgress,
    pipelineMessage,
    cancelRequested,
    pipelineStatusText: pipelineStatusTextValue,
    pipelineStageText: pipelineStageTextValue,
    pipelineProgressPercent,
    canCancelCurrentPipeline,
    applyPipelineMeta,
    resetPipelineTask,
    preparePipelineTask,
  };
}
