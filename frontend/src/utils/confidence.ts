const QUESTION_ONLY_RE = /^[\s?？]+$/;

function isUsableText(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const text = value.trim();
  if (!text) return false;
  return !QUESTION_ONLY_RE.test(text);
}

function fallbackLevel(score: unknown): string {
  const num = Number(score);
  if (!Number.isFinite(num)) return "medium";
  if (num >= 0.78) return "high";
  if (num >= 0.55) return "medium";
  return "low";
}

function fallbackSummary(level: string): string {
  if (level === "high") {
    return "当前结果可信度较高，关键点跟踪、动作对齐和节奏估计整体稳定，可作为本轮分析的主要参考。";
  }
  if (level === "low") {
    return "当前结果可信度较低，建议优先检查拍摄视角、遮挡和节奏同步情况，再结合视频回放谨慎解读。";
  }
  return "当前结果可信度中等，整体趋势可以参考，但局部片段可能受跟踪质量或对齐稳定性影响。";
}

function fallbackIssueCopy(code: string): { message: string; suggestion: string } {
  if (code === "tracking_coverage_low") {
    return {
      message: "关键点覆盖率偏低，部分肢体没有被稳定识别。",
      suggestion: "建议保证全身完整入镜、光照均匀，并尽量减少快速遮挡后再重新分析。",
    };
  }
  if (code === "long_occlusion_gap") {
    return {
      message: "存在较长时间的遮挡或关键点缺失。",
      suggestion: "建议拉开拍摄距离，减少人与道具或身体自遮挡，确保手脚和躯干连续可见。",
    };
  }
  if (code === "alignment_unstable") {
    return {
      message: "动作对齐稳定性不足，部分片段的匹配结果可能不够可靠。",
      suggestion: "建议检查示范与学员视频的起始时刻是否接近，并尽量保留完整连续的动作片段。",
    };
  }
  if (code === "tempo_confidence_low") {
    return {
      message: "节奏估计稳定性较低，节拍相关判断需要谨慎参考。",
      suggestion: "建议使用更清晰的原始音频，或在节奏更明确的片段重新分析。",
    };
  }
  return {
    message: "本轮分析存在可信度风险。",
    suggestion: "建议结合原视频回放检查拍摄质量，并在条件更稳定时重新分析。",
  };
}

export function normalizedConfidenceSummary(
  confidence: Record<string, any> | null | undefined,
  fallback?: unknown,
): string {
  if (isUsableText(confidence?.summary)) return confidence.summary.trim();
  if (isUsableText(fallback)) return fallback.trim();
  return fallbackSummary(fallbackLevel(confidence?.level || confidence?.score));
}

export function normalizedConfidenceIssues(
  confidence: Record<string, any> | null | undefined,
): Array<Record<string, any>> {
  if (!Array.isArray(confidence?.issues)) return [];
  return confidence.issues.map((rawIssue) => {
    const issue = rawIssue && typeof rawIssue === "object" ? rawIssue : {};
    const code = String(issue.code || "").trim();
    const fallback = fallbackIssueCopy(code);
    return {
      ...issue,
      code,
      message: isUsableText(issue.message) ? String(issue.message).trim() : fallback.message,
      suggestion: isUsableText(issue.suggestion) ? String(issue.suggestion).trim() : fallback.suggestion,
    };
  });
}
