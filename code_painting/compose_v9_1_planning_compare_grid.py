#!/usr/bin/env python3
"""Compose one four-strategy V9.1 planning comparison."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument(
        "--logic",
        choices=["canonical", "oursv2-5"],
        required=True,
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def probe_duration(path: Path) -> float:
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
    release = (
        args.asset_root
        / "outputs/matched_candidate_image_video_release_20260722"
    )
    run_root = release / "v9_1_planning_runs" / args.logic
    strategies = ("orientation", "fused", "topscore", "oursv2")
    videos = {
        strategy: run_root / strategy / "planner_output/head_cam_plan.mp4"
        for strategy in strategies
    }
    missing = [str(path) for path in videos.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing V9.1 input videos:\n" + "\n".join(missing))

    output_name = f"v9-1_{args.logic}.mp4"
    config_path = release / f"v9-1_{args.logic}_config.json"
    manifest_name = f"v9-1_{args.logic}_manifest.json"
    duration = max(probe_duration(path) for path in videos.values())
    if args.logic == "canonical":
        method = "CANONICAL RTCP"
        group = "RTCP TARGET | 19CM TOOL | CLOSE=0.4"
        note = (
            "Candidate/human-center origin is the RTCP target. "
            "IK applies T_L6URDF_RTCP=Ry(-1.57)@Tx(0.19); "
            "rigid K2 transport preserves RTCP-to-object."
        )
    else:
        method = "OURS V2 + 5CM"
        group = "LEGACY TARGET | EXTRA 5CM | CLOSE=0.4"
        note = (
            "AnyGrasp panes preserve the V8 5cm local-forward candidate offset. "
            "The OursV2 pane adds 5cm to its historical 14cm local +Z retreat "
            "(19cm total); rigid K2 transport preserves EE-to-object."
        )

    config = {
        "schema_version": 1,
        "selected_episode": {
            "task": "pick_diverse_bottles",
            "episode_id": 0,
            "display_name": (
                f"pick_diverse_bottles / id0 / V9.1 {args.logic}"
            ),
            "interaction_keyframes": [38, 78],
            "planning_logic": args.logic,
        },
        "timeline_policy": {
            "target_duration_seconds": duration,
            "short_stream_policy": "Freeze final frame.",
        },
        "evidence_notes": [
            note,
            "Pregrasp retreat is 0.12m and does not change the final grasp target.",
            "Gripper commands are normalized: open=1.0, close=0.4.",
            "No IK-feasible fallback candidate is introduced.",
            "IK misses remain recorded, but do not gate close/action in this visualization-only comparison.",
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
                "duration": duration,
            },
        },
        "tiles": [
            {
                "position": index + 1,
                "type": "video",
                "label": f"{label} | {method}",
                "group": group,
                "accent": accent,
                "input": str(videos[strategy]),
                "start": 0,
                "end": None,
                "offset": 0,
                "speed": 1,
            }
            for index, (strategy, label, accent) in enumerate(
                (
                    ("orientation", "ORIENTATION", "0x7C3AED"),
                    ("fused", "FUSED", "0x2563EB"),
                    ("topscore", "TOP-SCORE", "0xDC2626"),
                    ("oursv2", "OURS V2", "0x047857"),
                )
            )
        ],
    }
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
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
        output = release / output_name
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"],
            check=True,
        )
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
