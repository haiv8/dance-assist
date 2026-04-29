import type { PipelineResultSummaryResponse, ScoreExplanation } from "../types/video";

export function confidenceLevelText(value?: number | string | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  if (num >= 0.78) return "high";
  if (num >= 0.55) return "medium";
  return "low";
}

export function isLowConfidence(value?: number | string | null) {
  const num = Number(value);
  return Number.isFinite(num) && num < 0.55;
}

export function normalizeScoreExplanation(value: unknown): ScoreExplanation | null {
  if (!value || typeof value !== "object") return null;
  const item = value as ScoreExplanation;
  if (!item.summary && !item.next_action && !item.score_note) return null;
  return {
    level: item.level || null,
    summary: item.summary || "总分用于辅助训练复盘，需要结合视频和问题片段一起判断。",
    score_note: item.score_note || "总分综合动作准确性、节奏匹配、流畅度和质量风险；分数用于训练复盘，不等同于教师评分。",
    confidence_note: item.confidence_note || "可信度用于说明姿态跟踪和对齐结果是否稳定，不等同于动作好坏。",
    main_factor: item.main_factor || null,
    next_action: item.next_action || "建议先查看高优先级问题片段，再结合对照视频分段练习。",
  };
}

export function buildFallbackScoreExplanation(
  detail: PipelineResultSummaryResponse | null | undefined,
  issueCount = 0,
): ScoreExplanation {
  const scores = detail?.report?.scores || {};
  const pose = Number(scores.score_pose ?? detail?.score_pose);
  const tempo = Number(scores.score_tempo ?? detail?.score_tempo);
  const confidence = Number(detail?.report?.confidence?.score ?? detail?.confidence_score);
  const hasLowConfidence = Number.isFinite(confidence) && confidence < 0.55;

  let summary = "总分由动作准确性、节奏匹配、流畅度和质量风险共同决定，建议结合问题片段复盘。";
  let mainFactor: ScoreExplanation["main_factor"] = "balanced";
  if (hasLowConfidence) {
    summary = "当前可信度偏低，分数需要结合视频回看谨慎理解，建议先检查拍摄质量。";
    mainFactor = "confidence";
  } else if (Number.isFinite(pose) && Number.isFinite(tempo) && tempo - pose >= 8) {
    summary = "当前总分主要受动作空间偏差影响，节奏匹配相对较好。";
    mainFactor = "pose";
  } else if (Number.isFinite(pose) && Number.isFinite(tempo) && pose - tempo >= 8) {
    summary = "当前总分主要受节奏偏差影响，动作姿态接近度相对更稳定。";
    mainFactor = "tempo";
  }

  return {
    level: null,
    summary,
    score_note: "总分不是教师主观评分，而是基于动作、节奏、流畅度和质量风险的辅助复盘指标。",
    confidence_note: hasLowConfidence
      ? "可信度较低时，建议优先检查拍摄角度、全身入镜、光照和遮挡情况。"
      : "可信度反映姿态跟踪和对齐稳定性，不等于动作好坏。",
    main_factor: mainFactor,
    next_action: issueCount > 0
      ? "下一步优先查看高优先级问题片段，再回到视频中分段练习。"
      : "下一步可以从整体视频回看和重点关节开始复盘。",
  };
}

export function scoreExplanationForDetail(
  detail: PipelineResultSummaryResponse | null | undefined,
  issueCount = 0,
) {
  if (!detail) return null;
  return (
    normalizeScoreExplanation(detail.report?.score_explanation) ||
    normalizeScoreExplanation(detail.score_explanation) ||
    buildFallbackScoreExplanation(detail, issueCount)
  );
}
