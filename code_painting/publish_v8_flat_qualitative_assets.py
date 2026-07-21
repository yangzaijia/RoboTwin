#!/usr/bin/env python3
"""Publish the V8 6x2 videos and legacy V3 six-panel images into one flat folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EPISODES = (
    ("handover_bottle", 1),
    ("handover_bottle", 3),
    ("pick_diverse_bottles", 0),
    ("pick_diverse_bottles", 1),
    ("place_bread_basket", 0),
    ("place_bread_basket", 1),
    ("pnp_bread", 7),
    ("pnp_bread", 8),
    ("pnp_tray", 2),
    ("pnp_tray", 3),
    ("stack_cups", 0),
    ("stack_cups", 1),
)

TARGET_OBJECTS = {
    "handover_bottle": {"left": "right_bottle", "right": "right_bottle"},
    "pick_diverse_bottles": {"left": "left_bottle", "right": "right_bottle"},
    "place_bread_basket": {"left": "basket", "right": "bread"},
    "pnp_bread": {"left": "left_bread", "right": "right_bread"},
    "pnp_tray": {"left": "left_dark_red_cup", "right": "right_bottle"},
    "stack_cups": {
        "left": "left_light_pink_cup",
        "right": "right_dark_red_cup",
    },
}

FRAME_RE = re.compile(r"_keyframe_(\d{6})_metadata\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--move-videos", action="store_true")
    parser.add_argument(
        "--robotwin-root", type=Path, default=Path("/home/zaijia001/ssd/RoboTwin")
    )
    parser.add_argument(
        "--asset-root",
        type=Path,
        default=Path("/home/zaijia001/ssd/data/piper/paper_qualitative_assets"),
    )
    parser.add_argument(
        "--source-video-root",
        type=Path,
        default=Path(
            "/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/"
            "v8_physical_axes_raw_batch_6x2_20260721_recomposed"
        ),
    )
    parser.add_argument(
        "--preview-root",
        type=Path,
        default=Path(
            "/home/zaijia001/ssd/RoboTwin/code_painting/"
            "anygrasp_h2o_preview_d435_robot_frame_approach_axis_"
            "v8_physical_axes_raw_batch_6x2_20260720"
        ),
    )
    parser.add_argument(
        "--metadata-root",
        type=Path,
        default=Path(
            "/home/zaijia001/ssd/RoboTwin/code_painting/selection_strategy_compare_v4"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(
            "/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/"
            "v8_6x2_flat_release_20260721"
        ),
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_geometry(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def probe_video(path: Path) -> dict[str, Any]:
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_frames:format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    return json.loads(output)


def raw_episode_root(asset_root: Path, task: str, episode_id: int) -> Path:
    hand_root = asset_root.parent / "hand" / task
    for name in (f"{task}_output", f"{task}_output_old_cam"):
        candidate = hand_root / name / f"foundation_input_{episode_id}"
        if candidate.is_dir():
            return candidate
    return hand_root / f"{task}_output" / f"foundation_input_{episode_id}"


def discover(args: argparse.Namespace) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    for task, episode_id in EPISODES:
        metadata_dir = args.metadata_root / task
        metadata_paths = sorted(metadata_dir.glob(f"id{episode_id}_keyframe_*_metadata.json"))
        frame_records: list[dict[str, Any]] = []
        episode_root = raw_episode_root(args.asset_root, task, episode_id)
        for metadata_path in metadata_paths:
            match = FRAME_RE.search(metadata_path.name)
            if not match:
                continue
            frame = int(match.group(1))
            frame_records.append(
                {
                    "frame": frame,
                    "metadata_path": metadata_path,
                    "raw_grasp_json": episode_root / "grasps" / f"grasp_{frame:06d}.json",
                    "object_debug_json": (
                        args.preview_root
                        / task
                        / f"foundation_input_{episode_id}"
                        / f"frame_{frame:06d}_object_distance_debug.json"
                    ),
                }
            )
        video_path = (
            args.source_video_root
            / task
            / f"id{episode_id}"
            / "candidate_retarget_grid_2x2_physical_axes_raw_v8.mp4"
        )
        episodes.append(
            {
                "task": task,
                "episode_id": episode_id,
                "video_path": video_path,
                "frames": frame_records,
            }
        )
    return episodes


def validate_inputs(episodes: list[dict[str, Any]]) -> None:
    missing: list[str] = []
    for episode in episodes:
        if not episode["video_path"].is_file():
            missing.append(str(episode["video_path"]))
        if not episode["frames"]:
            missing.append(f"metadata frames: {episode['task']}/id{episode['episode_id']}")
        for record in episode["frames"]:
            for key in ("metadata_path", "raw_grasp_json", "object_debug_json"):
                if not record[key].is_file():
                    missing.append(str(record[key]))
    frame_count = sum(len(episode["frames"]) for episode in episodes)
    if len(episodes) != 12 or frame_count != 38:
        missing.append(f"expected 12 episodes/38 frames, got {len(episodes)}/{frame_count}")
    if missing:
        raise FileNotFoundError("missing inputs:\n" + "\n".join(missing))


def exporter_config(
    args: argparse.Namespace,
    episode: dict[str, Any],
    record: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    task = episode["task"]
    return {
        "schema_version": 1,
        "robotwin_root": str(args.robotwin_root),
        "metadata_path": str(record["metadata_path"]),
        "raw_grasp_json": str(record["raw_grasp_json"]),
        "object_debug_json": str(record["object_debug_json"]),
        "output_dir": str(output_dir),
        "publish_contact_sheet": str(output_dir / "unused_publish.png"),
        "backup_contact_sheet": str(output_dir / "unused_backup.png"),
        "camera_cv_axis_mode": "legacy_r1",
        "orientation_metric": "approach_axis",
        "max_orientation_error_deg": 90.0,
        "target_objects": TARGET_OBJECTS[task],
        "weights": {"anygrasp": 0.25, "orientation": 0.75},
        "render": {
            "axis_length_m": 0.045,
            "dense_axis_length_m": 0.025,
            "overlay_axis_length_m": 0.032,
            "global_title_height": 96,
            "contact_columns": 3,
        },
    }


def image_filename(task: str, episode_id: int, index: int, frame: int) -> str:
    return (
        f"{task}_{episode_id}_{index:02d}_keyframe_{frame:06d}_"
        "strategies_2x3_legacy_v3.png"
    )


def video_filename(task: str, episode_id: int) -> str:
    return f"{task}_{episode_id}_00_retarget_2x2_v8.mp4"


def readme_text() -> str:
    return """# V8 6x2 Flat Qualitative Assets

