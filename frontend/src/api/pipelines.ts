import { http } from "./http";
import type {
  AnalysisReportDetailResponse,
  AnalysisReportListResponse,
  PipelineActionResponse,
  SystemActionResponse,
  SystemStatusResponse,
  PipelineFrameDetailResponse,
  PipelineFrameRangeResponse,
  PipelineResultResponse,
  PipelineResultSummaryResponse,
  PipelineRunRequest,
  PipelineRunResponse,
  PipelineStatusResponse,
  PipelineTaskListResponse,
} from "../types/video";

export async function runPipeline(body: PipelineRunRequest): Promise<PipelineRunResponse> {
  const { data } = await http.post<PipelineRunResponse>("/api/pipelines/run", body);
  return data;
}

export async function getPipelineStatus(pipelineId: string): Promise<PipelineStatusResponse> {
  const { data } = await http.get<PipelineStatusResponse>(`/api/pipelines/${pipelineId}/status`);
  return data;
}

export async function cancelPipeline(pipelineId: string): Promise<PipelineStatusResponse> {
  const { data } = await http.post<PipelineStatusResponse>(`/api/pipelines/${pipelineId}/cancel`);
  return data;
}

export async function deletePipelineTask(pipelineId: string): Promise<PipelineActionResponse> {
  const { data } = await http.delete<PipelineActionResponse>(`/api/pipelines/${pipelineId}`);
  return data;
}

export async function retryPipeline(pipelineId: string, overwrite = false): Promise<PipelineStatusResponse> {
  const { data } = await http.post<PipelineStatusResponse>(`/api/pipelines/${pipelineId}/retry`, null, {
    params: { overwrite },
  });
  return data;
}

export async function getPipelineResult(pipelineId: string): Promise<PipelineResultResponse> {
  const { data } = await http.get<PipelineResultResponse>(`/api/pipelines/${pipelineId}/result`);
  return data;
}

export async function getPipelineResultSummary(pipelineId: string): Promise<PipelineResultSummaryResponse> {
  const { data } = await http.get<PipelineResultSummaryResponse>(`/api/pipelines/${pipelineId}/result/summary`);
  return data;
}

export async function getPipelineFrameDetail(
  pipelineId: string,
  frame: number,
): Promise<PipelineFrameDetailResponse> {
  const { data } = await http.get<PipelineFrameDetailResponse>(`/api/pipelines/${pipelineId}/result/frame/${frame}`);
  return data;
}

export async function getPipelineFrameRange(
  pipelineId: string,
  params: {
    start_frame?: number;
    end_frame?: number;
    start_sec?: number;
    end_sec?: number;
  },
): Promise<PipelineFrameRangeResponse> {
  const { data } = await http.get<PipelineFrameRangeResponse>(`/api/pipelines/${pipelineId}/result/frames`, { params });
  return data;
}

export async function listPipelineTasks(params?: {
  limit?: number;
  status?: string;
}): Promise<PipelineTaskListResponse> {
  const { data } = await http.get<PipelineTaskListResponse>("/api/pipelines", { params });
  return data;
}


export async function listAnalysisReports(params?: {
  limit?: number;
  q?: string;
  min_score?: number;
  min_confidence?: number;
}): Promise<AnalysisReportListResponse> {
  const { data } = await http.get<AnalysisReportListResponse>("/api/reports", { params });
  return data;
}

export async function getAnalysisReport(pipelineId: string): Promise<AnalysisReportDetailResponse> {
  const { data } = await http.get<AnalysisReportDetailResponse>(`/api/reports/${pipelineId}`);
  return data;
}


const SYSTEM_STATUS_CACHE_TTL_MS = 60_000;
let cachedSystemStatus: SystemStatusResponse | null = null;
let cachedSystemStatusAt = 0;
let systemStatusRequest: Promise<SystemStatusResponse> | null = null;

export async function getSystemStatus(options?: { force?: boolean; maxAgeMs?: number }): Promise<SystemStatusResponse> {
  const maxAgeMs = options?.maxAgeMs ?? SYSTEM_STATUS_CACHE_TTL_MS;
  const now = Date.now();
  if (!options?.force && cachedSystemStatus && now - cachedSystemStatusAt < maxAgeMs) {
    return cachedSystemStatus;
  }
  if (!options?.force && systemStatusRequest) return systemStatusRequest;

  systemStatusRequest = http.get<SystemStatusResponse>("/api/system/status")
    .then(({ data }) => {
      cachedSystemStatus = data;
      cachedSystemStatusAt = Date.now();
      return data;
    })
    .finally(() => {
      systemStatusRequest = null;
    });

  return systemStatusRequest;
}

export function getCachedSystemStatus(): SystemStatusResponse | null {
  return cachedSystemStatus;
}

export async function getSystemStatusUncached(): Promise<SystemStatusResponse> {
  const { data } = await http.get<SystemStatusResponse>("/api/system/status");
  cachedSystemStatus = data;
  cachedSystemStatusAt = Date.now();
  return data;
}

export async function rebuildAnalysisReports(): Promise<SystemActionResponse> {
  const { data } = await http.post<SystemActionResponse>("/api/system/maintenance/rebuild-reports");
  return data;
}


export async function trimOutputPairs(keep: number): Promise<SystemActionResponse> {
  const { data } = await http.post<SystemActionResponse>("/api/system/maintenance/trim-outputs", null, { params: { keep } });
  return data;
}

export async function cleanupDebugArtifacts(): Promise<SystemActionResponse> {
  const { data } = await http.post<SystemActionResponse>("/api/system/maintenance/cleanup-debug");
  return data;
}
