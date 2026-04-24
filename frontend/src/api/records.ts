import { http } from "./http";
import type { RecordWorkspaceResponse } from "../types/video";

export async function getRecordsWorkspace(limit = 100): Promise<RecordWorkspaceResponse> {
  const { data } = await http.get<RecordWorkspaceResponse>("/api/records/workspace", {
    params: { limit },
  });
  return data;
}