This directory is intentionally flat. Sorting by filename groups one episode's video and keyframe images together.

- `*_00_retarget_2x2_v8.mp4`: V8 physical-axis raw-strategy comparison video.
- `*_keyframe_*_strategies_2x3_legacy_v3.png`: 2-row x 3-column candidate sheet.
- The PNGs intentionally use the previous canonical/V3 orientation-debug semantics requested for this release. They are not relabeled as current Piper physical-axis V8 debug output.
- Videos were moved here. Their former structured paths are symbolic links to these flat files so existing manifests remain valid.

六格图顺序：AnyGrasp dense candidates、Orientation、Fused、Top-score、OursV2、all-method overlay。
"""


def main() -> int:
    args = parse_args()
    args.output_root = args.output_root.expanduser().resolve()
    episodes = discover(args)
    validate_inputs(episodes)
    frame_count = sum(len(episode["frames"]) for episode in episodes)
    print(f"Episodes: {len(episodes)}")
    print(f"Keyframe sheets: {frame_count}")
    print(f"Output: {args.output_root}")
    print(f"Video policy: {'move + source symlink' if args.move_videos else 'hard link'}")
    for episode in episodes:
        print(
            f"  {episode['task']}_{episode['episode_id']}: "
            f"video + {len(episode['frames'])} sheets"
        )
    if args.dry_run:
        print("Dry run complete; no files written.")
        return 0
    if args.output_root.exists():
        raise FileExistsError(f"refusing existing output: {args.output_root}")

    exporter = args.asset_root / "export_keyframe_candidate_comparison_v3.py"
    if not exporter.is_file():
        raise FileNotFoundError(exporter)
    staging_release = args.output_root.with_name(f".{args.output_root.name}.staging")
    if staging_release.exists():
        raise FileExistsError(f"refusing existing staging output: {staging_release}")
    staging_release.mkdir(parents=True)
    image_manifest: list[dict[str, Any]] = []
    moved_videos: list[tuple[Path, Path]] = []
    try:
        with tempfile.TemporaryDirectory(
            prefix="v8_flat_six_panel_", dir=str(args.asset_root)
        ) as temporary:
            temporary_root = Path(temporary)
            for episode in episodes:
                task = episode["task"]
                episode_id = int(episode["episode_id"])
                for index, record in enumerate(episode["frames"], start=1):
                    frame = int(record["frame"])
                    item_root = temporary_root / f"{task}_{episode_id}_{frame:06d}"
                    output_dir = item_root / "rendered"
                    config_path = item_root / "config.json"
                    item_root.mkdir(parents=True)
                    config = exporter_config(args, episode, record, output_dir)
                    config_path.write_text(
                        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    subprocess.run(
                        [sys.executable, str(exporter), "--config", str(config_path)],
                        check=True,
                    )
                    sheet = output_dir / "all_strategies_contact_sheet.png"
                    geometry = png_geometry(sheet)
                    if geometry != (1920, 1152):
                        raise ValueError(f"unexpected six-panel geometry {geometry}: {sheet}")
                    flat_name = image_filename(task, episode_id, index, frame)
                    flat_path = staging_release / flat_name
                    shutil.copy2(sheet, flat_path)
                    image_manifest.append(
                        {
                            "task": task,
                            "episode_id": episode_id,
                            "keyframe": frame,
                            "flat_name": flat_name,
                            "geometry": list(geometry),
                            "sha256": sha256(flat_path),
                            "semantics": "legacy_v3_canonical_approach_axis",
                            "sources": {
                                "metadata": str(record["metadata_path"]),
                                "raw_grasp": str(record["raw_grasp_json"]),
                                "object_debug": str(record["object_debug_json"]),
                            },
                        }
                    )

        args.output_root.parent.mkdir(parents=True, exist_ok=True)
        staging_release.rename(args.output_root)
        video_manifest: list[dict[str, Any]] = []
        for episode in episodes:
            source = episode["video_path"]
            destination = args.output_root / video_filename(
                episode["task"], int(episode["episode_id"])
            )
            if args.move_videos:
                shutil.move(str(source), str(destination))
                source.symlink_to(destination)
                moved_videos.append((source, destination))
                policy = "moved_with_source_symlink"
            else:
                os.link(source, destination)
                policy = "hard_link"
            subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-i", str(destination), "-f", "null", "-"],
                stdin=subprocess.DEVNULL,
                check=True,
            )
            video_manifest.append(
                {
                    "task": episode["task"],
                    "episode_id": int(episode["episode_id"]),
                    "flat_name": destination.name,
                    "former_path": str(source),
                    "former_path_is_symlink": source.is_symlink(),
                    "policy": policy,
                    "sha256": sha256(destination),
                    "probe": probe_video(destination),
                }
            )

        manifest = {
            "schema": "v8_6x2_flat_qualitative_assets.v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_root": str(args.output_root),
            "naming": "{task}_{id}_{order}_{description}.{ext}",
            "episode_count": len(episodes),
            "video_count": len(video_manifest),
            "keyframe_image_count": len(image_manifest),
            "image_layout": "2 rows x 3 columns",
            "image_semantics": "previous canonical/V3 approach-axis debug version",
            "video_semantics": "V8 Piper physical-axis raw-strategy recomposition",
            "videos": video_manifest,
            "images": image_manifest,
        }
        (args.output_root / "flat_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (args.output_root / "README.md").write_text(readme_text(), encoding="utf-8")
    except Exception:
        for source, destination in reversed(moved_videos):
            if source.is_symlink():
                source.unlink()
            if destination.exists():
                shutil.move(str(destination), str(source))
        if staging_release.exists():
            shutil.rmtree(staging_release)
        if args.output_root.exists():
            shutil.rmtree(args.output_root)
        raise

    print(f"Published: {args.output_root}")
    print(f"Videos: {len(video_manifest)}")
    print(f"Six-panel images: {len(image_manifest)}")
    print(f"Manifest: {args.output_root / 'flat_manifest.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
