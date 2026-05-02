from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEARCH_ROOTS = [PROJECT_ROOT / "outputs", PROJECT_ROOT / ".runtime" / "outputs"]
CSV_NAME = "thesis_experiment_summary.csv"
MD_NAME = "thesis_experiment_summary.md"

SUMMARY_FIELDS = [
    "sample_id",
    "sample_type",
    "pipeline_id",
    "pair_name",
    "teacher_video_id",
    "user_video_id",
    "score_total",
    "score_pose",
    "score_tempo",
    "confidence_score",
    "confidence_level",
    "issue_count",
    "high_issue_count",
    "total_sec",
    "slowest_stage",
    "finished_at",
    "note",
]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _num(value: Any, digits: int = 2) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    try:
        number = float(value)
    except Exception:
        return ""
    if number != number:
        return ""
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def _md(value: Any, fallback: str = "暂无数据") -> str:
    text = _text(value, fallback)
    return text.replace("|", "\\|").replace("\n", " ")


def _score_value(report: dict[str, Any], summary: dict[str, Any], key: str) -> Any:
    scores = _as_dict(report.get("scores"))
    for value in (summary.get(key), scores.get(key), report.get(key)):
        if value is not None:
            return value
    if key == "score_total":
        return report.get("score_0_100")
    return None


def _confidence_score(report: dict[str, Any], summary: dict[str, Any]) -> Any:
    confidence = _as_dict(report.get("confidence"))
    for value in (summary.get("confidence_score"), confidence.get("score"), report.get("confidence_score")):
        if value is not None:
            return value
    return None


def _confidence_level(report: dict[str, Any], summary: dict[str, Any]) -> str:
    confidence = _as_dict(report.get("confidence"))
    return _text(summary.get("confidence_level") or confidence.get("level") or report.get("confidence_level"))


def _issues_from_payload(report: dict[str, Any], issues_payload: Any) -> list[dict[str, Any]]:
    if isinstance(issues_payload, list):
        return [item for item in issues_payload if isinstance(item, dict)]
    if isinstance(issues_payload, dict) and isinstance(issues_payload.get("issues"), list):
        return [item for item in issues_payload["issues"] if isinstance(item, dict)]

    issues: list[dict[str, Any]] = []
    for value in (report.get("markers"), _as_dict(report.get("confidence")).get("issues"), report.get("tempo_segments")):
        if isinstance(value, list):
            issues.extend(item for item in value if isinstance(item, dict))
    return issues


def _severity(issue: dict[str, Any]) -> str:
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


def _performance(report: dict[str, Any], summary: dict[str, Any]) -> tuple[str, str]:
    performance = _as_dict(report.get("performance") or summary.get("performance"))
    stages = [stage for stage in _as_list(performance.get("stages")) if isinstance(stage, dict)]
    slowest = ""
    slowest_duration: float | None = None
    for stage in stages:
        try:
            duration = float(stage.get("duration_sec"))
        except Exception:
            continue
        if duration != duration:
            continue
        if slowest_duration is None or duration > slowest_duration:
            slowest_duration = duration
            slowest = _text(stage.get("name"))
    return _num(performance.get("total_sec")), slowest


def _report_paths(search_roots: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for root in search_roots:
        if root.exists():
            paths.extend(root.rglob("report.json"))
    return sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True)


def _pipeline_id(report: dict[str, Any], summary: dict[str, Any], report_path: Path) -> str:
    return _text(summary.get("pipeline_id") or report.get("pipeline_id") or report.get("result_id") or report_path.parent.name)


def _matches_pipeline(report: dict[str, Any], summary: dict[str, Any], report_path: Path, wanted: set[str]) -> bool:
    if not wanted:
        return True
    candidates = {
        _pipeline_id(report, summary, report_path),
        _text(summary.get("pair_name")),
        _text(report.get("pair_name")),
        report_path.parent.name,
    }
    return bool(candidates & wanted)


