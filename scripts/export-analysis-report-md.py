from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = [PROJECT_ROOT / "outputs", PROJECT_ROOT / ".runtime" / "outputs"]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, fallback: str = "--") -> str:
    if value is None:
        return fallback
    value_text = str(value).strip()
    return value_text if value_text else fallback


def _num(value: Any, digits: int = 2) -> str:
    if isinstance(value, bool):
        return "--"
    try:
        number = float(value)
    except Exception:
        return "--"
    if number != number:
        return "--"
    return f"{number:.{digits}f}"


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value).strip("_") or "unknown"


def _report_paths() -> list[Path]:
    paths: list[Path] = []
    for root in SEARCH_ROOTS:
        if root.exists():
            paths.extend(root.rglob("report.json"))
    return sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True)


def _report_matches_pipeline(report: dict[str, Any], pipeline_id: str, path: Path) -> bool:
    candidates = {
        _text(report.get("pipeline_id"), ""),
        _text(report.get("result_id"), ""),
        _text(report.get("result"), ""),
        path.parent.name,
    }
    return pipeline_id in candidates


def _resolve_report_path(args: argparse.Namespace) -> Path:
    if args.report_path:
        path = Path(args.report_path).expanduser()
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"report path not found: {path}")
        return path

    reports = _report_paths()
    if args.pipeline_id:
        for path in reports:
            try:
                report = _as_dict(_load_json(path))
            except Exception:
                continue
            if _report_matches_pipeline(report, args.pipeline_id, path):
                return path
        raise FileNotFoundError(f"report.json not found for pipeline_id: {args.pipeline_id}")

    if reports:
        return reports[0]
    raise FileNotFoundError("no report.json found under outputs or .runtime/outputs")


def _load_optional_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def _resolve_sidecar_paths(report_path: Path) -> tuple[Path, Path]:
    return report_path.parent / "summary.json", report_path.parent / "issues.json"


def _issues_from_payload(report: dict[str, Any], issues_payload: Any) -> list[dict[str, Any]]:
    if isinstance(issues_payload, list):
        return [item for item in issues_payload if isinstance(item, dict)]
    if isinstance(issues_payload, dict) and isinstance(issues_payload.get("issues"), list):
        return [item for item in issues_payload["issues"] if isinstance(item, dict)]

    markers = _as_list(report.get("markers"))
    issues: list[dict[str, Any]] = []
    for marker in markers:
        if isinstance(marker, dict):
            issues.append(marker)
    return issues


def _severity_key(issue: dict[str, Any]) -> str:
    raw = str(issue.get("severity") or "").strip().lower()
    if raw in {"high", "severe"}:
        return "high"
    if raw in {"medium", "clear"}:
        return "medium"
    if raw in {"low", "mild"}:
        return "low"
    return "unknown"


def _issue_type(issue: dict[str, Any]) -> str:
    return _text(issue.get("type") or issue.get("issue_type"), "unknown")


def _issue_summary(issue: dict[str, Any]) -> str:
    return _text(issue.get("summary") or issue.get("advice") or issue.get("message"), "暂无数据")


def _issue_sec(issue: dict[str, Any]) -> str:
    value = issue.get("sec")
    if value is None:
        value = issue.get("start_sec")
    return _num(value, 2)


def _md_escape(value: Any) -> str:
    return _text(value).replace("|", "\\|").replace("\n", " ")


def _score_value(report: dict[str, Any], summary: dict[str, Any], key: str) -> Any:
    scores = _as_dict(report.get("scores"))
    return scores.get(key) if scores.get(key) is not None else summary.get(key)


def _confidence_score(report: dict[str, Any], summary: dict[str, Any]) -> Any:
    confidence = _as_dict(report.get("confidence"))
    return confidence.get("score") if confidence.get("score") is not None else summary.get("confidence_score")


