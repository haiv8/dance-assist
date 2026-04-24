import { http } from "./http";
import type { AiCoachResponse, AiProviderStatusResponse } from "../types/video";

export async function getAiCoachReport(pipelineId: string): Promise<AiCoachResponse> {
  const { data } = await http.post<AiCoachResponse>(`/api/ai/reports/${pipelineId}/coach`, {
    force_refresh: false,
  }, {
    timeout: 120_000,
  });
  return data;
}

export async function getAiProviderStatus(): Promise<AiProviderStatusResponse> {
  const { data } = await http.get<AiProviderStatusResponse>("/api/ai/status");
  return data;
}
