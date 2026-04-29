import { computed, ref } from "vue";
import { getAiCoachReport } from "../api/ai";
import { friendlyError } from "../utils/errors";
import type { AiCoachResponse } from "../types/video";

export function useAiCoach() {
  const aiCoach = ref<AiCoachResponse | null>(null);
  const aiCoachLoading = ref(false);
  const aiCoachError = ref("");

  const aiCoachSourceText = computed(() => {
    if (!aiCoach.value) return "";
    if (aiCoach.value.generated_by === "aliyun") return aiCoach.value.model || "阿里云百炼";
    if (aiCoach.value.generated_by === "openai") return aiCoach.value.model || "OpenAI";
    return "本地兜底";
  });

  const aiCoachFallbackHint = computed(() => {
    if (aiCoach.value?.generated_by !== "local_fallback") return "";
    return "当前展示的是基于分析报告的本地规则建议；云端 AI 不可用时，演示复盘仍可继续。";
  });

  function clearAiCoach() {
    aiCoach.value = null;
    aiCoachError.value = "";
  }

  async function loadAiCoach(pipelineId: string) {
    if (!pipelineId) return;
    aiCoachLoading.value = true;
    aiCoachError.value = "";
    try {
      aiCoach.value = await getAiCoachReport(pipelineId);
    } catch (err: any) {
      aiCoachError.value = friendlyError(err, "AI解读生成失败");
    } finally {
      aiCoachLoading.value = false;
    }
  }

  return {
    aiCoach,
    aiCoachLoading,
    aiCoachError,
    aiCoachSourceText,
    aiCoachFallbackHint,
    clearAiCoach,
    loadAiCoach,
  };
}