def _load_manifest(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    manifest_path = Path(path).expanduser()
    if not manifest_path.is_absolute():
        manifest_path = (PROJECT_ROOT / manifest_path).resolve()
    payload = _load_json(manifest_path)
    samples = payload.get("samples") if isinstance(payload, dict) else None
    return [item for item in samples if isinstance(item, dict)] if isinstance(samples, list) else []


def _sample_haystack(row: dict[str, str], report: dict[str, Any] | None = None, summary: dict[str, Any] | None = None) -> str:
    parts: list[str] = [
        str(row.get(key) or "")
        for key in ("pipeline_id", "pair_name", "teacher_video_id", "user_video_id", "note")
    ]
    for payload in (summary or {}, report or {}):
        if not isinstance(payload, dict):
            continue
        for key in (
            "teacher_filename",
            "user_filename",
            "teacher_video",
            "user_video",
            "filename",
            "file_name",
            "source_path",
            "video_path",
        ):
            parts.append(str(payload.get(key) or ""))
        input_quality = _as_dict(payload.get("input_quality"))
        parts.append(str(input_quality.get("summary") or ""))
        for meta_key in ("teacher_meta", "user_meta"):
            meta = _as_dict(input_quality.get(meta_key))
            for key in ("filename", "file_name", "path", "source_path", "video_path"):
                parts.append(str(meta.get(key) or ""))
    return " ".join(parts).lower()


def _infer_from_manifest(
    row: dict[str, str],
    samples: list[dict[str, Any]],
    report: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
) -> tuple[str, str]:
    haystack = _sample_haystack(row, report, summary)
    for sample in samples:
        sample_id = _text(sample.get("sample_id"))
        sample_type = _text(sample.get("type"))
        sample_path = Path(str(sample.get("path") or ""))
        path_stem = sample_path.stem
        path_name = sample_path.name
        tokens = [sample_id, path_stem, path_name]
        for token in tokens:
            token = token.lower().strip()
            if token and token in haystack:
                return sample_id, sample_type
    return "", _infer_sample_type(row, report, summary)


def _infer_sample_type(
    row: dict[str, str],
    report: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
) -> str:
    text = _sample_haystack(row, report, summary)
    if "original" in text:
        return "original"
    if "low_quality" in text or "480p" in text or "blur" in text or "compressed" in text:
        return "low_quality"
    if "slow" in text or "0_8" in text or "0.8" in text or "80pct" in text:
        return "slow"
    if "fast" in text or "1_2" in text or "1.2" in text or "120pct" in text:
        return "fast"
    if "offset" in text or "trim" in text or "delay" in text or "start" in text:
        return "start_offset"
    return "unknown"


def _note(row: dict[str, str], issue_count: int, high_issue_count: int) -> str:
    notes: list[str] = []
    try:
        confidence = float(row.get("confidence_score") or "")
    except Exception:
        confidence = None
    if confidence is not None and confidence < 0.55:
        notes.append("可信度较低")
    if high_issue_count:
        notes.append("存在高优先级问题")
    elif issue_count:
        notes.append("存在可复盘问题片段")
    if row.get("sample_type") in {"slow", "fast", "low_quality", "start_offset"}:
        notes.append("扰动样例，仅用于趋势验证")
    return "；".join(notes)


def collect_rows(search_roots: list[Path], pipeline_ids: list[str] | None = None, manifest: str | None = None) -> list[dict[str, str]]:
    wanted = {item for item in (pipeline_ids or []) if item}
    samples = _load_manifest(manifest)
    rows: list[dict[str, str]] = []

    for report_path in _report_paths(search_roots):
        report = _as_dict(_load_optional_json(report_path))
        summary = _as_dict(_load_optional_json(report_path.parent / "summary.json"))
        if not report:
            continue
        if not _matches_pipeline(report, summary, report_path, wanted):
            continue

        issues = _issues_from_payload(report, _load_optional_json(report_path.parent / "issues.json"))
        severity_counts = Counter(_severity(issue) for issue in issues)
        total_sec, slowest_stage = _performance(report, summary)

        row = {
            "sample_id": "",
            "sample_type": "",
            "pipeline_id": _pipeline_id(report, summary, report_path),
            "pair_name": _text(summary.get("pair_name") or report.get("pair_name") or report_path.parent.name),
            "teacher_video_id": _text(summary.get("teacher_video_id") or report.get("teacher_video_id")),
            "user_video_id": _text(summary.get("user_video_id") or report.get("user_video_id")),
            "score_total": _num(_score_value(report, summary, "score_total")),
            "score_pose": _num(_score_value(report, summary, "score_pose")),
            "score_tempo": _num(_score_value(report, summary, "score_tempo")),
            "confidence_score": _num(_confidence_score(report, summary)),
            "confidence_level": _confidence_level(report, summary),
            "issue_count": str(len(issues)),
            "high_issue_count": str(severity_counts.get("high", 0)),
            "total_sec": total_sec,
            "slowest_stage": slowest_stage,
            "finished_at": _text(summary.get("finished_at") or report.get("finished_at") or report.get("created_at")),
            "note": "",
        }
        sample_id, sample_type = _infer_from_manifest(row, samples, report, summary)
        row["sample_id"] = sample_id
        row["sample_type"] = sample_type
        row["note"] = _note(row, len(issues), severity_counts.get("high", 0))
        rows.append(row)

    rows.sort(key=lambda item: item.get("finished_at") or item.get("pipeline_id") or "", reverse=True)
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text("\ufeff" + output.getvalue(), encoding="utf-8")


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md(value) for value in row) + " |")
    return lines


