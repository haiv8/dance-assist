export type RoleType = "teacher" | "user";
export type RoleQueryType = RoleType | "all";

export interface VideoUploadResponse {
  video_id: string;
  role: RoleType;
  filename: string;
  size_bytes: number;
  url: string;
  meta_url: string;
}

export interface VideoItem {
  video_id: string;
  role: RoleType;
  filename: string;
  url: string;
  uploaded_at: string;
  size_bytes: number;
}

export interface VideoListResponse {
  items: VideoItem[];
}

export interface VideoActionResponse {
  ok: boolean;
  video_id: string;
  message: string;
  item?: VideoItem | null;
}

export type PipelineStatusType = "pending" | "running" | "done" | "failed" | "canceled";

export interface PipelineRunRequest {
  teacher_video_id: string;
  user_video_id: string;
  overwrite?: boolean;
}

export interface PipelineRunResponse {
  pipeline_id: string;
  pair_name: string;
  status: PipelineStatusType;
  message?: string | null;
  queued_at?: string | null;
  updated_at?: string | null;
  executor?: string | null;
  attempt_count?: number | null;
  retry_count?: number | null;
  error_type?: string | null;
  stage?: string | null;
  progress?: number | null;
  cancel_requested?: boolean | null;
  cancel_requested_at?: string | null;
  timeout_sec?: number | null;
  timeout_at?: string | null;
}

export interface PipelineStatusResponse {
  pipeline_id: string;
  pair_name: string;
  status: PipelineStatusType;
  message?: string | null;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
  executor?: string | null;
  attempt_count?: number | null;
  retry_count?: number | null;
  error_type?: string | null;
  stage?: string | null;
  progress?: number | null;
  cancel_requested?: boolean | null;
  cancel_requested_at?: string | null;
  timeout_sec?: number | null;
  timeout_at?: string | null;
}

export interface PipelineActionResponse {
  ok: boolean;
  pipeline_id: string;
  message: string;
}

export interface ScoreExplanation {
  level?: string | null;
  summary?: string | null;
  score_note?: string | null;
  confidence_note?: string | null;
  main_factor?: string | null;
  next_action?: string | null;
}

export interface PipelineResultResponse {
  pipeline_id: string;
  pair_name: string;
  status: PipelineStatusType;
  message?: string | null;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
  executor?: string | null;
  attempt_count?: number | null;
  retry_count?: number | null;
  error_type?: string | null;
  stage?: string | null;
  progress?: number | null;
  cancel_requested?: boolean | null;
  cancel_requested_at?: string | null;
  timeout_sec?: number | null;
  timeout_at?: string | null;
  report?: Record<string, any> | null;
  timeline?: Record<string, any> | null;
  files?: Record<string, string> | null;
  score_explanation?: ScoreExplanation | null;
}

export interface PipelineResultSummaryResponse {
  pipeline_id: string;
  pair_name: string;
  status: PipelineStatusType;
  message?: string | null;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
  executor?: string | null;
  attempt_count?: number | null;
  retry_count?: number | null;
  error_type?: string | null;
  stage?: string | null;
  progress?: number | null;
  cancel_requested?: boolean | null;
  cancel_requested_at?: string | null;
  timeout_sec?: number | null;
  timeout_at?: string | null;
  report?: Record<string, any> | null;
  timeline?: Record<string, any> | null;
  files?: Record<string, string> | null;
  issues?: RecordWorkspaceIssueItem[] | null;
  score_explanation?: ScoreExplanation | null;
}

export interface PipelineFrameDetailResponse {
  pipeline_id: string;
  pair_name: string;
  status: PipelineStatusType;
  frame: number;
  frame_analysis?: Record<string, any> | null;
}

export interface PipelineFrameRangeItem {
  frame: number;
  sec?: number | null;
  frame_analysis?: Record<string, any> | null;
}

export interface PipelineFrameRangeResponse {
  pipeline_id: string;
  pair_name: string;
  status: PipelineStatusType;
  start_frame: number;
  end_frame: number;
  total: number;
  fps_teacher?: number | null;
  items: PipelineFrameRangeItem[];
}


export interface PipelineTaskListItem {
  pipeline_id: string;
  pair_name: string;
  status: PipelineStatusType;
  message?: string | null;
  stage?: string | null;
  progress?: number | null;
  teacher_video_id?: string | null;
  user_video_id?: string | null;
  executor?: string | null;
  attempt_count?: number | null;
  retry_count?: number | null;
  error_type?: string | null;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
  score_total?: number | null;
  confidence_score?: number | null;
  cancel_requested?: boolean | null;
  cancel_requested_at?: string | null;
  timeout_sec?: number | null;
  timeout_at?: string | null;
}

