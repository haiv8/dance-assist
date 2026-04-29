import { http } from "./http";
import type { PracticeProjectDetailResponse, PracticeProjectListResponse, RecordWorkspaceResponse } from "../types/video";

export async function getRecordsWorkspace(limit = 50): Promise<RecordWorkspaceResponse> {
  const { data } = await http.get<RecordWorkspaceResponse>("/api/records/workspace", {
    params: { limit },
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
