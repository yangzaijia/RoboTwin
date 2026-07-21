#!/usr/bin/env python3
"""Overlay V8 IK targets and measured EE poses, then compose a 2x2 audit video."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.spatial.transform import Rotation as Rotation


METHOD_ORDER = ("orientation", "fused", "top_score")
METHOD_TITLES = {
    "orientation": "ORIENTATION RAW (V8)",
    "fused": "FUSED RAW (V8)",
    "top_score": "TOP-SCORE RAW (V8)",
}
METHOD_ACCENTS = {
    "orientation": "0x7C3AED",
    "fused": "0x2563EB",
    "top_score": "0xDC2626",
}
ARM_COLORS = {"left": (220, 40, 220), "right": (0, 150, 255)}


@dataclass(frozen=True)
class Arrival:
    frame_index: int
    keyframe: int
    stage: str
    status_by_arm: dict[str, dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--episode-id", type=int, required=True)
    parser.add_argument(
        "--method",
        action="append",
        required=True,
        metavar="NAME=PLAN_SUMMARY_JSON",
        help="Repeat for orientation, fused, and top_score.",
    )
    parser.add_argument("--ours-video", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--work-output-dir", type=Path, required=True)
    parser.add_argument("--flat-output-dir", type=Path, required=True)
    parser.add_argument("--arrival-hold-seconds", type=float, default=1.0)
    parser.add_argument("--fovy-deg", type=float, default=90.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def parse_methods(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"invalid --method {value!r}; expected NAME=PATH")
        name, path = value.split("=", 1)
        name = name.strip()
        if name not in METHOD_ORDER:
            raise ValueError(f"invalid method {name!r}; expected one of {METHOD_ORDER}")
        if name in result:
            raise ValueError(f"duplicate method: {name}")
        result[name] = Path(path).expanduser().resolve()
    if tuple(sorted(result)) != tuple(sorted(METHOD_ORDER)):
        raise ValueError(f"expected exactly {METHOD_ORDER}, got {tuple(result)}")
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pose_matrix(pose_world_wxyz: list[float] | np.ndarray) -> np.ndarray:
    pose = np.asarray(pose_world_wxyz, dtype=np.float64).reshape(7)
    quat_wxyz = pose[3:]
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = Rotation.from_quat(
        [quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]]
    ).as_matrix()
    matrix[:3, 3] = pose[:3]
    return matrix


def intrinsic_matrix(width: int, height: int, fovy_deg: float) -> np.ndarray:
    fy = float(height) / (2.0 * math.tan(math.radians(float(fovy_deg)) / 2.0))
    return np.array(
        [[fy, 0.0, width / 2.0], [0.0, fy, height / 2.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


def project_point(
    point_world: np.ndarray,
    camera_pose_world_wxyz: list[float],
    intrinsic: np.ndarray,
) -> tuple[int, int] | None:
    world_to_camera = np.linalg.inv(pose_matrix(camera_pose_world_wxyz))
    point_h = np.ones(4, dtype=np.float64)
    point_h[:3] = np.asarray(point_world, dtype=np.float64).reshape(3)
    point_sapien_entity = world_to_camera @ point_h
    # The metrics stream stores the SAPIEN camera entity pose, not
    # camera.get_model_matrix().  In this renderer the entity convention is
    # local +X forward, +Y left, +Z up.  Convert it explicitly to OpenCV
    # right/down/forward before applying the intrinsic matrix.
    point_cv = np.array(
        [
            -point_sapien_entity[1],
            -point_sapien_entity[2],
            point_sapien_entity[0],
        ]
    )
    if not np.isfinite(point_cv).all() or point_cv[2] <= 1e-6:
        return None
    pixel = intrinsic @ point_cv
    return int(round(pixel[0] / pixel[2])), int(round(pixel[1] / pixel[2]))


def clipped_line(
    image: np.ndarray,
    a: tuple[int, int] | None,
    b: tuple[int, int] | None,
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    if a is None or b is None:
        return
    ok, start, end = cv2.clipLine((0, 0, image.shape[1], image.shape[0]), a, b)
    if ok:
        cv2.line(image, start, end, color, thickness, cv2.LINE_AA)


def put_label(
    image: np.ndarray,
    text: str,
    origin: tuple[int, int],
    color: tuple[int, int, int],
    scale: float = 0.43,
    thickness: int = 1,
) -> None:
    cv2.putText(
        image,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (0, 0, 0),
        thickness + 2,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def draw_frame_legend(
    image: np.ndarray,
    active_by_arm: dict[str, int],
    selected: dict[tuple[int, str], dict[str, Any]],
) -> None:
    candidate_parts = []
    for arm in ("left", "right"):
        frame = active_by_arm.get(arm)
        candidate = None if frame is None else selected.get((frame, arm))
        if candidate is not None:
            candidate_parts.append(f"{arm[0].upper()}#{int(candidate['candidate_idx'])}")
    x0 = max(8, image.shape[1] - 344)
    overlay = image.copy()
    cv2.rectangle(overlay, (x0, 6), (image.shape[1] - 6, 72), (12, 12, 12), -1)
    cv2.addWeighted(overlay, 0.78, image, 0.22, 0, image)
    put_label(
        image,
        "TARGET " + (" / ".join(candidate_parts) if candidate_parts else "inactive")
        + " | L magenta | R orange",
        (x0 + 8, 25),
        (245, 245, 245),
        0.37,
        1,
    )
    put_label(image, "ACTUAL EE = white C-gripper", (x0 + 8, 45), (245, 245, 245), 0.37, 1)
    put_label(
        image,
        "TARGET XYZ: X red forward | Y green open | Z blue normal",
        (x0 + 8, 65),
        (245, 245, 245),
        0.32,
        1,
    )


def draw_gripper(
    image: np.ndarray,
    pose_world_wxyz: list[float],
    camera_pose_world_wxyz: list[float],
    intrinsic: np.ndarray,
    width_m: float,
    depth_m: float,
    color: tuple[int, int, int],
    label: str,
    draw_axes: bool,
    thickness: int,
) -> None:
    pose = pose_matrix(pose_world_wxyz)
    rotation = pose[:3, :3]
    center = pose[:3, 3]
    forward = rotation[:, 0]
    opening = rotation[:, 1]
    normal = rotation[:, 2]
    width_m = float(np.clip(width_m, 0.02, 0.12))
    depth_m = float(np.clip(depth_m, 0.018, 0.08))
    back = center - forward * min(0.02, depth_m * 0.7)
    left_base = center + opening * width_m * 0.5
    right_base = center - opening * width_m * 0.5
    points = {
        "lb": back + opening * width_m * 0.5,
        "rb": back - opening * width_m * 0.5,
        "lc": left_base,
        "rc": right_base,
        "lt": left_base + forward * max(0.025, depth_m),
        "rt": right_base + forward * max(0.025, depth_m),
    }
    projected = {
        name: project_point(point, camera_pose_world_wxyz, intrinsic)
        for name, point in points.items()
    }
    for a, b in (("lb", "rb"), ("lb", "lc"), ("rb", "rc"), ("lc", "lt"), ("rc", "rt")):
        clipped_line(image, projected[a], projected[b], color, thickness)
    center_px = project_point(center, camera_pose_world_wxyz, intrinsic)
    if center_px is not None and 0 <= center_px[0] < image.shape[1] and 0 <= center_px[1] < image.shape[0]:
        cv2.circle(image, center_px, 4, color, -1, cv2.LINE_AA)
        put_label(image, label, (center_px[0] + 6, center_px[1] - 6), color)
    if not draw_axes or center_px is None:
        return
    for vector, axis_color, axis_name in (
        (forward, (0, 0, 255), "X"),
        (opening, (0, 210, 0), "Y"),
        (normal, (255, 0, 0), "Z"),
    ):
        end = project_point(center + vector * 0.07, camera_pose_world_wxyz, intrinsic)
        if end is None:
            continue
        clipped_line(image, center_px, end, axis_color, 3)
        if 0 <= end[0] < image.shape[1] and 0 <= end[1] < image.shape[0]:
            put_label(image, axis_name, (end[0] + 3, end[1] + 3), axis_color, 0.38, 1)


def rotation_error_deg(a: list[float], b: list[float]) -> float:
    ra = pose_matrix(a)[:3, :3]
    rb = pose_matrix(b)[:3, :3]
    return float(math.degrees(Rotation.from_matrix(ra.T @ rb).magnitude()))


def selected_candidate_map(summary: dict[str, Any]) -> dict[tuple[int, str], dict[str, Any]]:
    result: dict[tuple[int, str], dict[str, Any]] = {}
    for arm, records in (summary.get("selected_candidates_by_executed_arm") or {}).items():
        for record in records:
            result[(int(record["source_frame"]), str(arm))] = record
    return result


def stage_status(
    summary: dict[str, Any], stage: str, arms: list[str]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    by_arm = summary.get("stages_by_executed_arm") or {}
    for arm in arms:
        value = (by_arm.get(arm) or {}).get(stage) or {}
        result[arm] = {
            "reached": bool(value.get("reached", False)),
            "pos_err_m": value.get("pos_err_m"),
            "rot_err_deg": value.get("rot_err_deg"),
            "status": value.get("status", "Missing"),
        }
    return result


def find_arrivals(rows: list[dict[str, Any]], summary: dict[str, Any]) -> dict[int, Arrival]:
    arrivals: dict[int, Arrival] = {}
    for index, row in enumerate(rows):
        stage = str(row.get("stage"))
        if stage not in {"grasp", "action"}:
            continue
        next_row = rows[index + 1] if index + 1 < len(rows) else None
        active_by_arm = {str(k): int(v) for k, v in (row.get("active_frame_by_arm") or {}).items()}
        if not active_by_arm:
            continue
        next_key = None if next_row is None else (
            str(next_row.get("stage")),
            {str(k): int(v) for k, v in (next_row.get("active_frame_by_arm") or {}).items()},
        )
        current_key = (stage, active_by_arm)
        if next_key == current_key:
            continue
        keyframes = sorted(set(active_by_arm.values()))
        if len(keyframes) != 1:
            continue
        keyframe = keyframes[0]
        arms = sorted(active_by_arm)
        arrivals[index] = Arrival(
            frame_index=index,
            keyframe=keyframe,
            stage=stage,
            status_by_arm=stage_status(summary, stage, arms),
        )
    return arrivals


def arrival_banner(image: np.ndarray, arrival: Arrival) -> np.ndarray:
    result = image.copy()
    statuses = arrival.status_by_arm
    passed = [bool(value["reached"]) for value in statuses.values()]
    border = (0, 200, 0) if all(passed) else ((0, 170, 255) if any(passed) else (0, 0, 230))
    cv2.rectangle(result, (2, 2), (result.shape[1] - 3, result.shape[0] - 3), border, 8)
    overlay = result.copy()
    cv2.rectangle(overlay, (0, result.shape[0] - 72), (result.shape[1], result.shape[0]), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.82, result, 0.18, 0, result)
    put_label(
        result,
        f"KF{arrival.keyframe} {arrival.stage.upper()} ARRIVAL HOLD",
        (14, result.shape[0] - 45),
        border,
        0.58,
        2,
    )
    parts = []
    for arm in ("left", "right"):
        if arm not in statuses:
            continue
        value = statuses[arm]
        pos = value.get("pos_err_m")
        rot = value.get("rot_err_deg")
        parts.append(
            f"{arm[0].upper()} {'PASS' if value['reached'] else 'FAIL'} "
            f"{float(pos) * 1000.0:.1f}mm/{float(rot):.1f}deg"
            if pos is not None and rot is not None
            else f"{arm[0].upper()} {'PASS' if value['reached'] else 'FAIL'}"
        )
    put_label(result, " | ".join(parts), (14, result.shape[0] - 17), (245, 245, 245), 0.48, 1)
    return result


def render_method(
    method: str,
    summary_path: Path,
    output_path: Path,
    arrival_dir: Path,
    hold_seconds: float,
    fovy_deg: float,
) -> dict[str, Any]:
    summary = load_json(summary_path)
    source = Path(summary["head_video"])
    metrics_path = Path(summary["debug_execution_metrics"])
    rows = [json.loads(line) for line in metrics_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = selected_candidate_map(summary)
    arrivals = find_arrivals(rows, summary)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {source}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_count != len(rows):
        raise ValueError(f"video/metrics frame mismatch for {method}: {frame_count} != {len(rows)}")
    intrinsic = intrinsic_matrix(width, height, fovy_deg)
    hold_frames = max(1, int(round(fps * hold_seconds)))
    arrival_dir.mkdir(parents=True, exist_ok=True)
    arrival_images: dict[int, Path] = {}
    with tempfile.TemporaryDirectory(prefix=f"{method}_pose_overlay_") as tmp:
        intermediate = Path(tmp) / "intermediate.mp4"
        writer = cv2.VideoWriter(
            str(intermediate), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            raise RuntimeError(f"cannot open writer: {intermediate}")
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            row = rows[index]
            camera_pose = row.get("current_head_camera_pose_world_wxyz")
            active_by_arm = {
                str(k): int(v) for k, v in (row.get("active_frame_by_arm") or {}).items()
            }
            if camera_pose is not None:
                for arm in ("left", "right"):
                    arm_metrics = (row.get("arms") or {}).get(arm)
                    active_frame = active_by_arm.get(arm)
                    candidate = None if active_frame is None else selected.get((active_frame, arm))
                    if not arm_metrics or not candidate:
                        continue
                    width_m = float(candidate.get("width_m", 0.08))
                    depth_m = float(candidate.get("depth_m", 0.04))
                    label = f"TGT {arm[0].upper()}#{int(candidate['candidate_idx'])}"
                    draw_gripper(
                        frame,
                        arm_metrics["current_eval_pose_world_wxyz"],
                        camera_pose,
                        intrinsic,
                        width_m,
                        depth_m,
                        (245, 245, 245),
                        f"ACT {arm[0].upper()}",
                        False,
                        3,
                    )
                    draw_gripper(
                        frame,
                        arm_metrics["target_eval_pose_world_wxyz"],
                        camera_pose,
                        intrinsic,
                        width_m,
                        depth_m,
                        ARM_COLORS[arm],
                        label,
                        True,
                        5,
                    )
            draw_frame_legend(frame, active_by_arm, selected)
            writer.write(frame)
            arrival = arrivals.get(index)
            if arrival is not None:
                held = arrival_banner(frame, arrival)
                image_path = arrival_dir / f"{method}_keyframe_{arrival.keyframe:06d}_{arrival.stage}_arrival.png"
                if not cv2.imwrite(str(image_path), held):
                    raise RuntimeError(f"failed to write {image_path}")
                arrival_images[arrival.keyframe] = image_path
                for _ in range(hold_frames):
                    writer.write(held)
            index += 1
        cap.release()
        writer.release()
        if index != frame_count:
            raise ValueError(f"decoded {index}/{frame_count} frames for {method}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(intermediate),
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path),
            ],
            check=True,
        )
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(output_path), "-f", "null", "-"],
        check=True,
    )
    return {
        "method": method,
        "summary_path": str(summary_path),
        "source_video": str(source),
        "metrics_path": str(metrics_path),
        "output_video": str(output_path),
        "source_frames": frame_count,
        "fps": fps,
        "arrival_hold_seconds": hold_seconds,
        "arrivals": [
            {
                "source_frame_index": arrival.frame_index,
                "source_time_seconds": arrival.frame_index / fps,
                "keyframe": arrival.keyframe,
                "stage": arrival.stage,
                "status_by_arm": arrival.status_by_arm,
                "image": str(arrival_images[arrival.keyframe]),
            }
            for arrival in arrivals.values()
        ],
        "selected_candidates": {
            arm: [
                {"frame": int(record["source_frame"]), "candidate": int(record["candidate_idx"])}
                for record in records
            ]
            for arm, records in (summary.get("selected_candidates_by_executed_arm") or {}).items()
        },
        "frame_contract": {
            "input": summary.get("candidate_input_frame_contract"),
            "planner": summary.get("candidate_frame_contract"),
            "remap": summary.get("candidate_orientation_remap_label"),
            "forward_axis": summary.get("approach_axis"),
        },
    }


def add_panel_header(image: np.ndarray, title: str, subtitle: str, color: tuple[int, int, int]) -> np.ndarray:
    image = cv2.resize(image, (640, 480), interpolation=cv2.INTER_AREA)
    panel = np.full((576, 640, 3), 247, dtype=np.uint8)
    panel[96:] = image
    cv2.rectangle(panel, (0, 0), (639, 95), color, 5)
    cv2.putText(panel, title, (16, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.63, (25, 25, 25), 2, cv2.LINE_AA)
    cv2.putText(panel, subtitle, (16, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.49, (50, 50, 50), 1, cv2.LINE_AA)
    return panel


def placeholder_panel(title: str, subtitle: str) -> np.ndarray:
    image = np.full((480, 640, 3), 28, dtype=np.uint8)
    cv2.putText(image, "NOT EXECUTED", (178, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.05, (80, 80, 255), 3, cv2.LINE_AA)
    cv2.putText(image, "No arrival pose is fabricated", (160, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (220, 220, 220), 1, cv2.LINE_AA)
    return add_panel_header(image, title, subtitle, (0, 0, 220))


def compose_arrival_sheet(
    records: dict[str, dict[str, Any]],
    output_path: Path,
) -> None:
    panels: list[np.ndarray] = []
    for keyframe in (38, 78):
        for method in METHOD_ORDER:
            arrivals = {int(x["keyframe"]): x for x in records[method]["arrivals"]}
            arrival = arrivals.get(keyframe)
            title = f"{METHOD_TITLES[method]} | KEYFRAME {keyframe}"
            if arrival is None:
                panels.append(placeholder_panel(title, "Stage absent in the recorded execution"))
                continue
            image = cv2.imread(arrival["image"], cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(arrival["image"])
            status = arrival["status_by_arm"]
            summary = " | ".join(
                f"{arm[0].upper()} {'PASS' if value['reached'] else 'FAIL'}"
                for arm, value in sorted(status.items())
            )
            color = (0, 170, 0) if all(x["reached"] for x in status.values()) else (0, 130, 230)
            panels.append(add_panel_header(image, title, summary, color))
    sheet = cv2.vconcat([cv2.hconcat(panels[:3]), cv2.hconcat(panels[3:])])
    if sheet.shape[:2] != (1152, 1920):
        raise ValueError(f"unexpected arrival sheet shape: {sheet.shape}")
    if not cv2.imwrite(str(output_path), sheet):
        raise RuntimeError(f"failed to write {output_path}")


def compose_grid(
    args: argparse.Namespace,
    records: dict[str, dict[str, Any]],
    method_videos: dict[str, Path],
    output_path: Path,
) -> tuple[Path, Path]:
    duration = float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(args.ours_video)],
            text=True,
        ).strip()
    )
    config_path = args.work_output_dir / "pose_audit_grid_config.json"
    manifest_path = args.work_output_dir / "pose_audit_grid_manifest.json"
    config = {
        "schema_version": 1,
        "selected_episode": {
            "task": args.task,
            "episode_id": args.episode_id,
            "display_name": f"{args.task} / id{args.episode_id} / V8 target-vs-actual pose audit",
            "interaction_keyframes": [38, 78],
        },
        "timeline_policy": {
            "target_duration_seconds": duration,
            "short_stream_policy": "Arrival holds are inserted; final frames freeze to the OursV2 duration.",
        },
        "output": {
            "fps": 30,
            "codec": "libx264",
            "preset": "medium",
            "crf": 18,
            "font_file": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "manifest_path": manifest_path.name,
            "grid": {
                "path": output_path.name,
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
    for position, method in enumerate(METHOD_ORDER, start=1):
        arrivals = records[method]["arrivals"]
        statuses = []
        for arrival in arrivals:
            states = arrival["status_by_arm"]
            statuses.append(
                f"KF{arrival['keyframe']} "
                + "/".join(f"{arm[0].upper()}{'PASS' if value['reached'] else 'FAIL'}" for arm, value in sorted(states.items()))
            )
        config["tiles"].append(
            {
                "position": position,
                "type": "video",
                "label": METHOD_TITLES[method] + " + POSE AUDIT",
                "group": " | ".join(statuses) or "NO ARRIVAL",
                "accent": METHOD_ACCENTS[method],
                "input": str(method_videos[method]),
                "source_path": str(method_videos[method]),
                "start": 0.0,
                "end": None,
                "offset": 0.0,
                "speed": 1.0,
            }
        )
    config["tiles"].append(
        {
            "position": 4,
            "type": "video",
            "label": "OURS V2 (HISTORICAL)",
            "group": "UNCHANGED | NO V8 METRICS OVERLAY",
            "accent": "0x047857",
            "input": str(args.ours_video),
            "source_path": str(args.ours_video),
            "start": 0.0,
            "end": None,
            "offset": 0.0,
            "speed": 1.0,
        }
    )
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run(
        ["python3", str(args.asset_root / "compose_pipeline_grid.py"), "--config", str(config_path)],
        cwd=args.asset_root,
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(output_path), "-f", "null", "-"],
        check=True,
    )
    return config_path, manifest_path


def main() -> int:
    args = parse_args()
    methods = parse_methods(args.method)
    args.ours_video = args.ours_video.expanduser().resolve()
    args.asset_root = args.asset_root.expanduser().resolve()
    args.work_output_dir = args.work_output_dir.expanduser().resolve()
    args.flat_output_dir = args.flat_output_dir.expanduser().resolve()
    for path in (*methods.values(), args.ours_video, args.asset_root / "compose_pipeline_grid.py"):
        if not path.is_file():
            raise FileNotFoundError(path)
    flat_video = args.flat_output_dir / f"{args.task}_{args.episode_id}_00b_retarget_2x2_v8_pose_audit.mp4"
    flat_sheet = args.flat_output_dir / f"{args.task}_{args.episode_id}_03_v8_video_matched_arrivals_2x3.png"
    flat_manifest = args.flat_output_dir / f"{args.task}_{args.episode_id}_pose_audit_manifest.json"
    outputs = (flat_video, flat_sheet, flat_manifest)
    if not args.overwrite and any(path.exists() for path in outputs):
        raise FileExistsError(f"refusing existing outputs: {[str(path) for path in outputs if path.exists()]}")
    print(f"Task: {args.task}/id{args.episode_id}")
    print(f"Methods: {', '.join(METHOD_ORDER)}")
    print(f"Flat video: {flat_video}")
    print(f"Flat arrival sheet: {flat_sheet}")
    if args.dry_run:
        print("Dry run complete; no files written.")
        return 0
    args.work_output_dir.mkdir(parents=True, exist_ok=True)
    args.flat_output_dir.mkdir(parents=True, exist_ok=True)
    arrival_dir = args.work_output_dir / "arrival_frames"
    method_videos: dict[str, Path] = {}
    records: dict[str, dict[str, Any]] = {}
    for method in METHOD_ORDER:
        output = args.work_output_dir / f"{method}_target_actual_pose_overlay.mp4"
        method_videos[method] = output
        records[method] = render_method(
            method,
            methods[method],
            output,
            arrival_dir,
            args.arrival_hold_seconds,
            args.fovy_deg,
        )
    work_sheet = args.work_output_dir / "v8_video_matched_arrivals_2x3.png"
    compose_arrival_sheet(records, work_sheet)
    work_video = args.work_output_dir / flat_video.name
    config_path, compositor_manifest = compose_grid(args, records, method_videos, work_video)
    shutil.copy2(work_video, flat_video)
    shutil.copy2(work_sheet, flat_sheet)
    manifest = {
        "schema": "v8_execution_pose_audit.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": args.task,
        "episode_id": args.episode_id,
        "purpose": "Compare the exact V8 IK target wireframe against the recorded actual EE pose.",
        "axis_contract": {
            "target_local_x": "red, physical gripper forward",
            "target_local_y": "green, gripper opening",
            "target_local_z": "blue, gripper-plane normal",
            "actual_pose": "white C-gripper wireframe",
        },
        "arrival_policy": {
            "hold_seconds": args.arrival_hold_seconds,
            "grasp_stage": "interaction keyframe 38",
            "action_stage": "interaction keyframe 78",
            "missing_stage": "NOT EXECUTED placeholder; never synthesized",
        },
        "flat_outputs": {"video": str(flat_video), "arrival_sheet": str(flat_sheet)},
        "work_outputs": {
            "directory": str(args.work_output_dir),
            "grid_config": str(config_path),
            "grid_manifest": str(compositor_manifest),
        },
        "methods": records,
        "oursv2": {
            "source_video": str(args.ours_video),
            "overlay": "unchanged; this historical source has no matching V8 execution metrics stream",
        },
    }
    flat_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {flat_video}")
    print(f"Wrote: {flat_sheet}")
    print(f"Wrote: {flat_manifest}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}")
        raise SystemExit(1)
