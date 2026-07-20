#!/usr/bin/env python3
"""Render a six-panel audit for the verified AnyGrasp -> robot_replay -> Piper chain."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def axis_angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).reshape(3)
    b = np.asarray(b, dtype=np.float64).reshape(3)
    dot = float(np.clip(np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-12), -1.0, 1.0))
    return float(np.rad2deg(np.arccos(dot)))


def render_frame(
    entry: Mapping[str, Any],
    summary: Mapping[str, Any],
    output_root: Path,
    preview: Any,
    compare: Any,
    common: Any,
    header_height: int,
) -> dict[str, Any]:
    frame = int(entry["frame"])
    metadata = common.load_json(Path(entry["metadata_path"]))
    raw_grasps = common.load_json(Path(entry["raw_grasp_json"]))
    debug = common.load_json(Path(entry["object_debug_json"]))
    source = metadata["frame_columns"][0]
    base_image = cv2.imread(str(source["foundation_image"]), cv2.IMREAD_COLOR)
    if base_image is None:
        raise FileNotFoundError(source["foundation_image"])
    head_pose = np.asarray(source["head_camera_pose_world_wxyz"], dtype=np.float64)
    camera = dict(source["camera_intrinsics"])
    pool = common.frame_candidate_pool(raw_grasps, metadata, debug, preview)
    by_idx = {int(row["candidate_idx"]): row for row in pool}
    records = {arm: common.selected_record(summary, frame, arm) for arm in ("left", "right")}
    objects = {
        name: np.asarray(position, dtype=np.float64)
        for name, position in debug["object_world_positions"].items()
    }

    physical_equivalence: dict[str, dict[str, float]] = {}
    for arm, record in records.items():
        raw_rot = common.pose_rotation(by_idx[int(record["candidate_idx"])]["pose"])
        canonical_rot = common.pose_rotation(record["raw_pose_world_wxyz"])
        physical_equivalence[arm] = {
            "raw_plus_x_vs_canonical_plus_z_deg": axis_angle_deg(raw_rot[:, 0], canonical_rot[:, 2]),
            "raw_plus_y_vs_canonical_plus_y_deg": axis_angle_deg(raw_rot[:, 1], canonical_rot[:, 1]),
            "raw_plus_z_vs_canonical_minus_x_deg": axis_angle_deg(raw_rot[:, 2], -canonical_rot[:, 0]),
        }

    panels: list[tuple[str, np.ndarray]] = []

    dense = base_image.copy()
    for row in pool:
        arm = "left" if row["nearest_object"] == "left_bottle" else "right"
        common.render_pose(
            compare.draw_pose, dense, row["pose"], head_pose, camera,
            arm=arm, label=f"#{row['candidate_idx']}", width_m=row["width_m"],
            depth_m=row["depth_m"], forward_axis="local_x", axes=False, thickness=1,
        )
    panels.append((
        "01_anygrasp_dense_raw.png",
        common.add_header(
            dense,
            "1 | ALL ANYGRASP CANDIDATES (RAW)",
            f"{len(pool)} candidates | raw actor uses +X forward",
            "Red +X approach | green +Y opening | blue +Z plane normal",
            (90, 90, 90), header_height,
        ),
    ))

    selected_raw = base_image.copy()
    for arm, record in records.items():
        idx = int(record["candidate_idx"])
        row = by_idx[idx]
        common.render_pose(
            compare.draw_pose, selected_raw, row["pose"], head_pose, camera,
            arm=arm, label=f"{arm[0].upper()} raw #{idx}", width_m=record["width_m"],
            depth_m=record["depth_m"], forward_axis="local_x", marker="square", thickness=4,
        )
    panels.append((
        "02_selected_raw_anygrasp.png",
        common.add_header(
            selected_raw,
            "2 | SELECTED RAW ANYGRASP POSES",
            " | ".join(f"{arm.upper()} #{int(rec['candidate_idx'])}" for arm, rec in records.items()),
            "No frame remap, camera-up branch, or 5 cm target shift",
            (170, 0, 170), header_height,
        ),
    ))

    canonical = base_image.copy()
    for arm, record in records.items():
        idx = int(record["candidate_idx"])
        common.render_pose(
            compare.draw_pose, canonical, record["raw_pose_world_wxyz"], head_pose, camera,
            arm=arm, label=f"{arm[0].upper()} canonical #{idx}", width_m=record["width_m"],
            depth_m=record["depth_m"], forward_axis="local_z", marker="diamond", thickness=4,
        )
    max_equiv = max(value for row in physical_equivalence.values() for value in row.values())
    panels.append((
        "03_equivalent_robot_replay.png",
        common.add_header(
            canonical,
            "3 | SAME PHYSICAL GRASPS IN ROBOT_REPLAY FRAME",
            "Canonical actor uses +Z forward; this is a basis change, not a gripper rotation",
            f"Max mapped-axis disagreement vs panel 2: {max_equiv:.6f} deg",
            (0, 100, 220), header_height,
        ),
    ))

    camera_up = base_image.copy()
    for arm, record in records.items():
        idx = int(record["candidate_idx"])
        centered_pose = common.pose_with_position(record["pose_world_wxyz"], record["raw_pose_world_wxyz"][:3])
        common.render_pose(
            compare.draw_pose, camera_up, centered_pose, head_pose, camera,
            arm=arm, label=f"{arm[0].upper()} camera-up #{idx}", width_m=record["width_m"],
            depth_m=record["depth_m"], forward_axis="local_z", marker="diamond", thickness=4,
        )
    panels.append((
        "04_camera_back_up_branch.png",
        common.add_header(
            camera_up,
            "4 | PARALLEL-JAW CAMERA-BACK-UP BRANCH",
            "Forward stays canonical +Z; only the 180 deg finger-swap branch may change",
            "Up constraint: -canonical X = raw +Z points toward world up",
            (0, 155, 210), header_height,
        ),
    ))

    target = base_image.copy()
    target_distances: dict[str, float] = {}
    for arm, record in records.items():
        idx = int(record["candidate_idx"])
        raw_center = np.asarray(record["raw_pose_world_wxyz"][:3], dtype=np.float64)
        target_center = np.asarray(record["pose_world_wxyz"][:3], dtype=np.float64)
        object_name = f"{arm}_bottle"
        target_distances[arm] = float(np.linalg.norm(target_center - objects[object_name]))
        centered_pose = common.pose_with_position(record["pose_world_wxyz"], raw_center)
        common.render_pose(
            compare.draw_pose, target, centered_pose, head_pose, camera,
            arm=arm, label=f"center #{idx}", width_m=record["width_m"], depth_m=record["depth_m"],
            forward_axis="local_z", dashed=True, axes=False, thickness=2,
        )
        common.render_pose(
            compare.draw_pose, target, record["pose_world_wxyz"], head_pose, camera,
            arm=arm, label=f"target #{idx}", width_m=record["width_m"], depth_m=record["depth_m"],
            forward_axis="local_z", color=common.PLAN_LEFT_COLOR if arm == "left" else common.PLAN_RIGHT_COLOR,
            marker="triangle", thickness=4,
        )
        a = common.project_world_point(preview, compare, raw_center, head_pose, camera)
        b = common.project_world_point(preview, compare, target_center, head_pose, camera)
        if a is not None and b is not None:
            cv2.arrowedLine(target, a, b, (30, 30, 30), 2, cv2.LINE_AA, tipLength=0.18)
        common.draw_anchor_and_line(
            target, preview, compare, objects[object_name], target_center, head_pose, camera,
            color=common.LEFT_COLOR if arm == "left" else common.RIGHT_COLOR,
            label=arm.upper(),
        )
    panels.append((
        "05_final_target_and_object_anchor.png",
        common.add_header(
            target,
            "5 | FINAL PLANNER TARGET + OBJECT ANCHOR",
            "Dashed=selected center | solid triangle=5 cm back along canonical +Z",
            " | ".join(f"{arm.upper()} target-anchor {100.0 * value:.1f} cm" for arm, value in target_distances.items()),
            (120, 60, 160), header_height,
        ),
    ))

    overlay = base_image.copy()
    for arm, record in records.items():
        idx = int(record["candidate_idx"])
        common.render_pose(
            compare.draw_pose, overlay, by_idx[idx]["pose"], head_pose, camera,
            arm=arm, label=f"RAW-{arm[0].upper()}#{idx}", width_m=record["width_m"],
            depth_m=record["depth_m"], forward_axis="local_x", marker="square", thickness=4,
        )
        common.render_pose(
            compare.draw_pose, overlay, record["raw_pose_world_wxyz"], head_pose, camera,
            arm=arm, label=f"CAN-{arm[0].upper()}#{idx}", width_m=record["width_m"],
            depth_m=record["depth_m"], forward_axis="local_z", dashed=True, marker="diamond", thickness=3,
        )
        common.render_pose(
            compare.draw_pose, overlay, record["pose_world_wxyz"], head_pose, camera,
            arm=arm, label=f"TGT-{arm[0].upper()}#{idx}", width_m=record["width_m"],
            depth_m=record["depth_m"], forward_axis="local_z", dashed=True,
            color=common.PLAN_LEFT_COLOR if arm == "left" else common.PLAN_RIGHT_COLOR,
            marker="triangle", thickness=3,
        )
    panels.append((
        "06_raw_canonical_target_overlay.png",
        common.add_header(
            overlay,
            "6 | CONSISTENCY OVERLAY",
            "Square=raw +X actor | diamond=canonical +Z actor | triangle=final shifted target",
            "Raw and canonical gripper geometry should overlap; only target position is shifted",
            (20, 20, 20), header_height,
        ),
    ))

    frame_dir = output_root / f"frame_{frame:06d}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    panel_paths: list[Path] = []
    for filename, panel in panels:
        path = frame_dir / filename
        if not cv2.imwrite(str(path), panel):
            raise RuntimeError(f"Failed to write {path}")
        panel_paths.append(path)
    sheet = cv2.vconcat([
        cv2.hconcat([panel for _, panel in panels[:3]]),
        cv2.hconcat([panel for _, panel in panels[3:]]),
    ])
    sheet_path = frame_dir / "candidate_frame_consistency_contact_sheet_v7.png"
    if not cv2.imwrite(str(sheet_path), sheet):
        raise RuntimeError(f"Failed to write {sheet_path}")
    return {
        "frame": frame,
        "selected_ids": {arm: int(record["candidate_idx"]) for arm, record in records.items()},
        "physical_equivalence_axis_errors_deg": physical_equivalence,
        "final_target_to_object_anchor_m": target_distances,
        "panels": [{"path": str(path), "sha256": common.sha256(path)} for path in panel_paths],
        "contact_sheet": {"path": str(sheet_path), "sha256": common.sha256(sheet_path), "shape": list(sheet.shape)},
    }


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.expanduser().resolve().read_text(encoding="utf-8"))
    robotwin_root = Path(config["robotwin_root"])
    plan_summary_path = Path(config["plan_summary"])
    output_root = Path(config["output_root"])
    source_paths = [
        plan_summary_path,
        *[Path(entry[key]) for entry in config["frames"] for key in ("metadata_path", "raw_grasp_json", "object_debug_json")],
    ]
    for path in source_paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    print(f"Config: {args.config.expanduser().resolve()}")
    print(f"Plan summary: {plan_summary_path}")
    print(f"Output: {output_root}")
    if args.dry_run:
        print("Dry run complete; all source files exist and no outputs were written.")
        return 0
    if output_root.exists() and any(output_root.iterdir()):
        if not args.overwrite:
            raise FileExistsError(f"Refusing non-empty output without --overwrite: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(robotwin_root / "code_painting"))
    import export_v6_candidate_geometry_audit as common
    import render_anygrasp_ranked_preview as preview
    import render_selection_strategy_compare_v4 as compare

    summary = common.load_json(plan_summary_path)
    if summary.get("candidate_input_frame_contract") != "robot_replay":
        raise ValueError("V7 audit requires candidate_input_frame_contract=robot_replay")
    if summary.get("candidate_frame_contract") != "robot_replay":
        raise ValueError("V7 audit requires candidate_frame_contract=robot_replay")
    frame_records = [
        render_frame(entry, summary, output_root, preview, compare, common, int(config.get("header_height", 96)))
        for entry in config["frames"]
    ]
    manifest = {
        "schema": "piper_anygrasp_v7_frame_consistency.v1",
        "axis_contract": {
            "anygrasp_raw": "red +X approach; green +Y opening; blue +Z plane normal",
            "robot_replay": "blue +Z approach; green +Y opening; -red -X equals raw +Z plane normal",
            "mapped_physical_axes": "raw +X == canonical +Z; raw +Y == canonical +Y; raw +Z == canonical -X",
            "piper_ik_boundary": "single existing Curobo-to-SAPIEN link6 adapter; no second candidate remap",
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
