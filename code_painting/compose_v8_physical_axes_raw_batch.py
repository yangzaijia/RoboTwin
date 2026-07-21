#!/usr/bin/env python3
"""Compose one native-speed V8 raw-strategy comparison and write audit metadata."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--episode-id", required=True, type=int)
    parser.add_argument("--orientation-root", required=True, type=Path)
    parser.add_argument("--fused-root", required=True, type=Path)
    parser.add_argument("--topscore-root", required=True, type=Path)
    parser.add_argument("--ours-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--asset-root", required=True, type=Path)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def probe_duration(path: Path) -> float | None:
    if not path.is_file():
        return None
    output = subprocess.check_output(
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
    return float(output)


def selected_ids(summary: dict[str, Any] | None) -> dict[str, list[dict[str, int]]]:
    result: dict[str, list[dict[str, int]]] = {}
    if not summary:
        return result
    for arm, rows in (summary.get("selected_candidates_by_executed_arm") or {}).items():
        result[str(arm)] = [
            {"frame": int(row.get("source_frame", -1)), "candidate": int(row.get("candidate_idx", -1))}
            for row in rows
        ]
    return result


def stage_status(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {"available": False, "execution_success": False, "failure_count": None, "stages": {}}
    stages: dict[str, Any] = {}
    for stage, value in (summary.get("stages") or {}).items():
        arms = ((value.get("attempt_history") or [{}])[-1].get("arms") or {})
        stages[str(stage)] = {
            "reached": bool(value.get("reached", False)),
            "arms": {
                str(arm): {
                    "reached": bool(record.get("reached", False)),
                    "position_error_m": record.get("pos_err_m"),
                    "rotation_error_deg": record.get("rot_err_deg"),
                }
                for arm, record in arms.items()
            },
        }
    return {
        "available": True,
        "execution_success": bool(summary.get("execution_success", False)),
        "execution_failed": bool(summary.get("execution_failed", False)),
        "failure_count": len(summary.get("failed_stage_records") or []),
        "reach_rotation_tolerance_deg": summary.get("reach_rot_tol_deg"),
        "execute_partial_cartesian_plan": summary.get("execute_partial_cartesian_plan"),
        "stages": stages,
    }


def method_record(name: str, root: Path, task: str, episode_id: int) -> dict[str, Any]:
    episode_dir = root / task / f"foundation_input_{episode_id}"
    summary_path = episode_dir / "plan_summary.json"
    video_path = episode_dir / "head_cam_plan.mp4"
    summary = read_json(summary_path)
    return {
        "name": name,
        "root": str(root),
        "episode_dir": str(episode_dir),
        "summary_path": str(summary_path),
        "video_path": str(video_path),
        "video_available": video_path.is_file(),
        "duration_seconds": probe_duration(video_path),
        "selected_candidates": selected_ids(summary),
        "status": stage_status(summary),
    }


def compact_status(method: dict[str, Any]) -> str:
    if not method["video_available"]:
        return "MISSING"
    status = method["status"]
    failures = status.get("failure_count")
    if not status.get("execution_failed"):
        return "STRICT PASS"
    action_reached = bool((status.get("stages") or {}).get("action", {}).get("reached", False))
    suffix = "ACTION REACHED" if action_reached else "ACTION NOT REACHED"
    return f"FAILURES {failures} | {suffix}"


def candidate_text(method: dict[str, Any]) -> str:
    arms = method.get("selected_candidates") or {}
    parts = []
    for arm in ("left", "right"):
        rows = arms.get(arm, [])
        short = ", ".join(f"f{x['frame']}#{x['candidate']}" for x in rows)
        parts.append(f"{arm.upper()}: {short or 'MISSING'}")
    return " | ".join(parts)


def make_tile(position: int, label: str, group: str, accent: str, video_path: str) -> dict[str, Any]:
    return {
        "position": position,
        "type": "video",
        "label": label,
        "group": group,
        "accent": accent,
        "input": video_path,
        "source_path": video_path,
        "start": 0.0,
        "end": None,
        "offset": 0.0,
        "speed": 1.0,
    }


def main() -> int:
    args = parse_args()
    records = [
        method_record("orientation", args.orientation_root, args.task, args.episode_id),
        method_record("fused", args.fused_root, args.task, args.episode_id),
        method_record("top_score", args.topscore_root, args.task, args.episode_id),
        method_record("oursv2_historical", args.ours_root, args.task, args.episode_id),
    ]
    missing = [record["name"] for record in records if not record["video_available"]]
    if missing and not args.allow_missing:
        raise FileNotFoundError(f"missing videos: {missing}")
    durations = [float(record["duration_seconds"]) for record in records if record["duration_seconds"] is not None]
    if not durations:
        raise RuntimeError("no video source is available")
    ours_duration = records[3]["duration_seconds"]
    target_duration = float(ours_duration if ours_duration is not None else max(durations))

    episode_dir = args.output_root / args.task / f"id{args.episode_id}"
    episode_dir.mkdir(parents=True, exist_ok=True)
    config_path = episode_dir / "candidate_retarget_grid_2x2_physical_axes_raw_v8_config.json"
    output_name = "candidate_retarget_grid_2x2_physical_axes_raw_v8.mp4"
    manifest_name = "candidate_retarget_grid_2x2_physical_axes_raw_v8_manifest.json"
    keyframes = sorted(
        {
            row["frame"]
            for record in records[:3]
            for rows in record.get("selected_candidates", {}).values()
            for row in rows
            if row["frame"] >= 0
        }
    )
    evidence = [
        "V8 converts robot_replay canonical +Z approach to physical Piper +X before URDFIK and retains the independent Curobo-to-SAPIEN link6 adapter.",
        "No IK-feasible reranking, replacement, or fallback is used; failures and early stops are preserved.",
        "All streams retain native speed and freeze their final frame to the historical OursV2 duration.",
    ]
    evidence.extend(f"{record['name']}: {candidate_text(record)}; {compact_status(record)}" for record in records[:3])
    evidence.append(
        f"oursv2_historical: reach tolerance={records[3]['status'].get('reach_rotation_tolerance_deg')} deg; unchanged reference."
    )
    config = {
        "schema_version": 1,
        "selected_episode": {
            "task": args.task,
            "episode_id": args.episode_id,
            "display_name": f"{args.task} / id{args.episode_id} / V8 physical-axis raw strategies",
            "interaction_keyframes": keyframes,
        },
        "timeline_policy": {
            "target_duration_seconds": target_duration,
            "method_pairs": "Native-speed raw-strategy executions against unchanged historical OursV2.",
            "short_stream_policy": "Freeze the final frame; never stretch or synthesize continuation.",
        },
        "evidence_notes": evidence,
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
            make_tile(1, "ORIENTATION RAW (V8)", compact_status(records[0]), "0x7C3AED", records[0]["video_path"]),
            make_tile(2, "FUSED RAW (V8)", compact_status(records[1]), "0x2563EB", records[1]["video_path"]),
            make_tile(3, "TOP-SCORE RAW (V8)", compact_status(records[2]), "0xDC2626", records[2]["video_path"]),
            make_tile(
                4,
                "OURS V2 (HISTORICAL)",
                f"REACH TOL {records[3]['status'].get('reach_rotation_tolerance_deg')} DEG | UNCHANGED",
                "0x047857",
                records[3]["video_path"],
            ),
        ],
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    compositor = args.asset_root / "compose_pipeline_grid.py"
    command = ["python3", str(compositor), "--config", str(config_path)]
    if args.allow_missing:
        command.append("--allow-missing")
    if args.dry_run:
        command.append("--dry-run")
    subprocess.run(command, check=True, cwd=args.asset_root)
    if args.dry_run:
        return 0

    output_path = episode_dir / output_name
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(output_path), "-f", "null", "-"], check=True)
    status = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": args.task,
        "episode_id": args.episode_id,
        "target_duration_seconds": target_duration,
        "output_video": str(output_path),
        "config_path": str(config_path),
        "manifest_path": str(episode_dir / manifest_name),
        "complete_decode": True,
        "methods": records,
    }
    status_path = episode_dir / "execution_status_v8.json"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote status: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
