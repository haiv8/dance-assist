import type {
  PipelineResultResponse,
  PipelineRunResponse,
  PipelineStatusResponse,
  PipelineStatusType,
} from "../types/video";

export type PipelineMeta = Partial<PipelineRunResponse & PipelineStatusResponse & PipelineResultResponse>;

export interface PipelineTaskPatch {
  status?: PipelineStatusType;
  stage?: string;
  progress?: number;
  message?: string;
  cancelRequested?: boolean;
}

export function isRunningPipelineStatus(status?: string | null): status is "pending" | "running" {
  return status === "pending" || status === "running";
}

export function isTerminalPipelineStatus(status?: string | null): status is "done" | "failed" | "canceled" {
  return status === "done" || status === "failed" || status === "canceled";
}

export function canCancelPipeline(status?: string | null, cancelRequested = false): boolean {
  return isRunningPipelineStatus(status) && !cancelRequested;
}

export function normalizePipelineProgress(value: unknown): number | undefined {
  const progress = Number(value);
  if (!Number.isFinite(progress)) return undefined;
  return Math.max(0, Math.min(1, progress));
}

export function pipelineMetaToPatch(meta?: PipelineMeta | null): PipelineTaskPatch {
  if (!meta) return {};
  const patch: PipelineTaskPatch = {};
  if (meta.status) patch.status = meta.status;
  if (typeof meta.stage === "string") patch.stage = meta.stage;
  const progress = normalizePipelineProgress(meta.progress);
  if (progress !== undefined) patch.progress = progress;
  if (typeof meta.message === "string") patch.message = meta.message;
  if (typeof meta.cancel_requested === "boolean") patch.cancelRequested = meta.cancel_requested;
  return patch;
}

export function pipelineStatusText(status?: string | null): string {
  if (status === "pending") return "等待中";
  if (status === "running") return "分析中";
  if (status === "done") return "已完成";
  if (status === "failed") return "失败";
  if (status === "canceled") return "已取消";
  return status || "未开始";
}

export function pipelineStatusTone(status?: string | null): "ok" | "warn" | "danger" | "neutral" {
  if (status === "done") return "ok";
  if (status === "failed") return "danger";
  if (status === "pending" || status === "running") return "warn";
  return "neutral";
}

export function pipelineStageText(stage?: string | null, status?: string | null): string {
  if (stage === "queued") return "已进入队列";
  if (stage === "preparing_inputs") return "准备素材";
  if (stage === "extracting_pose") return "提取骨架";
  if (stage === "aligning_motion") return "动作对齐与评分";
  if (stage === "rendering_outputs") return "生成对比输出";
  if (stage === "packaging_results") return "整理结果";
  if (stage === "completed") return "结果已就绪";
  if (stage === "failed") return "任务失败";
  if (stage === "canceled") return "任务已取消";
  return pipelineStatusText(status);
}