export interface PipelineTaskListResponse {
  items: PipelineTaskListItem[];
  total: number;
  status_filter?: string | null;
  limit: number;
}


export interface AnalysisReportItem {
  pipeline_id: string;
  pair_name?: string | null;
  teacher_video_id?: string | null;
  user_video_id?: string | null;
  status: PipelineStatusType;
  stage?: string | null;
  executor?: string | null;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
  score_total?: number | null;
  score_pose?: number | null;
  score_tempo?: number | null;
  confidence_score?: number | null;
  confidence_level?: string | null;
  score_explanation?: ScoreExplanation | null;
  overall_advice?: string | null;
  confidence_summary?: string | null;
  beginner_summary?: string | null;
  teaching_summary?: string | null;
  top_joints?: any[];
  files?: Record<string, string> | null;
}

export interface AnalysisReportListResponse {
  items: AnalysisReportItem[];
  total: number;
  limit: number;
  query?: string | null;
  min_score?: number | null;
  min_confidence?: number | null;
}

export interface AnalysisReportDetailResponse extends AnalysisReportItem {
  report?: Record<string, any> | null;
}

export type IssueSeverityType = "high" | "medium" | "low";

export interface RecordWorkspaceItem extends PipelineTaskListItem {
  score_pose?: number | null;
  score_tempo?: number | null;
  confidence_level?: string | null;
  overall_advice?: string | null;
  confidence_summary?: string | null;
  beginner_summary?: string | null;
  teaching_summary?: string | null;
  top_joints?: any[];
  files?: Record<string, string> | null;
  has_report: boolean;
  issue_count: number;
}

export interface RecordWorkspaceIssueItem {
  id: string;
  pipeline_id: string;
  pair_name: string;
  teacher_video_id?: string | null;
  user_video_id?: string | null;
  type: string;
  severity: IssueSeverityType;
  sec: number;
  frame?: number | null;
  summary: string;
  action?: string | null;
  finished_at?: string | null;
  score_total?: number | null;
  confidence_score?: number | null;
}

export interface IssueReplayItem {
  id: string;
  pipelineId: string;
  pairName: string;
  teacherVideoId?: string | null;
  userVideoId?: string | null;
  type: string;
  severity: IssueSeverityType;
  sec: number;
  frame?: number | null;
  summary: string;
  action?: string | null;
  finishedAt?: string | null;
  scoreTotal?: number | null;
  confidenceScore?: number | null;
}

export interface RecordWorkspaceResponse {
  items: RecordWorkspaceItem[];
  issues: RecordWorkspaceIssueItem[];
  total: number;
  issue_total: number;
  limit: number;
}

export interface AiCoachPriorityIssue {
  title: string;
  severity: IssueSeverityType;
  time_hint?: string | null;
  reason: string;
  practice_tip: string;
}

export interface AiCoachPracticeStep {
  title: string;
  duration_min: number;
  steps: string[];
  success_criteria: string;
}

export interface AiCoachResponse {
  pipeline_id: string;
  pair_name?: string | null;
  generated_by: "openai" | "aliyun" | "local_fallback";
  model?: string | null;
  summary: string;
  priority_issues: AiCoachPriorityIssue[];
  practice_plan: AiCoachPracticeStep[];
  teacher_notes: string[];
  safety_note?: string | null;
  setup_hint?: string | null;
}

export interface AiProviderStatusResponse {
  provider: string;
  configured: boolean;
  model?: string | null;
  base_url?: string | null;
}


export interface SystemStorageEntry {
  path: string;
  bytes: number;
  megabytes: number;
}

export interface SystemStatusResponse {
  ok: boolean;
  checked_at?: string | null;
  task_store?: string | null;
  pipeline_executor?: string | null;
  app_home?: string | null;
  retain_output_pairs?: number | null;
  output_pair_count?: number | null;
  checks: Record<string, any>;
  paths: Record<string, string>;
  storage: Record<string, SystemStorageEntry>;
}

export interface SystemActionResponse {
  ok: boolean;
  action: string;
  message: string;
  report_count?: number | null;
  affected_count?: number | null;
  freed_bytes?: number | null;
}
