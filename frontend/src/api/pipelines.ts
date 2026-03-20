import { http } from "./http";
import type {
  AnalysisReportDetailResponse,
  AnalysisReportListResponse,
  SystemActionResponse,
  SystemStatusResponse,
  PipelineFrameDetailResponse,
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


export async function getSystemStatus(): Promise<SystemStatusResponse> {
  const { data } = await http.get<SystemStatusResponse>("/api/system/status");
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
