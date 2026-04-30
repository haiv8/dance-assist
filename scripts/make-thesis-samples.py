from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _import_storage_helpers():
    try:
        from app.services.storage import get_video_meta  # type: ignore
    except Exception as exc:  # pragma: no cover - defensive CLI error path
        raise RuntimeError(f"cannot import backend storage helpers: {exc}") from exc
    return get_video_meta


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{stderr}")


def _require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"{name} is not available on PATH")


def _resolve_video_path(*, video_id: str | None, video_path: str | None, role: str) -> Path:
    if video_path:
        path = Path(video_path).expanduser()
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"{role} video path not found: {path}")
        return path

    if video_id:
        get_video_meta = _import_storage_helpers()
        meta = get_video_meta(video_id, role=role)
        path = Path(str(meta.get("path") or "")).resolve()
        if not path.exists():
            raise FileNotFoundError(f"{role} video_id resolved but file is missing: {path}")
        return path

    raise ValueError(f"provide --{role}-video-id or --{role}-path")


def _safe_output_path(output_dir: Path, filename: str, overwrite: bool) -> Path:
    path = output_dir / filename
    if path.exists() and not overwrite:
        raise FileExistsError(f"output already exists, pass --overwrite to replace: {path}")
    return path


def _ffmpeg_copy(src: Path, dst: Path) -> list[str]:
    return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-c", "copy", str(dst)]


def _ffmpeg_variant(src: Path, dst: Path, vf: str, *, extra: list[str] | None = None) -> list[str]:
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
    ]
    if extra:
        cmd.extend(extra)
    cmd.append(str(dst))
    return cmd


def _ffmpeg_trim(src: Path, dst: Path, start_sec: float) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start_sec:.3f}",
        "-i",
        str(src),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(dst),
    ]


def _has_ffmpeg_filter(name: str) -> bool:
    try:
        result = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    except Exception:
        return False
    return result.returncode == 0 and name in (result.stdout or "")


def _make_sample(sample_id: str, sample_type: str, description: str, path: Path, command: list[str]) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "type": sample_type,
        "path": str(path),
        "description": description,
        "ffmpeg_command": command,
        "created_at": _now_iso(),
    }


def generate_samples(args: argparse.Namespace) -> dict[str, Any]:
    _require_tool("ffmpeg")
    _require_tool("ffprobe")

    teacher_path = _resolve_video_path(video_id=args.teacher_video_id, video_path=args.teacher_path, role="teacher")
    user_path = _resolve_video_path(video_id=args.user_video_id, video_path=args.user_path, role="user")

    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = (PROJECT_ROOT / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    samples: list[dict[str, Any]] = []

    variants: list[tuple[str, str, str, list[str], Path]] = []

    teacher_copy = _safe_output_path(output_dir, "thesis_exp_teacher_reference.mp4", args.overwrite)
    variants.append(
        (
            "teacher_reference",
            "teacher_reference",
            "教师示范视频参考拷贝，用于论文实验配对。",
            _ffmpeg_copy(teacher_path, teacher_copy),
            teacher_copy,
        )
    )

    original_path = _safe_output_path(output_dir, "thesis_exp_user_original.mp4", args.overwrite)
    variants.append(
        (
            "user_original",
            "original",
            "学员原始视频拷贝，用作对照样例。",
            _ffmpeg_copy(user_path, original_path),
            original_path,
        )
    )

    slow_path = _safe_output_path(output_dir, "thesis_exp_user_slow_0_8x.mp4", args.overwrite)
    variants.append(
        (
            "user_slow_0_8x",
            "slow_0.8x",
            "学员视频 0.8x 慢速样例，用于观察节奏偏慢对评分的影响。",
            _ffmpeg_variant(user_path, slow_path, "setpts=PTS/0.8"),
            slow_path,
        )
    )

    fast_path = _safe_output_path(output_dir, "thesis_exp_user_fast_1_2x.mp4", args.overwrite)
    variants.append(
        (
            "user_fast_1_2x",
            "fast_1.2x",
            "学员视频 1.2x 快速样例，用于观察节奏偏快对评分的影响。",
            _ffmpeg_variant(user_path, fast_path, "setpts=PTS/1.2"),
            fast_path,
        )
    )

    offset_path = _safe_output_path(output_dir, "thesis_exp_user_offset_trim_2s.mp4", args.overwrite)
    variants.append(
        (
            "user_offset_trim_2s",
            "start_offset",
            "裁剪学员视频前 2 秒，制造起始错位样例。",
            _ffmpeg_trim(user_path, offset_path, 2.0),
            offset_path,
        )
    )

    low_quality_path = _safe_output_path(output_dir, "thesis_exp_user_low_quality_480p.mp4", args.overwrite)
    variants.append(
        (
            "user_low_quality_480p",
            "low_quality",
            "降低学员视频分辨率到 480p 并压缩码率，用于观察可信度变化。",
            _ffmpeg_variant(user_path, low_quality_path, "scale=-2:480", extra=["-b:v", "450k", "-maxrate", "450k", "-bufsize", "900k"]),
            low_quality_path,
        )
    )

    if args.include_blur:
        if not _has_ffmpeg_filter("boxblur"):
            raise RuntimeError("ffmpeg boxblur filter is not available; rerun without --include-blur")
        blur_path = _safe_output_path(output_dir, "thesis_exp_user_blur.mp4", args.overwrite)
        variants.append(
            (
                "user_blur",
                "blur",
                "学员视频模糊样例，用于观察低清晰度输入对可信度的影响。",
                _ffmpeg_variant(user_path, blur_path, "boxblur=2:1"),
                blur_path,
            )
        )

    for sample_id, sample_type, description, command, path in variants:
        _run(command)
        samples.append(_make_sample(sample_id, sample_type, description, path, command))

    manifest = {
        "created_at": _now_iso(),
        "teacher_source": str(teacher_path),
        "user_source": str(user_path),
        "output_dir": str(output_dir),
        "samples": samples,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate controlled thesis experiment samples from an existing teacher/user video pair.",
    )
    parser.add_argument("--teacher-video-id", help="Teacher video_id from the local material library.")
    parser.add_argument("--teacher-path", help="Teacher video path. Overrides --teacher-video-id when provided.")
    parser.add_argument("--user-video-id", help="User video_id from the local material library.")
    parser.add_argument("--user-path", help="User video path. Overrides --user-video-id when provided.")
    parser.add_argument("--output-dir", default=".runtime/thesis_samples", help="Output directory. Default: .runtime/thesis_samples")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing generated files in the output directory.")
    parser.add_argument("--include-blur", action="store_true", help="Also generate a blurred sample if ffmpeg supports boxblur.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (args.teacher_video_id or args.teacher_path) or not (args.user_video_id or args.user_path):
        parser.print_help()
        return 2
    try:
        manifest = generate_samples(args)
    except Exception as exc:
        print(f"sample generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"generated {len(manifest['samples'])} thesis samples")
    print(f"manifest: {manifest['manifest_path']}")
    for sample in manifest["samples"]:
        print(f"- {sample['sample_id']}: {sample['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
