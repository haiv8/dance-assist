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
    summary: item.summary || "状态：总分已生成。操作：结合视频和问题片段判断。反馈：辅助训练复盘。",
    score_note: item.score_note || "状态：总分为辅助指标。操作：查看动作、节奏、流畅度和质量风险。反馈：不等同教师评分。",
    confidence_note: item.confidence_note || "状态：可信度说明跟踪稳定性。操作：低可信时回看视频。反馈：避免误读动作好坏。",
    main_factor: item.main_factor || null,
    next_action: item.next_action || "状态：问题片段已排序。操作：先看高优先级。反馈：再分段练习。",
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

  let summary = "状态：总分已生成。操作：结合动作、节奏、流畅度和质量风险。反馈：形成复盘重点。";
  let mainFactor: ScoreExplanation["main_factor"] = "balanced";
  if (hasLowConfidence) {
    summary = "状态：可信度偏低。操作：先检查拍摄质量并回看视频。反馈：谨慎理解分数。";
    mainFactor = "confidence";
  } else if (Number.isFinite(pose) && Number.isFinite(tempo) && tempo - pose >= 8) {
    summary = "状态：动作空间偏差影响总分。操作：优先修动作。反馈：节奏可作为稳定项。";
    mainFactor = "pose";
  } else if (Number.isFinite(pose) && Number.isFinite(tempo) && pose - tempo >= 8) {
    summary = "状态：节奏偏差影响总分。操作：优先对齐节拍。反馈：动作姿态相对稳定。";
    mainFactor = "tempo";
  }

  return {
    level: null,
    summary,
    score_note: "状态：总分为算法辅助。操作：结合动作、节奏和质量风险。反馈：用于复盘而非主观评分。",
    confidence_note: hasLowConfidence
      ? "状态：可信度较低。操作：检查角度、入镜、光照和遮挡。反馈：再判断分数。"
      : "状态：可信度可用。操作：参考跟踪和对齐稳定性。反馈：不直接代表动作好坏。",
    main_factor: mainFactor,
    next_action: issueCount > 0
      ? "状态：存在问题片段。操作：先看高优先级。反馈：回到视频分段练习。"
      : "状态：暂无明显片段。操作：回看整体视频和重点关节。反馈：确认练习方向。",
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
