#!/usr/bin/env python3
"""Run the paper V3 six-panel exporter while preserving real active-arm metadata."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np


ASSET_ROOT = Path("/home/zaijia001/ssd/data/piper/paper_qualitative_assets")
sys.path.insert(0, str(ASSET_ROOT))
import export_keyframe_candidate_comparison_v3 as exporter  # noqa: E402
import export_keyframe_candidate_images_combined_both_v2 as legacy_panels  # noqa: E402


def active_arms(config: Mapping[str, Any]) -> tuple[str, ...]:
    values = tuple(str(value) for value in config.get("active_arms", ()))
    if not values or any(value not in {"left", "right"} for value in values):
        raise ValueError(f"invalid active_arms: {values}")
    return values


def rank_candidates(
    config: Mapping[str, Any],
    metadata: Mapping[str, Any],
    pool: list[dict[str, Any]],
    preview_module: Any,
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    metric = str(config["orientation_metric"])
    max_error = float(config["max_orientation_error_deg"])
    anygrasp_weight = float(config["weights"]["anygrasp"])
    orientation_weight = float(config["weights"]["orientation"])
    arms = active_arms(config)
    selected: dict[str, dict[str, dict[str, Any]]] = {
        strategy: {
            arm: {"candidate_idx": "INACTIVE", "inactive": True, "score": None}
            for arm in ("left", "right")
            if arm not in arms
        }
        for strategy in exporter.STRATEGIES
    }
    rankings: dict[str, list[dict[str, Any]]] = {
        arm: [] for arm in ("left", "right") if arm not in arms
    }
    for arm in arms:
        human_record = exporter.metadata_record(metadata, "oursv2", arm)
        human_rotation = np.asarray(
            human_record["selection_pose"]["rotation_world"], dtype=np.float64
        )
        target_object = str(config["target_objects"][arm])
        rows: list[dict[str, Any]] = []
        for candidate in pool:
            if str(candidate["nearest_object"]) != target_object:
                continue
            row = copy.deepcopy(candidate)
            candidate_rotation = np.asarray(row["pose"]["rotation_world"], dtype=np.float64)
            distances = preview_module.orientation_distances_deg(
                human_rotation,
                candidate_rotation,
                approach_axis_index=2,
            )
            row.update({f"{name}_distance_deg": float(value) for name, value in distances.items()})
            row["orientation_metric"] = metric
            row["orientation_error_deg"] = float(distances[metric])
            row["orientation_score"] = float(
                preview_module.orientation_score_from_rotation_distance(
                    row["orientation_error_deg"]
                )
            )
            row["fused_score"] = (
                anygrasp_weight * float(row["score"])
                + orientation_weight * float(row["orientation_score"])
            )
            rows.append(row)
        if not rows:
            raise RuntimeError(f"No {arm} candidate belongs to object {target_object}")
        eligible = [row for row in rows if float(row["orientation_error_deg"]) <= max_error]
        if not eligible:
            raise RuntimeError(f"No {arm} candidate survives {metric} <= {max_error} deg")
        orientation = min(
            eligible,
            key=lambda row: (
                float(row["orientation_error_deg"]),
                -float(row["score"]),
                int(row["candidate_idx"]),
            ),
        )
        fused = max(
            eligible,
            key=lambda row: (
                float(row["fused_score"]),
                float(row["score"]),
                -int(row["candidate_idx"]),
            ),
        )
        top_score = max(rows, key=lambda row: (float(row["score"]), -int(row["candidate_idx"])))
        selected["orientation"][arm] = copy.deepcopy(orientation)
        selected["fused"][arm] = copy.deepcopy(fused)
        selected["top_score"][arm] = copy.deepcopy(top_score)
        selected["oursv2"][arm] = {
            "candidate_idx": None,
            "score": None,
            "pose": copy.deepcopy(human_record["selection_pose"]),
            "width": float(human_record.get("gripper_width_m", 0.08)),
            "depth": float(human_record.get("gripper_depth_m", 0.04)),
            "orientation_metric": "human_target",
        }
        rankings[arm] = sorted(
            rows,
            key=lambda row: (
                float(row["orientation_error_deg"]),
                -float(row["score"]),
                int(row["candidate_idx"]),
            ),
        )
    return selected, rankings


def source_record(metadata: Mapping[str, Any], strategy: str, arm: str) -> dict[str, Any]:
    matches = [
        record
        for record in metadata["records"]
        if str(record.get("strategy")) == strategy and str(record.get("arm")) == arm
    ]
    if len(matches) == 1:
        return copy.deepcopy(matches[0])
    for fallback in ("top_score", "oursv2"):
        candidates = [
            record
            for record in metadata["records"]
            if str(record.get("strategy")) == fallback and str(record.get("arm")) == arm
        ]
        if len(candidates) == 1:
            value = copy.deepcopy(candidates[0])
            value["strategy"] = strategy
            value["selection_source"] = f"synthesized V3 {strategy} record from {fallback} template"
            return value
    raise ValueError(f"No source template for {strategy}/{arm}")


def updated_metadata(
    metadata: Mapping[str, Any],
    selected: Mapping[str, Mapping[str, Mapping[str, Any]]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(metadata)
    arms = active_arms(config)
    records = []
    for strategy in exporter.STRATEGIES:
        for arm in arms:
            original = source_record(metadata, strategy, arm)
            selection = selected[strategy][arm]
            original["strategy"] = strategy
            original["arm"] = arm
            original["candidate_idx"] = selection.get("candidate_idx")
            original["candidate_score"] = selection.get("score")
            original["selection_pose"] = copy.deepcopy(selection["pose"])
            original["canonical_pose"] = copy.deepcopy(selection["pose"])
            original["gripper_width_m"] = float(selection.get("width", 0.08))
            original["gripper_depth_m"] = float(selection.get("depth", 0.04))
            if strategy != "oursv2":
                original["selection_source"] = (
                    f"paper V3 canonical rerank: {config['orientation_metric']}"
                    if strategy != "top_score"
                    else "paper V3 canonical top AnyGrasp score within arm object partition"
                )
                original["selection_metrics"] = {
                    "ranking_strategy": strategy,
                    "orientation_metric": str(config["orientation_metric"]),
                    "orientation_error_deg": float(selection["orientation_error_deg"]),
                    "so3_rotation_distance_deg": float(selection["so3_distance_deg"]),
                    "parallel_jaw_symmetry_distance_deg": float(
                        selection["parallel_jaw_symmetry_distance_deg"]
                    ),
                    "approach_axis_distance_deg": float(selection["approach_axis_distance_deg"]),
                    "anygrasp_score_raw": float(selection["score"]),
                    "orientation_score": float(selection["orientation_score"]),
                    "fused_score": float(selection["fused_score"]),
                }
            records.append(original)
    result["schema"] = "selection_strategy_paper_comparison_v3.active_arms.v1"
    result["records"] = records
    result["active_arms"] = list(arms)
    result["orientation_metric"] = str(config["orientation_metric"])
    result["parallel_jaw_convention"] = (
        "canonical local +Z is directed approach; selection uses approach_axis and ignores roll"
    )
    return result


def render_all_methods_panel(
    metadata: Mapping[str, Any],
    selected: Mapping[str, Mapping[str, Mapping[str, Any]]],
    output_path: Path,
    draw_pose: Any,
    render: Mapping[str, Any],
) -> None:
    source = metadata["frame_columns"][0]
    image = cv2.imread(str(source["foundation_image"]), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(source["foundation_image"])
    head_pose = np.asarray(source["head_camera_pose_world_wxyz"], dtype=np.float64)
    camera = dict(source["camera_intrinsics"])
    styles = {
        "orientation": {"dashed": False, "line_thickness": 4, "marker": "square"},
        "fused": {"dashed": True, "line_thickness": 3, "marker": "diamond"},
        "top_score": {"dashed": False, "line_thickness": 3, "marker": "triangle"},
        "oursv2": {"dashed": False, "line_thickness": 2, "marker": "circle"},
    }
    for strategy in exporter.STRATEGIES:
        for arm in metadata["active_arms"]:
            candidate = selected[strategy][arm]
            candidate_text = (
                "H" if candidate.get("candidate_idx") is None else str(candidate["candidate_idx"])
            )
            draw_pose(
                image,
                exporter.pose_array(candidate["pose"]),
                head_pose,
                camera,
                color=exporter.STRATEGY_COLORS[strategy],
                label=f"{strategy[:3].upper()}-{'L' if arm == 'left' else 'R'}#{candidate_text}",
                width_m=float(candidate.get("width", 0.08)),
                depth_m=float(candidate.get("depth", 0.04)),
                axis_length_m=float(render["overlay_axis_length_m"]),
                forward_axis="local_z",
                draw_axes=True,
                label_offset=(6, -8 if arm == "left" else 16),
                **styles[strategy],
            )
    panel = exporter.add_header(
        image,
        "ALL FOUR STRATEGIES | CANONICAL SELECTION POSES",
        "ORI magenta | FUSED orange dashed | TOP black | OURSV2 blue-brown",
        "Only metadata-active arms | no planner/TCP offsets | axes X red Y green Z blue",
        (0, 110, 220),
        int(render["global_title_height"]),
    )
    if not cv2.imwrite(str(output_path), panel):
        raise RuntimeError(f"Failed to write {output_path}")


def render_strategy_image(
    metadata: Mapping[str, Any],
    strategy: str,
    output_path: Path,
    render: Mapping[str, Any],
    draw_pose: Any,
) -> dict[str, Any]:
    requested_frame = int(metadata["requested_frame"])
    task = str(metadata["task"])
    episode_id = int(metadata["episode_id"])
    global_title_height = int(render["global_title_height"])
    axis_length_m = float(render["axis_length_m"])
    source = legacy_panels.frame_source(metadata, requested_frame)
    image_path = Path(str(source["foundation_image"]))
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Cannot read Foundation image: {image_path}")
    arms = []
    active = tuple(str(arm) for arm in metadata["active_arms"])
    for arm in active:
        arm_record = legacy_panels.record_for(metadata, strategy, arm)
        arms.append(
            legacy_panels.draw_arm_on_shared_image(
                image,
                source,
                arm_record,
                arm,
                axis_length_m,
                draw_pose,
            )
        )
    canvas = np.full(
        (global_title_height + image.shape[0], image.shape[1], 3),
        250,
        dtype=np.uint8,
    )
    accent = legacy_panels.STRATEGY_COLORS[strategy]
    cv2.rectangle(
        canvas,
        (0, 0),
        (canvas.shape[1] - 1, global_title_height - 1),
        (245, 245, 245),
        -1,
    )
    cv2.rectangle(canvas, (0, 0), (10, global_title_height - 1), accent, -1)
    scope = "BOTH" if len(active) == 2 else active[0].upper()
    legacy_panels.put_text(
        canvas,
        f"{legacy_panels.STRATEGY_DISPLAY[strategy]} | {task} | id{episode_id} | keyframe {requested_frame} | {scope}",
        (22, 27),
        0.52,
        (25, 25, 25),
        2,
    )
    identity = "  |  ".join(
        f"{arm.upper()} {legacy_panels.candidate_title(legacy_panels.record_for(metadata, strategy, arm))}"
        for arm in active
    )
    legacy_panels.put_text(canvas, identity, (22, 55), 0.48, (35, 35, 35), 2)
    semantics = (
        "Selection pose before planner offset | OursV2 is a human-retarget target, not an AnyGrasp candidate"
        if strategy == "oursv2"
        else "Canonical selection pose before planner offset / retreat / pregrasp"
    )
    display_semantics = (
        f"Human-retarget targets | shared replay background frame {requested_frame}"
        if strategy == "oursv2"
        else f"Selection Pose only | shared replay background frame {requested_frame}"
    )
    legacy_panels.put_text(
        canvas, display_semantics, (22, 80), 0.38, (65, 65, 65), 1
    )
    canvas[global_title_height:, :] = image
    cv2.rectangle(
        canvas,
        (0, 0),
        (canvas.shape[1] - 1, canvas.shape[0] - 1),
        accent,
        2,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), canvas):
        raise RuntimeError(f"Failed to write {output_path}")
    return {
        "strategy": strategy,
        "display_name": legacy_panels.STRATEGY_DISPLAY[strategy],
        "task": task,
        "episode_id": episode_id,
        "keyframe": requested_frame,
        "hand_scope": scope.lower(),
        "layout": "single_replay_background_active_arms",
        "background_frame": requested_frame,
        "foundation_image": str(image_path),
        "pose_semantics": semantics,
        "arms": arms,
        "output": str(output_path),
        "sha256": legacy_panels.sha256(output_path),
        "image_shape": list(canvas.shape),
    }


exporter.rank_candidates = rank_candidates
exporter.updated_metadata = updated_metadata
exporter.render_all_methods_panel = render_all_methods_panel
legacy_panels.render_strategy_image = render_strategy_image


if __name__ == "__main__":
    try:
        raise SystemExit(exporter.main())
    except (FileExistsError, FileNotFoundError, KeyError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}")
        raise SystemExit(1)
