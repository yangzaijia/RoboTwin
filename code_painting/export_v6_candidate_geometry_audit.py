#!/usr/bin/env python3
"""Render V6 AnyGrasp candidate geometry without invoking planning or IK."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np
from scipy.spatial.transform import Rotation


LEFT_COLOR = (180, 0, 180)
RIGHT_COLOR = (0, 140, 255)
PLAN_LEFT_COLOR = (255, 160, 0)
PLAN_RIGHT_COLOR = (0, 210, 210)
OBJECT_COLORS = {"left_bottle": LEFT_COLOR, "right_bottle": RIGHT_COLOR}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pose_rotation(pose_wxyz: Sequence[float]) -> np.ndarray:
    pose = np.asarray(pose_wxyz, dtype=np.float64).reshape(7)
    return Rotation.from_quat([pose[4], pose[5], pose[6], pose[3]]).as_matrix()


def pose_with_position(pose_wxyz: Sequence[float], position: Sequence[float]) -> np.ndarray:
    pose = np.asarray(pose_wxyz, dtype=np.float64).reshape(7).copy()
    pose[:3] = np.asarray(position, dtype=np.float64).reshape(3)
    return pose


def pose_from_position_rotation(position: Sequence[float], rotation: np.ndarray) -> np.ndarray:
    quat_xyzw = Rotation.from_matrix(np.asarray(rotation, dtype=np.float64).reshape(3, 3)).as_quat()
    return np.asarray([*position, quat_xyzw[3], *quat_xyzw[:3]], dtype=np.float64)


def put_text(
    image: np.ndarray,
    text: str,
    xy: tuple[int, int],
    scale: float,
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    cv2.putText(
        image,
        text,
        xy,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def add_header(
    image: np.ndarray,
    title: str,
    subtitle: str,
    note: str,
    accent: tuple[int, int, int],
    header_height: int,
) -> np.ndarray:
    canvas = np.full((header_height + image.shape[0], image.shape[1], 3), 250, dtype=np.uint8)
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1] - 1, header_height - 1), (245, 245, 245), -1)
    cv2.rectangle(canvas, (0, 0), (10, header_height - 1), accent, -1)
    put_text(canvas, title, (22, 27), 0.48, (25, 25, 25), 2)
    put_text(canvas, subtitle, (22, 55), 0.42, (35, 35, 35), 1)
    put_text(canvas, note, (22, 80), 0.34, (65, 65, 65), 1)
    canvas[header_height:, :] = image
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1] - 1, canvas.shape[0] - 1), accent, 2)
    return canvas


def selected_record(summary: Mapping[str, Any], frame: int, arm: str) -> dict[str, Any]:
    rows = [
        row
        for row in summary["selected_candidates_by_executed_arm"][arm]
        if int(row["source_frame"]) == int(frame)
    ]
    if len(rows) != 1:
        raise ValueError(f"Expected one selected record for frame={frame} arm={arm}, found {len(rows)}")
    return dict(rows[0])


def render_pose(
    draw_pose: Any,
    image: np.ndarray,
    pose: Sequence[float],
    head_pose: Sequence[float],
    camera: Mapping[str, Any],
    *,
    arm: str,
    label: str,
    width_m: float,
    depth_m: float,
    forward_axis: str,
    dashed: bool = False,
    axes: bool = True,
    color: tuple[int, int, int] | None = None,
    marker: str = "circle",
    thickness: int = 2,
) -> None:
    draw_pose(
        image,
        np.asarray(pose, dtype=np.float64),
        np.asarray(head_pose, dtype=np.float64),
        camera,
        color=color or (LEFT_COLOR if arm == "left" else RIGHT_COLOR),
        label=label,
        width_m=float(width_m),
        depth_m=float(depth_m),
        axis_length_m=0.045,
        forward_axis=forward_axis,
        dashed=dashed,
        draw_axes=axes,
        line_thickness=thickness,
        marker=marker,
        label_offset=(6, -8 if arm == "left" else 16),
    )


def project_world_point(
    preview_module: Any,
    comparison_module: Any,
    point_world: Sequence[float],
    head_pose: Sequence[float],
    camera: Mapping[str, Any],
) -> tuple[int, int] | None:
    point_cam = preview_module.world_point_to_camera(
        np.asarray(point_world, dtype=np.float64),
        np.asarray(head_pose, dtype=np.float64),
        "legacy_r1",
    )
    return comparison_module.project_point(point_cam, camera)


def draw_anchor_and_line(
    image: np.ndarray,
    preview_module: Any,
    comparison_module: Any,
    anchor: Sequence[float],
    candidate: Sequence[float],
    head_pose: Sequence[float],
    camera: Mapping[str, Any],
    *,
    color: tuple[int, int, int],
    label: str,
) -> None:
    a = project_world_point(preview_module, comparison_module, anchor, head_pose, camera)
    b = project_world_point(preview_module, comparison_module, candidate, head_pose, camera)
    if a is None:
        return
    cv2.drawMarker(image, a, color, cv2.MARKER_CROSS, 18, 2, cv2.LINE_AA)
    put_text(image, f"{label} anchor", (a[0] + 8, a[1] - 8), 0.38, color, 1)
    if b is None:
        return
    cv2.line(image, a, b, color, 2, cv2.LINE_AA)
    distance_cm = 100.0 * float(
        np.linalg.norm(np.asarray(candidate, dtype=np.float64) - np.asarray(anchor, dtype=np.float64))
    )
    midpoint = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
    put_text(image, f"{distance_cm:.1f} cm", midpoint, 0.40, color, 1)


def frame_candidate_pool(
    raw_grasps: Mapping[str, Any],
    metadata: Mapping[str, Any],
    debug: Mapping[str, Any],
    preview_module: Any,
) -> list[dict[str, Any]]:
    source = metadata["frame_columns"][0]
    head_pose = np.asarray(source["head_camera_pose_world_wxyz"], dtype=np.float64)
    object_rows = {int(row["candidate_idx"]): row for row in debug["object_candidates"]}
    pool = []
    for candidate_idx, grasp in enumerate(raw_grasps["grasps"]):
        position, rotation = preview_module.camera_pose_to_world_pose(
            translation_cam=np.asarray(grasp["translation"], dtype=np.float64),
            rotation_cam=np.asarray(grasp["rotation_matrix"], dtype=np.float64),
            camera_pose_world_wxyz=head_pose,
            camera_cv_axis_mode="legacy_r1",
            candidate_post_rot_matrix=np.eye(3),
            candidate_orientation_remap_matrix=np.eye(3),
            candidate_frame_matrix=preview_module.candidate_frame_matrix("anygrasp_raw"),
            candidate_target_local_x_offset_m=0.0,
            candidate_target_local_z_offset_m=0.0,
        )
        pool.append(
            {
                "candidate_idx": candidate_idx,
                "pose": pose_from_position_rotation(position, rotation),
                "score": float(grasp["score"]),
                "width_m": float(grasp.get("width", 0.08)),
                "depth_m": float(grasp.get("depth", 0.04)),
                "nearest_object": str(object_rows[candidate_idx]["nearest_object"]),
            }
        )
    return pool


def render_frame(
    entry: Mapping[str, Any],
    summary: Mapping[str, Any],
    output_root: Path,
    preview_module: Any,
    comparison_module: Any,
    header_height: int,
) -> dict[str, Any]:
    frame = int(entry["frame"])
    metadata = load_json(Path(entry["metadata_path"]))
    raw_grasps = load_json(Path(entry["raw_grasp_json"]))
    debug = load_json(Path(entry["object_debug_json"]))
    source = metadata["frame_columns"][0]
    base_image = cv2.imread(str(source["foundation_image"]), cv2.IMREAD_COLOR)
    if base_image is None:
        raise FileNotFoundError(source["foundation_image"])
    head_pose = np.asarray(source["head_camera_pose_world_wxyz"], dtype=np.float64)
    camera = dict(source["camera_intrinsics"])
    pool = frame_candidate_pool(raw_grasps, metadata, debug, preview_module)
    by_idx = {int(row["candidate_idx"]): row for row in pool}
    records = {arm: selected_record(summary, frame, arm) for arm in ("left", "right")}
    objects = {
        name: np.asarray(position, dtype=np.float64)
        for name, position in debug["object_world_positions"].items()
    }

    panels: list[tuple[str, np.ndarray]] = []

    dense = base_image.copy()
    for row in pool:
        arm = "left" if row["nearest_object"] == "left_bottle" else "right"
        render_pose(
            comparison_module.draw_pose,
            dense,
            row["pose"],
            head_pose,
            camera,
            arm=arm,
            label=f"#{row['candidate_idx']}",
            width_m=row["width_m"],
            depth_m=row["depth_m"],
            forward_axis="local_x",
            axes=False,
            thickness=1,
        )
    panels.append((
        "01_anygrasp_dense_raw.png",
        add_header(
            dense,
            "ANYGRASP DENSE CANDIDATES | RAW NATIVE FRAME",
            f"{len(pool)} raw candidates | magenta=left partition | orange=right partition",
            "Correct raw semantics: red +X approach | green +Y opening | blue +Z normal",
            (90, 90, 90),
            header_height,
        ),
    ))

    selected_raw = base_image.copy()
    for arm, record in records.items():
        idx = int(record["candidate_idx"])
        row = by_idx[idx]
        render_pose(
            comparison_module.draw_pose,
            selected_raw,
            row["pose"],
            head_pose,
            camera,
            arm=arm,
            label=f"{arm[0].upper()} raw #{idx}",
            width_m=record["width_m"],
            depth_m=record["depth_m"],
            forward_axis="local_x",
            marker="square",
            thickness=4,
        )
    panels.append((
        "02_selected_raw_anygrasp.png",
        add_header(
            selected_raw,
            "V6 SELECTED IDS | RAW ANYGRASP POSES",
            " | ".join(f"{arm.upper()} #{int(rec['candidate_idx'])}" for arm, rec in records.items()),
            "Candidate centers and raw axes before robot_replay remap or planner offset",
            (170, 0, 170),
            header_height,
        ),
    ))

    stored = base_image.copy()
    for arm, record in records.items():
        raw_center_stored_rotation = pose_with_position(
            record["raw_pose_world_wxyz"], record["raw_pose_world_wxyz"][:3]
        )
        render_pose(
            comparison_module.draw_pose,
            stored,
            raw_center_stored_rotation,
            head_pose,
            camera,
            arm=arm,
            label=f"{arm[0].upper()} stored #{int(record['candidate_idx'])}",
            width_m=record["width_m"],
            depth_m=record["depth_m"],
            forward_axis="local_x",
            marker="diamond",
            thickness=4,
        )
    panels.append((
        "03_v6_stored_robot_replay.png",
        add_header(
            stored,
            "V6 STORED ROTATION | ROBOT_REPLAY REMAP",
            "Stored rotation is exactly 90 deg from raw AnyGrasp for all selected candidates",
            "Current V6 renders red +X as forward although robot_replay defines blue +Z as approach",
            (0, 100, 220),
            header_height,
        ),
    ))

    target = base_image.copy()
    target_distances: dict[str, float] = {}
    raw_distances: dict[str, float] = {}
    for arm, record in records.items():
        idx = int(record["candidate_idx"])
        raw_position = np.asarray(record["raw_pose_world_wxyz"][:3], dtype=np.float64)
        target_position = np.asarray(record["pose_world_wxyz"][:3], dtype=np.float64)
        object_name = f"{arm}_bottle"
        anchor = objects[object_name]
        raw_distances[arm] = float(np.linalg.norm(raw_position - anchor))
        target_distances[arm] = float(np.linalg.norm(target_position - anchor))
        raw_pose = pose_with_position(record["pose_world_wxyz"], raw_position)
        render_pose(
            comparison_module.draw_pose,
            target,
            raw_pose,
            head_pose,
            camera,
            arm=arm,
            label=f"raw center #{idx}",
            width_m=record["width_m"],
            depth_m=record["depth_m"],
            forward_axis="local_x",
            dashed=True,
            axes=False,
            thickness=2,
        )
        render_pose(
            comparison_module.draw_pose,
            target,
            record["pose_world_wxyz"],
            head_pose,
            camera,
            arm=arm,
            label=f"V6 target #{idx}",
            width_m=record["width_m"],
            depth_m=record["depth_m"],
            forward_axis="local_x",
            color=PLAN_LEFT_COLOR if arm == "left" else PLAN_RIGHT_COLOR,
            marker="triangle",
            thickness=4,
        )
        a = project_world_point(preview_module, comparison_module, raw_position, head_pose, camera)
        b = project_world_point(preview_module, comparison_module, target_position, head_pose, camera)
        if a is not None and b is not None:
            cv2.arrowedLine(target, a, b, (30, 30, 30), 2, cv2.LINE_AA, tipLength=0.18)
    panels.append((
        "04_v6_plan_target_minus_x_5cm.png",
        add_header(
            target,
            "CURRENT V6 PLAN TARGET | -5 CM ALONG STORED RED +X",
            "Dashed=raw center | colored solid=current target | black arrow=applied translation",
            "This offset follows stored +X, not raw AnyGrasp approach after robot_replay remap",
            (0, 160, 210),
            header_height,
        ),
    ))

    distances = base_image.copy()
    for arm, record in records.items():
        object_name = f"{arm}_bottle"
        raw_position = np.asarray(record["raw_pose_world_wxyz"][:3], dtype=np.float64)
        render_pose(
            comparison_module.draw_pose,
            distances,
            pose_with_position(record["pose_world_wxyz"], raw_position),
            head_pose,
            camera,
            arm=arm,
            label=f"{arm[0].upper()} #{int(record['candidate_idx'])}",
            width_m=record["width_m"],
            depth_m=record["depth_m"],
            forward_axis="local_x",
            axes=False,
            thickness=3,
        )
        draw_anchor_and_line(
            distances,
            preview_module,
            comparison_module,
            objects[object_name],
            raw_position,
            head_pose,
            camera,
            color=LEFT_COLOR if arm == "left" else RIGHT_COLOR,
            label=arm.upper(),
        )
    panels.append((
        "05_raw_center_object_anchor_distance.png",
        add_header(
            distances,
            "RAW CANDIDATE CENTER TO OBJECT SPATIAL ANCHOR",
            " | ".join(f"{arm.upper()} {100.0 * value:.1f} cm" for arm, value in raw_distances.items()),
            "Anchor is object pose origin, not nearest object surface; tall-bottle top grasps can be far",
            (120, 60, 160),
            header_height,
        ),
    ))

    overlay = base_image.copy()
    for arm, record in records.items():
        idx = int(record["candidate_idx"])
        raw_pose = by_idx[idx]["pose"]
        render_pose(
            comparison_module.draw_pose,
            overlay,
            raw_pose,
            head_pose,
            camera,
            arm=arm,
            label=f"RAW-{arm[0].upper()}#{idx}",
            width_m=record["width_m"],
            depth_m=record["depth_m"],
            forward_axis="local_x",
            marker="square",
            thickness=4,
        )
        render_pose(
            comparison_module.draw_pose,
            overlay,
            record["pose_world_wxyz"],
            head_pose,
            camera,
            arm=arm,
            label=f"V6-{arm[0].upper()}#{idx}",
            width_m=record["width_m"],
            depth_m=record["depth_m"],
            forward_axis="local_x",
            dashed=True,
            color=PLAN_LEFT_COLOR if arm == "left" else PLAN_RIGHT_COLOR,
            marker="triangle",
            thickness=3,
        )
    panels.append((
        "06_raw_vs_current_v6_overlay.png",
        add_header(
            overlay,
            "OVERLAY | RAW ANYGRASP VS CURRENT V6 TARGET",
            "Solid square=raw native pose | dashed triangle=current V6 target",
            "Different orientation convention (90 deg) plus -5 cm along stored red +X",
            (20, 20, 20),
            header_height,
        ),
    ))

    frame_dir = output_root / f"frame_{frame:06d}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    panel_paths = []
    for filename, panel in panels:
        path = frame_dir / filename
        if not cv2.imwrite(str(path), panel):
            raise RuntimeError(f"Failed to write {path}")
        panel_paths.append(path)
    sheet = cv2.vconcat([cv2.hconcat([panel for _, panel in panels[:3]]), cv2.hconcat([panel for _, panel in panels[3:]])])
    sheet_path = frame_dir / "candidate_geometry_audit_contact_sheet_v6.png"
    if not cv2.imwrite(str(sheet_path), sheet):
        raise RuntimeError(f"Failed to write {sheet_path}")
    return {
        "frame": frame,
        "selected_ids": {arm: int(record["candidate_idx"]) for arm, record in records.items()},
        "raw_center_to_object_anchor_m": raw_distances,
        "current_target_to_object_anchor_m": target_distances,
        "panels": [{"path": str(path), "sha256": sha256(path)} for path in panel_paths],
        "contact_sheet": {
            "path": str(sheet_path),
            "sha256": sha256(sheet_path),
            "shape": list(sheet.shape),
        },
    }


def main() -> int:
    args = parse_args()
    config = load_json(args.config.expanduser().resolve())
    robotwin_root = Path(config["robotwin_root"])
    plan_summary_path = Path(config["plan_summary"])
    output_root = Path(config["output_root"])
    print(f"Config: {args.config.expanduser().resolve()}")
    print(f"Plan summary: {plan_summary_path}")
    print(f"Output: {output_root}")
    print("Frames:", ", ".join(str(int(entry["frame"])) for entry in config["frames"]))
    print("Panels: dense raw, selected raw, V6 stored, V6 target, anchor distances, overlay")
    if args.dry_run:
        for path in [plan_summary_path, *[Path(entry[key]) for entry in config["frames"] for key in ("metadata_path", "raw_grasp_json", "object_debug_json")]]:
            if not path.is_file():
                raise FileNotFoundError(path)
        print("Dry run complete; all source files exist and no outputs were written.")
        return 0
    if output_root.exists() and any(output_root.iterdir()):
        if not args.overwrite:
            raise FileExistsError(f"Refusing non-empty output without --overwrite: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(robotwin_root / "code_painting"))
    import render_anygrasp_ranked_preview as preview_module
    import render_selection_strategy_compare_v4 as comparison_module

    summary = load_json(plan_summary_path)
    frame_records = [
        render_frame(
            entry,
            summary,
            output_root,
            preview_module,
            comparison_module,
            int(config.get("header_height", 96)),
        )
        for entry in config["frames"]
    ]
    manifest = {
        "schema": "piper_anygrasp_v6_candidate_geometry_audit.v1",
        "axis_contract": {
            "anygrasp_raw": "red +X approach; green +Y opening; blue +Z normal",
            "robot_replay": "canonical +Z equals raw AnyGrasp +X approach",
            "current_v6_interpretation": "stored robot_replay rotation rendered/executed with red +X forward",
        },
        "sources": {"config": str(args.config.expanduser().resolve()), "plan_summary": str(plan_summary_path)},
        "frames": frame_records,
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for record in frame_records:
        print(f"Wrote frame {record['frame']}: {record['contact_sheet']['path']}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
