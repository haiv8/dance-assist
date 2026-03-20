import { http } from "./http";
import type { RoleQueryType, RoleType, VideoActionResponse, VideoListResponse, VideoUploadResponse } from "../types/video";

export async function uploadVideo(params: {
  file: File;
  role: RoleType;
  name?: string;
}): Promise<VideoUploadResponse> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("role", params.role);
  if (params.name && params.name.trim()) {
    form.append("name", params.name.trim());
  }
  const { data } = await http.post<VideoUploadResponse>("/api/videos/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listVideos(role: RoleQueryType = "all"): Promise<VideoListResponse> {
  const { data } = await http.get<VideoListResponse>("/api/videos", {
    params: { role },
  });
  return data;
}

export async function renameVideo(params: {
  videoId: string;
  role: RoleType;
  name: string;
}): Promise<VideoActionResponse> {
  const { data } = await http.patch<VideoActionResponse>(`/api/videos/${params.videoId}`, { name: params.name }, {
    params: { role: params.role },
  });
  return data;
}

export async function deleteVideo(params: {
  videoId: string;
  role: RoleType;
}): Promise<VideoActionResponse> {
  const { data } = await http.delete<VideoActionResponse>(`/api/videos/${params.videoId}`, {
    params: { role: params.role },
  });
  return data;
}
