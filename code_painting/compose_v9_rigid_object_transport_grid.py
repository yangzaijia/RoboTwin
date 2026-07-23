#!/usr/bin/env python3
"""Compose one V9 rigid-object-transport comparison without modifying V8 assets."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--robotwin-root", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--run-tag", default="v9_ee_rigid_object_transport_20260723")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def duration(path: Path) -> float:
    return float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
        ).strip()
    )


def main() -> int:
    args = parse_args()
    planner_root = args.robotwin_root / "code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes"
    videos = {
        strategy: planner_root
        / f"paper_{args.run_tag}_{strategy}"
        / "pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4"
        for strategy in ("orientation", "fused", "topscore")
    }
    videos["oursv2"] = (
        planner_root
        / "L16_de_human_replay_clean_right_cam/pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4"
    )
    missing = [str(path) for path in videos.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing input videos:\n" + "\n".join(missing))
    target_duration = max(duration(path) for path in videos.values())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config_path = args.output_dir / "v9_pick_diverse_bottles_0_05_rigid_object_transport_2x2_config.json"
    output_name = "v9_pick_diverse_bottles_0_05_rigid_object_transport_2x2.mp4"
    manifest_name = "v9_pick_diverse_bottles_0_05_rigid_object_transport_2x2_manifest.json"
    config = {
        "schema_version": 1,
        "selected_episode": {
            "task": "pick_diverse_bottles",
            "episode_id": 0,
            "display_name": "pick_diverse_bottles / id0 / rigid object transport",
            "interaction_keyframes": [38, 78],
        },
        "timeline_policy": {
            "target_duration_seconds": target_duration,
            "short_stream_policy": "Freeze final frame.",
        },
        "evidence_notes": [
            "K1 candidates and physical-axis conversion are unchanged from V8.",
            "After K1 arrival, K2 TCP targets preserve the measured TCP-to-object attachment transform.",
            "The desired object endpoint is the FoundationPose world pose at source frame 78.",
            "OursV2 is the unchanged historical reference.",
        ],
        "output": {
            "fps": 30,
            "codec": "libx264",
            "preset": "medium",
            "crf": 20,
            "font_file": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "manifest_path": manifest_name,
            "grid": {
                "path": output_name,
                "columns": 2,
                "rows": 2,
                "cell_width": 640,
                "cell_height": 398,
                "video_content_height": 360,
                "banner_height": 38,
                "label_layout": "separate",
                "duration": target_duration,
            },
        },
        "tiles": [
            {
                "position": 1,
                "type": "video",
                "label": "ORIENTATION | RIGID TRANSPORT",
                "group": "K1 GRASP KEPT THROUGH K2",
                "accent": "0x7C3AED",
                "input": str(videos["orientation"]),
                "start": 0,
                "end": None,
                "offset": 0,
                "speed": 1,
            },
            {
                "position": 2,
                "type": "video",
                "label": "FUSED | RIGID TRANSPORT",
                "group": "K1 GRASP KEPT THROUGH K2",
                "accent": "0x2563EB",
                "input": str(videos["fused"]),
                "start": 0,
                "end": None,
                "offset": 0,
                "speed": 1,
            },
            {
                "position": 3,
                "type": "video",
                "label": "TOP-SCORE | RIGID TRANSPORT",
                "group": "NO IK-FEASIBLE FALLBACK",
                "accent": "0xDC2626",
                "input": str(videos["topscore"]),
                "start": 0,
                "end": None,
                "offset": 0,
                "speed": 1,
            },
            {
                "position": 4,
                "type": "video",
                "label": "OURS V2 | HISTORICAL",
                "group": "UNCHANGED REFERENCE",
                "accent": "0x047857",
                "input": str(videos["oursv2"]),
                "start": 0,
                "end": None,
                "offset": 0,
                "speed": 1,
            },
        ],
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    command = [
        "python3",
        str(args.asset_root / "compose_pipeline_grid.py"),
        "--config",
        str(config_path),
    ]
    if args.dry_run:
        command.append("--dry-run")
    print(" ".join(command))
    subprocess.run(command, check=True, cwd=args.asset_root)
    if not args.dry_run:
        output_path = args.output_dir / output_name
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(output_path), "-f", "null", "-"], check=True)
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
