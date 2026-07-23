#!/usr/bin/env python3
"""Render method-specific candidate-to-RoboTwin transform audit sheets."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np


ARM_COLORS = {"left": (180, 0, 180), "right": (0, 140, 255)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--robotwin-root", type=Path, required=True)
    parser.add_argument("--plan-summary", type=Path, required=True)
    parser.add_argument("--metadata-k1", type=Path, required=True)
    parser.add_argument("--metadata-k2", type=Path, required=True)
    parser.add_argument("--method-label", required=True)
    parser.add_argument(
        "--pipeline-kind",
        choices=("anygrasp_v9", "oursv2_historical"),
        default="anygrasp_v9",
        help="Render the AnyGrasp-to-Piper V9 chain or the historical OursV2 human-retarget chain.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_for_frame(metadata: Mapping[str, Any], frame: int) -> Mapping[str, Any]:
    for item in metadata.get("frame_columns", []):
        if int(item.get("frame", -1)) == frame:
            return item
    raise KeyError(f"metadata does not contain frame={frame}")


def selected_by_arm(summary: Mapping[str, Any], frame: int) -> dict[str, dict[str, Any]]:
    result = {}
    for arm in ("left", "right"):
        matches = [
            dict(item)
            for item in (summary.get("selected_candidates_by_executed_arm") or {}).get(arm, [])
            if int(item.get("source_frame", -1)) == frame
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one selected record for arm={arm}, frame={frame}; got {len(matches)}")
        result[arm] = matches[0]
    return result


def add_header(
    image: np.ndarray,
    title: str,
    subtitle: str,
    note: str,
    accent: tuple[int, int, int],
) -> np.ndarray:
    header_h = 102
    canvas = np.full((header_h + image.shape[0], image.shape[1], 3), 248, np.uint8)
    canvas[header_h:] = image
    cv2.rectangle(canvas, (0, 0), (10, header_h - 1), accent, -1)
    cv2.putText(canvas, title, (22, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(canvas, subtitle, (22, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (40, 40, 40), 1, cv2.LINE_AA)
    cv2.putText(canvas, note, (22, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (70, 70, 70), 1, cv2.LINE_AA)
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1] - 1, canvas.shape[0] - 1), accent, 2)
    return canvas


def background(source: Mapping[str, Any]) -> np.ndarray:
    image = cv2.imread(str(source["foundation_image"]), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(source["foundation_image"])
    if image.shape[:2] != (480, 640):
        image = cv2.resize(image, (640, 480), interpolation=cv2.INTER_AREA)
    canvas = np.full((600, 640, 3), 255, np.uint8)
    canvas[:480] = image
    return canvas


def pose_with_position(pose: list[float], position: list[float]) -> list[float]:
    return [*map(float, position), *map(float, pose[3:])]


def draw_pair(
    draw_pose: Any,
    image: np.ndarray,
    records: Mapping[str, Mapping[str, Any]],
    source: Mapping[str, Any],
    pose_key: str,
    forward_axis: str,
    suffix: str,
) -> None:
    for arm in ("left", "right"):
        record = records[arm]
        draw_pose(
            image,
            record[pose_key],
            source["head_camera_pose_world_wxyz"],
            source["camera_intrinsics"],
            color=ARM_COLORS[arm],
            label=f"{arm[0].upper()} {suffix}",
            width_m=float(record.get("width_m", 0.08)),
            depth_m=float(record.get("depth_m", 0.04)),
            axis_length_m=0.050,
            forward_axis=forward_axis,
            line_thickness=4,
            marker="square" if arm == "left" else "diamond",
            label_offset=(7, -9) if arm == "left" else (-82, 18),
        )


def add_not_executed_panel(
    source: Mapping[str, Any],
    method_label: str,
    reason: str,
) -> np.ndarray:
    image = background(source)
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (image.shape[1] - 1, 479), (235, 235, 235), -1)
    image = cv2.addWeighted(overlay, 0.78, image, 0.22, 0.0)
    cv2.putText(
        image,
        "NOT EXECUTED",
        (127, 235),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.25,
        (20, 20, 210),
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        f"{method_label}: no K2 rigid target exists",
        (122, 278),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.54,
        (50, 50, 50),
        1,
        cv2.LINE_AA,
    )
    return add_header(
        image,
        "6 | V9 K2 RIGID OBJECT-TRANSPORT TARGET",
        "not fabricated: execution stopped before close / attachment / action",
        reason,
        (0, 0, 210),
    )


def render_oursv2_panels(
    draw_pose: Any,
    k1_records: Mapping[str, Mapping[str, Any]],
    k2_records: Mapping[str, Mapping[str, Any]],
    k1_source: Mapping[str, Any],
    k2_source: Mapping[str, Any],
) -> list[np.ndarray]:
    panels: list[np.ndarray] = []

    image = background(k1_source)
    draw_pair(draw_pose, image, k1_records, k1_source, "raw_pose_world_wxyz", "local_z", "HUMAN K1")
    panels.append(
        add_header(
            image,
            "1 | OURSV2 HUMAN-RETARGET K1 TARGET",
            "native OursV2 convention: local +Z is the forward / approach axis",
            "source is the saved human-replay target, not an AnyGrasp candidate",
            (100, 100, 100),
        )
    )

    image = background(k1_source)
    draw_pair(draw_pose, image, k1_records, k1_source, "raw_pose_world_wxyz", "local_z", "IDENTITY")
    panels.append(
        add_header(
            image,
            "2 | NO ANYGRASP-TO-PIPER AXIS REMAP",
            "OursV2 keeps the saved human-target orientation unchanged",
            "the AnyGrasp +Z -> Piper +X fixed remap does not belong to this branch",
            (90, 80, 180),
        )
    )

    image = background(k1_source)
    draw_pair(draw_pose, image, k1_records, k1_source, "pose_world_wxyz", "local_z", "NO UP FLIP")
    panels.append(
        add_header(
            image,
            "3 | NO CAMERA-UP CANDIDATE BRANCH",
            "human-retarget orientation is preserved; no 180 deg candidate roll is selected",
            "camera-up equivalence is an AnyGrasp selection rule, not an OursV2 step",
            (0, 135, 220),
        )
    )

    image = background(k1_source)
    draw_pair(draw_pose, image, k1_records, k1_source, "pose_world_wxyz", "local_z", "K1 IK")
    panels.append(
        add_header(
            image,
            "4 | OURSV2 K1 TARGET SENT TO 0515 URDF IK",
            "0515 model gripper_bias=0.12 m; adapter translation is 0.12-0.12=0",
            "no -5 cm AnyGrasp offset and no Canonical 0.19 m RTCP transform",
            (30, 150, 40),
        )
    )

    image = background(k2_source)
    draw_pair(draw_pose, image, k2_records, k2_source, "pose_world_wxyz", "local_z", "HUMAN K2")
    panels.append(
        add_header(
            image,
            "5 | OURSV2 HUMAN-RETARGET K2 TARGET",
            "the second target comes independently from the saved human trajectory",
            "this historical branch does not preserve a measured K1 EE-to-object transform",
            (0, 0, 210),
        )
    )

    image = background(k2_source)
    draw_pair(draw_pose, image, k1_records, k2_source, "pose_world_wxyz", "local_z", "K1")
    draw_pair(draw_pose, image, k2_records, k2_source, "pose_world_wxyz", "local_z", "K2")
    panels.append(
        add_header(
            image,
            "6 | OURSV2 K1 AND K2 TARGETS IN FRAME-78 CAMERA",
            "both saved world targets are projected into the same D435 view",
            "motion follows human-retarget targets; V9 rigid object transport is not applied",
            (160, 70, 0),
        )
    )
    return panels


def render_anygrasp_panels(
    draw_pose: Any,
    camera_to_world_pose: Any,
    method_label: str,
    summary: Mapping[str, Any],
    k1_records: Mapping[str, Mapping[str, Any]],
    k2_records: Mapping[str, Mapping[str, Any]],
    k1_source: Mapping[str, Any],
    k2_source: Mapping[str, Any],
    action_debug: Mapping[str, Any],
) -> list[np.ndarray]:
    remap = np.array([[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]])
    before_remap: dict[str, dict[str, Any]] = {}
    camera_up_pose: dict[str, dict[str, Any]] = {}
    for arm in ("left", "right"):
        record = k1_records[arm]
        pose = camera_to_world_pose(
            record["translation_cam"],
            np.asarray(record["rotation_cam"], dtype=np.float64),
            k1_source["head_camera_pose_world_wxyz"],
        )
        before_remap[arm] = {**record, "pose": pose.tolist()}
        expected_after = camera_to_world_pose(
            record["translation_cam"],
            np.asarray(record["rotation_cam"], dtype=np.float64) @ remap,
            k1_source["head_camera_pose_world_wxyz"],
        )
        actual_raw = np.asarray(record["raw_pose_world_wxyz"], dtype=np.float64)
        if np.linalg.norm(expected_after[:3] - actual_raw[:3]) > 1e-6:
            raise ValueError(f"remap position audit failed for {arm}")
        camera_up_pose[arm] = {
            **record,
            "pose": pose_with_position(record["pose_world_wxyz"], record["raw_pose_world_wxyz"][:3]),
        }

    panels: list[np.ndarray] = []
    candidate_ids = "/".join(
        f"{arm[0].upper()}{int(k1_records[arm]['candidate_idx'])}" for arm in ("left", "right")
    )

    image = background(k1_source)
    draw_pair(draw_pose, image, before_remap, k1_source, "pose", "local_z", "INPUT")
    panels.append(
        add_header(
            image,
            "1 | SELECTED ROBOT_REPLAY CANDIDATE",
            f"{method_label} K1 {candidate_ids} | native local +Z is approach",
            "candidate translation_cam / rotation_cam before Piper-axis remap",
            (100, 100, 100),
        )
    )

    image = background(k1_source)
    draw_pair(draw_pose, image, k1_records, k1_source, "raw_pose_world_wxyz", "local_x", "REMAP")
    panels.append(
        add_header(
            image,
            "2 | FIXED AXIS REMAP TO PIPER PHYSICAL FRAME",
            "Piper +X = input +Z | Piper +Y = input +Y | Piper +Z = input -X",
            "orientation only; candidate origin is unchanged",
            (90, 80, 180),
        )
    )

    image = background(k1_source)
    draw_pair(draw_pose, image, camera_up_pose, k1_source, "pose", "local_x", "UP")
    flips = ", ".join(
        f"{arm[0].upper()} flip={k1_records[arm].get('camera_up_flip_applied')}"
        for arm in ("left", "right")
    )
    panels.append(
        add_header(
            image,
            "3 | PARALLEL-JAW CAMERA-UP EQUIVALENT BRANCH",
            flips,
            "optional 180 deg roll around forward +X; grasp line and origin stay fixed",
            (0, 135, 220),
        )
    )

    image = background(k1_source)
    draw_pair(draw_pose, image, k1_records, k1_source, "pose_world_wxyz", "local_x", "K1")
    panels.append(
        add_header(
            image,
            "4 | FINAL K1 ROBOTWIN REPLAY TARGET",
            "-5 cm along physical local +X, then sent to 0515 URDF IK",
            "gripper_bias=0.12 m makes adapter translation zero; Canonical 0.19 m is not used",
            (30, 150, 40),
        )
    )

    image = background(k2_source)
    draw_pair(draw_pose, image, k2_records, k2_source, "pose_world_wxyz", "local_x", "OLD K2")
    panels.append(
        add_header(
            image,
            "5 | OLD K2: INDEPENDENT NEW GRASP CANDIDATE",
            "this changes EE-to-object relation after the object was attached at K1",
            "kept only as an audit reference; no longer used by a completed V9 action",
            (0, 0, 210),
        )
    )

    if set(action_debug) == {"left", "right"}:
        corrected = {
            arm: {
                **k2_records[arm],
                "pose_world_wxyz": action_debug[arm]["rigid_transport_target_pose_world_wxyz"],
            }
            for arm in ("left", "right")
        }
        image = background(k2_source)
        draw_pair(draw_pose, image, corrected, k2_source, "pose_world_wxyz", "local_x", "V9 K2")
        panels.append(
            add_header(
                image,
                "6 | V9 K2: RIGID OBJECT-TRANSPORT TARGET",
                "T_W_EE2 = T_W_OBJECT2 @ inverse(T_EE_OBJECT measured after K1)",
                "same physical grasp is preserved while the object moves to FoundationPose frame 78",
                (160, 70, 0),
            )
        )
    else:
        failed = summary.get("failed_stage_records") or []
        reason = "K1 did not satisfy the reach gate"
        blocking = [
            record
            for record in failed
            if str(record.get("status", "")).lower() != "skipped" and not bool(record.get("reached"))
        ]
        if blocking:
            record = blocking[-1]
            reason = (
                f"K1 {record.get('arm', 'unknown arm')} {record.get('stage', 'unknown stage')} "
                f"reach miss: {float(record.get('rot_err_deg', float('nan'))):.2f} deg"
            )
        panels.append(add_not_executed_panel(k2_source, method_label, reason))
    return panels


def main() -> int:
    args = parse_args()
    paths = [args.plan_summary, args.metadata_k1, args.metadata_k2]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing inputs:\n" + "\n".join(missing))

    summary = load_json(args.plan_summary)
    if args.pipeline_kind == "anygrasp_v9" and summary.get("action_target_mode") != "rigid_object_transport":
        raise ValueError("plan summary is not a rigid_object_transport run")
    k1_records = selected_by_arm(summary, 38)
    k2_records = selected_by_arm(summary, 78)
    k1_source = source_for_frame(load_json(args.metadata_k1), 38)
    k2_source = source_for_frame(load_json(args.metadata_k2), 78)
    action_debug = summary.get("action_target_debug_by_arm") or {}

    if args.dry_run:
        print(
            f"Dry run: method={args.method_label} pipeline={args.pipeline_kind} "
            f"rigid_action_arms={sorted(action_debug)} -> {args.output}"
        )
        return 0

    import sys

    sys.path.insert(0, str(args.robotwin_root / "code_painting"))
    from render_selection_strategy_compare_v4 import camera_to_world_pose, draw_pose

    if args.pipeline_kind == "oursv2_historical":
        panels = render_oursv2_panels(draw_pose, k1_records, k2_records, k1_source, k2_source)
        axis_contract = {
            "oursv2_human_retarget": {
                "forward": "local +Z",
                "axis_remap": "none",
                "camera_up_candidate_branch": "none",
                "candidate_target_offset": "none",
            },
            "ik": {
                "family": "0515 Piper/OursV2 URDFIK",
                "gripper_bias_m": 0.12,
                "gripper_to_endlink_translation_m": 0.0,
                "canonical_rtcp_0p19_used": False,
            },
        }
        action_target_mode = "historical_oursv2_human_retarget"
    else:
        panels = render_anygrasp_panels(
            draw_pose,
            camera_to_world_pose,
            args.method_label,
            summary,
            k1_records,
            k2_records,
            k1_source,
            k2_source,
            action_debug,
        )
        axis_contract = {
            "input_robot_replay": {"forward": "local +Z", "opening": "local +Y", "normal": "local -X"},
            "piper_physical": {
                "forward": "local +X / red",
                "opening": "local +Y / green",
                "camera_back": "local +Z / blue",
            },
            "fixed_remap": "physical +X=input +Z; physical +Y=input +Y; physical +Z=input -X",
            "ik": {
                "family": "0515 Piper/OursV2 URDFIK",
                "gripper_bias_m": 0.12,
                "gripper_to_endlink_translation_m": 0.0,
                "canonical_rtcp_0p19_used": False,
            },
        }
        action_target_mode = "rigid_object_transport"

    sheet = cv2.vconcat([cv2.hconcat(panels[:3]), cv2.hconcat(panels[3:])])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), sheet):
        raise RuntimeError(f"failed to write {args.output}")
    manifest = {
        "schema": "candidate_to_robotwin_transform_audit.v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": args.method_label,
        "pipeline_kind": args.pipeline_kind,
        "plan_summary": str(args.plan_summary.resolve()),
        "plan_summary_sha256": sha256(args.plan_summary),
        "metadata_k1": str(args.metadata_k1.resolve()),
        "metadata_k1_sha256": sha256(args.metadata_k1),
        "metadata_k2": str(args.metadata_k2.resolve()),
        "metadata_k2_sha256": sha256(args.metadata_k2),
        "selected_record_ids": {
            "k1_frame_38": {
                arm: int(k1_records[arm]["candidate_idx"]) for arm in ("left", "right")
            },
            "k2_frame_78": {
                arm: int(k2_records[arm]["candidate_idx"]) for arm in ("left", "right")
            },
        },
        "output": str(args.output.resolve()),
        "output_sha256": sha256(args.output),
        "axis_contract": axis_contract,
        "action_target_mode": action_target_mode,
        "rigid_action_complete": set(action_debug) == {"left", "right"},
        "action_target_debug_by_arm": action_debug,
    }
    manifest_path = args.output.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
