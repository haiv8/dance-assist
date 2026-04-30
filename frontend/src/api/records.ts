import { http } from "./http";
import type { PracticeProjectDetailResponse, PracticeProjectListResponse, RecordFlagsResponse, RecordWorkspaceResponse } from "../types/video";

export async function getRecordsWorkspace(limit = 50): Promise<RecordWorkspaceResponse> {
  const { data } = await http.get<RecordWorkspaceResponse>("/api/records/workspace", {
    params: { limit },
  });
  return data;
}

export async function getRecordFlags(): Promise<Record<string, { starred?: boolean; note?: string; updated_at?: string }>> {
  const { data } = await http.get<{ items: Record<string, { starred?: boolean; note?: string; updated_at?: string }> }>("/api/records/flags");
  return data.items || {};
}

export async function updateRecordFlags(pipelineId: string, payload: { starred?: boolean; note?: string }): Promise<RecordFlagsResponse> {
  const { data } = await http.patch<RecordFlagsResponse>(`/api/records/${encodeURIComponent(pipelineId)}/flags`, payload);
  return data;
}

export async function downloadRecordsCsv(params: {
  limit?: number;
  starred?: boolean;
  status?: "done" | "failed" | "running";
} = {}): Promise<Blob> {
  const { data } = await http.get<Blob>("/api/records/export.csv", {
    params,
    responseType: "blob",
  });
  return data;
}

export async function getPracticeProjects(limit = 200): Promise<PracticeProjectListResponse> {
  const { data } = await http.get<PracticeProjectListResponse>("/api/practice-projects", {
    params: { limit },
  });
  return data;
}

export async function getPracticeProject(teacherVideoId: string, limit = 200): Promise<PracticeProjectDetailResponse> {
  const { data } = await http.get<PracticeProjectDetailResponse>(`/api/practice-projects/${encodeURIComponent(teacherVideoId)}`, {
    params: { limit },
  });
  return data;
}