def _score_explanation(report: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(report.get("score_explanation") or summary.get("score_explanation"))


def _conclusion(report: dict[str, Any], summary: dict[str, Any], issues: list[dict[str, Any]]) -> str:
    confidence = _confidence_score(report, summary)
    confidence_number: float | None
    try:
        confidence_number = float(confidence)
    except Exception:
        confidence_number = None

    issue_count = len(issues)
    total = _score_value(report, summary, "score_total") or report.get("score_0_100") or summary.get("score_total")
    parts = [
        f"本次分析总分为 {_num(total)}，该分数用于离线训练复盘，不能替代教师的现场评价。",
    ]
    if confidence_number is not None and confidence_number < 0.55:
        parts.append("本次结果可信度较低，姿态跟踪或拍摄条件可能影响评分，应优先结合原视频回看判断。")
    elif confidence_number is not None:
        parts.append(f"本次可信度为 {_num(confidence_number)}，可作为结果可靠性的参考。")
    else:
        parts.append("当前报告缺少可信度字段，结论需要结合视频和问题片段谨慎理解。")

    if issue_count >= 5:
        parts.append("问题片段数量较多，建议先处理高优先级片段，再回到完整动作串联。")
    elif issue_count > 0:
        parts.append("报告中已定位到若干问题片段，可作为后续练习和论文实验记录的辅助依据。")
    else:
        parts.append("当前报告未提供明确问题片段，建议检查 report/issue index 是否完整。")

    return "".join(parts)


def _build_markdown(report_path: Path, report: dict[str, Any], summary: dict[str, Any], issues: list[dict[str, Any]], summary_path: Path, issues_path: Path) -> str:
    pipeline_id = _text(summary.get("pipeline_id") or report.get("pipeline_id") or report.get("result_id") or report_path.parent.name)
    pair_name = _text(summary.get("pair_name") or report.get("pair_name") or report.get("pair"))
    explanation = _score_explanation(report, summary)
    performance = _as_dict(report.get("performance") or summary.get("performance"))
    stages = [stage for stage in _as_list(performance.get("stages")) if isinstance(stage, dict)]

    severity_counts = Counter(_severity_key(issue) for issue in issues)
    type_counts = Counter(_issue_type(issue) for issue in issues)
    priority = sorted(
        issues,
        key=lambda item: ({"high": 0, "medium": 1, "low": 2}.get(_severity_key(item), 9), float(item.get("sec") or item.get("start_sec") or 0)),
    )[:5]

    lines = [
        "# 分析结果导出报告",
        "",
        "## 基本信息",
        "",
        "| 字段 | 内容 |",
        "| --- | --- |",
        f"| pipeline_id | {_md_escape(pipeline_id)} |",
        f"| pair_name | {_md_escape(pair_name)} |",
        f"| teacher_video_id | {_md_escape(summary.get('teacher_video_id') or report.get('teacher_video_id'))} |",
        f"| user_video_id | {_md_escape(summary.get('user_video_id') or report.get('user_video_id'))} |",
        f"| finished_at | {_md_escape(summary.get('finished_at') or report.get('finished_at') or report.get('created_at'))} |",
        "",
        "## 评分结果",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 总分 | {_num(_score_value(report, summary, 'score_total') or report.get('score_0_100') or summary.get('score_total'))} |",
        f"| 动作分 | {_num(_score_value(report, summary, 'score_pose'))} |",
        f"| 节奏分 | {_num(_score_value(report, summary, 'score_tempo'))} |",
        f"| 可信度 | {_num(_confidence_score(report, summary))} |",
        "",
        "### 评分解释",
        "",
        f"- 等级：{_text(explanation.get('level'), '暂无数据')}",
        f"- 摘要：{_text(explanation.get('summary'), '暂无数据')}",
        f"- 下一步：{_text(explanation.get('next_action'), '暂无数据')}",
        "",
        "## 问题片段统计",
        "",
        f"- 问题片段总数：{len(issues)}",
        f"- high：{severity_counts.get('high', 0)}",
        f"- medium：{severity_counts.get('medium', 0)}",
        f"- low：{severity_counts.get('low', 0)}",
        "",
        "| 类型 | 数量 |",
        "| --- | ---: |",
    ]
    if type_counts:
        for item_type, count in sorted(type_counts.items()):
            lines.append(f"| {_md_escape(item_type)} | {count} |")
    else:
        lines.append("| 暂无数据 | 0 |")

    lines.extend([
        "",
        "### 前 5 个重点问题片段",
        "",
        "| 时间点 | 优先级 | 类型 | 摘要 |",
        "| ---: | --- | --- | --- |",
    ])
    if priority:
        for issue in priority:
            lines.append(
                f"| {_issue_sec(issue)}s | {_md_escape(_severity_key(issue))} | {_md_escape(_issue_type(issue))} | {_md_escape(_issue_summary(issue))} |"
            )
    else:
        lines.append("| -- | -- | -- | 暂无数据 |")

    lines.extend([
        "",
        "## 性能统计",
        "",
        f"- total_sec：{_num(performance.get('total_sec'))}",
        "",
        "| 阶段 | 耗时（秒） |",
        "| --- | ---: |",
    ])
    if stages:
        for stage in stages:
            lines.append(f"| {_md_escape(stage.get('name'))} | {_num(stage.get('duration_sec'))} |")
    else:
        lines.append("| 暂无数据 | -- |")

    lines.extend([
        "",
        "## 结论",
        "",
        _conclusion(report, summary, issues),
        "",
        "## 原始文件路径",
        "",
        f"- report.json：`{report_path}`",
        f"- summary.json：`{summary_path if summary_path.exists() else '暂无数据'}`",
        f"- issues.json：`{issues_path if issues_path.exists() else '暂无数据'}`",
        "",
    ])
    return "\n".join(lines)


def _default_output_path(pipeline_id: str) -> Path:
    return PROJECT_ROOT / ".runtime" / "exports" / f"analysis_report_{_safe_filename(pipeline_id)}.md"


def export_markdown(args: argparse.Namespace) -> Path:
    report_path = _resolve_report_path(args)
    report = _as_dict(_load_json(report_path))
    summary_path, issues_path = _resolve_sidecar_paths(report_path)
    summary = _as_dict(_load_optional_json(summary_path))
    issues = _issues_from_payload(report, _load_optional_json(issues_path))
    pipeline_id = _text(summary.get("pipeline_id") or report.get("pipeline_id") or report.get("result_id") or report_path.parent.name, "unknown")

    output = Path(args.output).expanduser() if args.output else _default_output_path(pipeline_id)
    if not output.is_absolute():
        output = (PROJECT_ROOT / output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_build_markdown(report_path, report, summary, issues, summary_path, issues_path), encoding="utf-8")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export an existing dance-assist analysis result to Markdown.")
    parser.add_argument("--pipeline-id", help="Pipeline/result id to search under outputs and .runtime/outputs.")
    parser.add_argument("--report-path", help="Direct path to report.json. Takes priority over --pipeline-id.")
    parser.add_argument("--output", help="Output Markdown path. Default: .runtime/exports/analysis_report_<pipeline_id>.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = export_markdown(args)
    except Exception as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    print(f"exported markdown report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
