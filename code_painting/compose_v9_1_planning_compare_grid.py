#!/usr/bin/env python3
"""Compose one four-strategy V9.1/V9.2 planning comparison."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from compose_v9_rigid_object_transport_grid import (
    make_baseline_compatible,
    refresh_manifest_output_probe,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument(
        "--logic",
        choices=["canonical", "oursv2-5", "canonical17"],
        required=True,
    )
    parser.add_argument("--pure-scene", action="store_true")
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
    if args.pure_scene:
        if args.logic == "canonical":
            raise ValueError(
                "Pure release is defined for oursv2-5 and canonical17"
            )
        run_roots = {
            "oursv2-5": (
                release
                / "v9p_planning_runs_oursv2_close03_pure/oursv2-5"
            ),
            "canonical17": (
                release
                / "v9p_planning_runs_canonical17_close03_pure/canonical17"
            ),
        }
    else:
        run_roots = {
            "canonical": release / "v9_1_planning_runs_close03/canonical",
            "oursv2-5": (
                release
                / "v9_1_planning_runs_close03_grasp_retreat05/oursv2-5"
            ),
            "canonical17": (
                release
                / "v9_2_planning_runs_canonical17_close03/canonical17"
            ),
        }
    run_root = run_roots[args.logic]
    strategies = ("orientation", "fused", "topscore", "oursv2")
    videos = {
        strategy: run_root / strategy / "planner_output/head_cam_plan.mp4"
        for strategy in strategies
    }
    missing = [str(path) for path in videos.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing V9.1/V9.2 input videos:\n" + "\n".join(missing)
        )
    if args.pure_scene:
        invalid: list[str] = []
        for strategy in strategies:
            summary = json.loads(
                (
                    run_root
                    / strategy
                    / "planner_output/plan_summary.json"
                ).read_text(encoding="utf-8")
            )
            command_text = (
                run_root / strategy / "command.sh.txt"
            ).read_text(encoding="utf-8")
            if int(summary.get("pure_scene_output", -1)) != 1:
                invalid.append(f"{strategy}: pure_scene_output != 1")
            if "--debug_visualize_targets 0" not in command_text:
                invalid.append(f"{strategy}: debug targets not disabled")
            if "--close_gripper 0.3" not in command_text:
                invalid.append(f"{strategy}: close_gripper != 0.3")
        if invalid:
            raise ValueError(
                "Invalid close=0.3 V9p inputs:\n" + "\n".join(invalid)
            )

    if args.pure_scene:
        output_stems = {
            "oursv2-5": "v9p_oursv2",
            "canonical17": "v9p_canonical",
        }
    else:
        output_stems = {
            "canonical": "v9-1_canonical",
            "oursv2-5": "v9-1_oursv2-5",
            "canonical17": "v9-2_canonical",
        }
    output_stem = output_stems[args.logic]
    output_name = f"{output_stem}.mp4"
    config_path = release / f"{output_stem}_config.json"
    manifest_name = f"{output_stem}_manifest.json"
    duration = max(probe_duration(path) for path in videos.values())
    if args.logic == "canonical":
        method = "CANONICAL RTCP"
        group = "RTCP TARGET | 19CM TOOL | CLOSE=0.3"
        note = (
            "Candidate/human-center origin is the RTCP target. "
            "IK applies T_L6URDF_RTCP=Ry(-1.57)@Tx(0.19); "
            "rigid K2 transport preserves RTCP-to-object."
        )
    elif args.logic == "canonical17":
        method = (
            "CANONICAL-17CM CLEAN"
            if args.pure_scene
            else "CANONICAL-17CM"
        )
        group = (
            "NO TARGET AXES | CLOSE=0.3"
            if args.pure_scene
            else "RTCP TARGET | CLOSE=0.3"
        )
        note = (
            "Candidate/human-center origin is the unchanged RTCP target. "
            "This isolated V9.2 run applies "
            "T_L6URDF_RTCP=Ry(-1.57)@Tx(0.17); "
            "the default Canonical-v1 0.19m server literal is unchanged."
        )
    else:
        method = (
            "V9 -5CM CLEAN" if args.pure_scene else "V9 GRASP - 5CM"
        )
        group = (
            "NO TARGET AXES | CLOSE=0.3"
            if args.pure_scene
            else "V9 TARGET - 5CM | CLOSE=0.3"
        )
        note = (
            "Orientation/Fused/Top-score add another 5cm retreat to the V9/V8 "
            "grasp target (10cm total from the raw candidate center). "
            "The OursV2 pane restores its unchanged historical 14cm target."
        )

    config = {
        "schema_version": 1,
        "selected_episode": {
            "task": "pick_diverse_bottles",
            "episode_id": 0,
            "display_name": (
                "pick_diverse_bottles / id0 / "
                + (
                    f"V9p {args.logic} clean close=0.3"
                    if args.pure_scene
                    else (
                        "V9.2 canonical17"
                        if args.logic == "canonical17"
                        else f"V9.1 {args.logic}"
                    )
                )
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
            "Gripper commands are normalized: open=1.0, close=0.3.",
            "No IK-feasible fallback candidate is introduced.",
            "IK misses remain recorded, but do not gate close/action in this visualization-only comparison.",
            *(
                [
                    "Pure-scene changes rendering only: no target axes or "
                    "debug grippers in any pane."
                ]
                if args.pure_scene
                else []
            ),
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
        "tiles": [],
    }
    for index, (strategy, label, accent) in enumerate(
        (
            ("orientation", "ORIENTATION", "0x7C3AED"),
            ("fused", "FUSED", "0x2563EB"),
            ("topscore", "TOP-SCORE", "0xDC2626"),
            ("oursv2", "OURS V2", "0x047857"),
        )
    ):
        tile_method = method
        tile_group = group
        if args.logic == "oursv2-5" and strategy == "oursv2":
            tile_method = (
                "V9 REFERENCE CLEAN"
                if args.pure_scene
                else "V9 REFERENCE"
            )
            tile_group = (
                "NO TARGET AXES | CLOSE=0.3"
                if args.pure_scene
                else "HISTORICAL 14CM | UNCHANGED | CLOSE=0.3"
            )
        config["tiles"].append(
            {
                "position": index + 1,
                "type": "video",
                "label": f"{label} | {tile_method}",
                "group": tile_group,
                "accent": accent,
                "input": str(videos[strategy]),
                "start": 0,
                "end": None,
                "offset": 0,
                "speed": 1,
            }
        )
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
        if args.pure_scene:
            make_baseline_compatible(output)
        refresh_manifest_output_probe(release / manifest_name, output)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"],
            check=True,
        )
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