def _analysis(rows: list[dict[str, str]]) -> str:
    parts = [
        f"本次共汇总 {len(rows)} 条已有 pipeline 结果，数据来自已生成的 report、summary 和 issues 文件，未重新运行算法。",
    ]
    if len(rows) < 5:
        parts.append("样例数量仍然较少，结果更适合用于说明系统输出结构和趋势观察，不能作为充分统计结论。")
    low_confidence_count = 0
    for row in rows:
        try:
            confidence = float(row.get("confidence_score") or "")
        except Exception:
            continue
        if confidence < 0.55:
            low_confidence_count += 1
    if low_confidence_count:
        parts.append(f"其中 {low_confidence_count} 条结果可信度较低，相关分数需要结合视频回看和拍摄质量谨慎解释。")
    sample_types = {row.get("sample_type") for row in rows}
    if sample_types & {"slow", "fast", "low_quality", "start_offset"}:
        parts.append("变速、低质量和起始错位样例主要用于验证评分、可信度和问题片段数量的变化趋势，不代表真实练习水平分布。")
    parts.append("论文撰写时建议同时报告总分、可信度和问题片段数量，避免只用单一分数评价练习效果。")
    return "".join(parts)


def _write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    issue_count_by_sample_type: Counter[str] = Counter()
    severity_totals = Counter()
    for row in rows:
        severity_totals["issues"] += int(row.get("issue_count") or 0)
        severity_totals["high"] += int(row.get("high_issue_count") or 0)
        sample_type = row.get("sample_type") or "unknown"
        issue_count_by_sample_type[sample_type] += int(row.get("issue_count") or 0)

    lines = [
        "# 论文实验结果汇总",
        "",
        "## 实验结果汇总表",
        "",
        *_markdown_table(
            ["样例", "类型", "pipeline_id", "总分", "动作分", "节奏分", "可信度", "问题数", "备注"],
            [
                [
                    row.get("sample_id"),
                    row.get("sample_type"),
                    row.get("pipeline_id"),
                    row.get("score_total"),
                    row.get("score_pose"),
                    row.get("score_tempo"),
                    row.get("confidence_score"),
                    row.get("issue_count"),
                    row.get("note"),
                ]
                for row in rows
            ],
        ),
        "",
        "## 性能统计表",
        "",
        *_markdown_table(
            ["pipeline_id", "total_sec", "slowest_stage", "finished_at"],
            [[row.get("pipeline_id"), row.get("total_sec"), row.get("slowest_stage"), row.get("finished_at")] for row in rows],
        ),
        "",
        "## 问题片段统计表",
        "",
        *_markdown_table(
            ["样例类型", "问题片段总数", "高优先级数量"],
            [[sample_type, issue_count, sum(int(row.get("high_issue_count") or 0) for row in rows if (row.get("sample_type") or "unknown") == sample_type)] for sample_type, issue_count in sorted(issue_count_by_sample_type.items())],
        ),
        "",
        "## 保守分析",
        "",
        _analysis(rows),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def export_summary(args: argparse.Namespace) -> tuple[Path, Path]:
    search_roots = [Path(args.outputs_dir).expanduser()] if args.outputs_dir else DEFAULT_SEARCH_ROOTS
    search_roots = [(PROJECT_ROOT / root).resolve() if not root.is_absolute() else root.resolve() for root in search_roots]
    rows = collect_rows(search_roots, pipeline_ids=args.pipeline_id, manifest=args.manifest)
    if not rows:
        searched = ", ".join(str(root) for root in search_roots)
        raise FileNotFoundError(f"no pipeline report results found under: {searched}")

    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = (PROJECT_ROOT / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / CSV_NAME
    md_path = output_dir / MD_NAME
    _write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return csv_path, md_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize existing dance-assist pipeline results for thesis experiments.")
    parser.add_argument("--outputs-dir", help="Directory containing pipeline output folders. Default: search outputs and .runtime/outputs.")
    parser.add_argument("--pipeline-id", action="append", help="Pipeline id to include. Can be repeated.")
    parser.add_argument("--manifest", help="Optional thesis_samples/manifest.json for sample labels.")
    parser.add_argument("--output-dir", default=".runtime/exports", help="Output directory. Default: .runtime/exports")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        csv_path, md_path = export_summary(args)
    except Exception as exc:
        print(f"thesis summary export failed: {exc}", file=sys.stderr)
        return 1
    print(f"csv summary: {csv_path}")
    print(f"markdown summary: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
