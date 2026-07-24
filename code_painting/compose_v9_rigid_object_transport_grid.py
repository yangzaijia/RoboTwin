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
    parser.add_argument("--variant", choices=["v9", "v9p"], default="v9")
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


def make_baseline_compatible(path: Path) -> None:
    temporary = path.with_name(f".{path.stem}.baseline.tmp.mp4")
    if temporary.exists():
        temporary.unlink()
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-y",
                "-i",
                str(path),
                "-an",
                "-c:v",
                "libx264",
                "-profile:v",
                "baseline",
                "-level:v",
                "3.2",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(temporary),
            ],
            check=True,
        )
        probe = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name,profile,pix_fmt",
                    "-of",
                    "json",
                    str(temporary),
                ],
                text=True,
            )
        )
        stream = probe["streams"][0]
        if (
            stream.get("codec_name") != "h264"
            or stream.get("profile") != "Constrained Baseline"
            or stream.get("pix_fmt") != "yuv420p"
        ):
            raise ValueError(f"Unexpected compatibility output: {stream}")
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(temporary),
                "-f",
                "null",
                "-",
            ],
            check=True,
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def refresh_manifest_output_probe(manifest_path: Path, output_path: Path) -> None:
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                (
                    "stream=codec_name,profile,pix_fmt,width,height,"
                    "avg_frame_rate,r_frame_rate,nb_frames:"
                    "format=format_name,duration,size"
                ),
                "-of",
                "json",
                str(output_path),
            ],
            text=True,
        )
    )
    stream = probe["streams"][0]
    container = probe["format"]
    frame_rate = stream["avg_frame_rate"]
    numerator, denominator = (int(value) for value in frame_rate.split("/"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output"]["probe"] = {
        "codec": stream["codec_name"],
        "profile": stream.get("profile"),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "pix_fmt": stream["pix_fmt"],
        "avg_frame_rate": frame_rate,
        "avg_fps": numerator / denominator,
        "r_frame_rate": stream["r_frame_rate"],
        "nb_frames": int(stream["nb_frames"]),
        "duration": float(container["duration"]),
        "container": container["format_name"],
        "size_bytes": int(container["size"]),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
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
    if args.variant == "v9p":
        invalid: list[str] = []
        for strategy in ("orientation", "fused", "topscore"):
            summary_path = videos[strategy].with_name("plan_summary.json")
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if int(summary.get("pure_scene_output", -1)) != 1:
                invalid.append(f"{strategy}: pure_scene_output != 1")
            arm_debugs = summary.get("arm_debugs") or {}
            if any(
                bool(debug.get("debug_visualize_targets"))
                for debug in arm_debugs.values()
                if isinstance(debug, dict)
            ):
                invalid.append(f"{strategy}: target-axis actor remains enabled")
        if invalid:
            raise ValueError(
                "V9p requires clean per-strategy videos:\n" + "\n".join(invalid)
            )
    target_duration = max(duration(path) for path in videos.values())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.variant == "v9p":
        output_stem = (
            "v9p_pick_diverse_bottles_0_05_"
            "rigid_object_transport_clean_2x2"
        )
        display_name = "pick_diverse_bottles / id0 / V9p clean rigid transport"
        method_suffix = "V9P CLEAN"
        first_three_group = "NO TARGET AXES OR DEBUG GRIPPERS"
        extra_notes = [
            "V9p changes rendering only: pure_scene_output=1 and "
            "debug_visualize_targets=0 for the first three panes.",
            "Candidates, IK settings, grasp offsets, and rigid K2 transport "
            "remain identical to V9.",
        ]
    else:
        output_stem = (
            "v9_pick_diverse_bottles_0_05_rigid_object_transport_2x2"
        )
        display_name = "pick_diverse_bottles / id0 / rigid object transport"
        method_suffix = "RIGID TRANSPORT"
        first_three_group = "K1 GRASP KEPT THROUGH K2"
        extra_notes = []
    config_path = args.output_dir / f"{output_stem}_config.json"
    output_name = f"{output_stem}.mp4"
    manifest_name = f"{output_stem}_manifest.json"
    config = {
        "schema_version": 1,
        "selected_episode": {
            "task": "pick_diverse_bottles",
            "episode_id": 0,
            "display_name": display_name,
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
            *extra_notes,
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
                "label": f"ORIENTATION | {method_suffix}",
                "group": first_three_group,
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
                "label": f"FUSED | {method_suffix}",
                "group": first_three_group,
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
                "label": f"TOP-SCORE | {method_suffix}",
                "group": (
                    first_three_group
                    if args.variant == "v9p"
                    else "NO IK-FEASIBLE FALLBACK"
                ),
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
        if args.variant == "v9p":
            make_baseline_compatible(output_path)
        refresh_manifest_output_probe(
            args.output_dir / manifest_name,
            output_path,
        )
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(output_path), "-f", "null", "-"], check=True)
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
