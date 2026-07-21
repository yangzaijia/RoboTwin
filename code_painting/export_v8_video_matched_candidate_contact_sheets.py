#!/usr/bin/env python3
"""Render V8 candidate sheets that exactly match execution-video plan summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np


METHODS = ("orientation", "fused", "top_score")
METHOD_TITLES = {
    "orientation": "ORIENTATION",
    "fused": "FUSED",
    "top_score": "GRASPNET TOP-SCORE",
}
METHOD_COLORS = {
    "orientation": (180, 0, 180),
    "fused": (0, 140, 255),
    "top_score": (20, 20, 20),
    "oursv2": (170, 100, 0),
}
ARM_COLORS = {"left": (180, 0, 180), "right": (0, 140, 255)}
OBJECT_COLORS = {"left_bottle": (180, 80, 180), "right_bottle": (0, 150, 255)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--episode-id", type=int, required=True)
    parser.add_argument("--keyframe", type=int, action="append", required=True)
    parser.add_argument(
        "--method",
        action="append",
        required=True,
        metavar="NAME=PLAN_SUMMARY_JSON",
        help="Repeat for orientation, fused, and top_score.",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        required=True,
        metavar="FRAME=METADATA_JSON",
        help="Repeat once per keyframe.",
    )
    parser.add_argument("--robotwin-root", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--publish-dir", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def keyed_paths(values: list[str], expected: set[str], label: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"invalid {label} value {value!r}; expected KEY=PATH")
        key, path = value.split("=", 1)
        key = key.strip()
        if key in result:
            raise ValueError(f"duplicate {label} key: {key}")
        result[key] = Path(path).expanduser().resolve()
    if set(result) != expected:
        raise ValueError(f"{label} keys must be {sorted(expected)}, got {sorted(result)}")
    return result


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    height: int = 96,
) -> np.ndarray:
    canvas = np.full((height + image.shape[0], image.shape[1], 3), 250, np.uint8)
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1] - 1, height - 1), (245, 245, 245), -1)
    cv2.rectangle(canvas, (0, 0), (10, height - 1), accent, -1)
    put_text(canvas, title, (22, 27), 0.50, (25, 25, 25), 2)
    put_text(canvas, subtitle, (22, 55), 0.44, (35, 35, 35), 2)
    put_text(canvas, note, (22, 80), 0.34, (65, 65, 65), 1)
    canvas[height:, :] = image
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1] - 1, canvas.shape[0] - 1), accent, 2)
    return canvas


def metadata_source(metadata: Mapping[str, Any], frame: int) -> Mapping[str, Any]:
    for item in metadata.get("frame_columns", []):
        if int(item.get("frame", -1)) == int(frame):
            return item
    raise KeyError(f"metadata has no frame column for {frame}")


def selected_map(summary: Mapping[str, Any], frame: int) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for arm in ("left", "right"):
        records = (summary.get("selected_candidates_by_executed_arm") or {}).get(arm, [])
        matches = [record for record in records if int(record.get("source_frame", -1)) == frame]
        if len(matches) != 1:
            raise ValueError(f"expected one selected {arm} candidate at frame {frame}, got {len(matches)}")
        result[arm] = dict(matches[0])
    return result


def oursv2_map(metadata: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for arm in ("left", "right"):
        matches = [
            record
            for record in metadata.get("records", [])
            if str(record.get("strategy")) == "oursv2" and str(record.get("arm")) == arm
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one OursV2 {arm} metadata record, got {len(matches)}")
        result[arm] = dict(matches[0])
    return result


def payload_pose(payload: Mapping[str, Any]) -> list[float]:
    frame = str(payload.get("frame", "world"))
    return [
        *[float(value) for value in payload[f"position_{frame}_m"]],
        *[float(value) for value in payload["quat_wxyz"]],
    ]


def candidate_identity(selected: Mapping[str, Mapping[str, Any]]) -> str:
    return " | ".join(
        f"{arm.upper()} #{int(selected[arm]['candidate_idx'])}" for arm in ("left", "right")
    )


def draw_v8_candidate(
    draw_pose: Any,
    image: np.ndarray,
    record: Mapping[str, Any],
    arm: str,
    source: Mapping[str, Any],
    *,
    color: tuple[int, int, int],
    label: str,
    axis_length: float,
    dashed: bool = False,
    line_thickness: int = 4,
    marker: str = "square",
    draw_axes: bool = True,
) -> None:
    draw_pose(
        image,
        record["pose_world_wxyz"],
        source["head_camera_pose_world_wxyz"],
        source["camera_intrinsics"],
        color=color,
        label=label,
        width_m=float(record.get("width_m", 0.08)),
        depth_m=float(record.get("depth_m", 0.04)),
        axis_length_m=axis_length,
        forward_axis="local_x",
        dashed=dashed,
        draw_axes=draw_axes,
        line_thickness=line_thickness,
        marker=marker,
        label_offset=(7, -9) if arm == "left" else (-72, 18),
    )


def draw_oursv2(
    draw_pose: Any,
    image: np.ndarray,
    record: Mapping[str, Any],
    arm: str,
    source: Mapping[str, Any],
    *,
    color: tuple[int, int, int],
    label: str,
    axis_length: float,
    draw_axes: bool = True,
) -> None:
    draw_pose(
        image,
        payload_pose(record["selection_pose"]),
        source["head_camera_pose_world_wxyz"],
        source["camera_intrinsics"],
        color=color,
        label=label,
        width_m=float(record.get("gripper_width_m", 0.08)),
        depth_m=float(record.get("gripper_depth_m", 0.04)),
        axis_length_m=axis_length,
        forward_axis="local_z",
        dashed=False,
        draw_axes=draw_axes,
        line_thickness=3,
        marker="circle",
        label_offset=(7, -9) if arm == "left" else (-84, 18),
    )


def read_background(source: Mapping[str, Any]) -> np.ndarray:
    image = cv2.imread(str(source["foundation_image"]), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(source["foundation_image"])
    if image.shape[:2] != (480, 640):
        image = cv2.resize(image, (640, 480), interpolation=cv2.INTER_AREA)
    return image


def render_frame(
    frame: int,
    metadata: Mapping[str, Any],
    summaries: Mapping[str, Mapping[str, Any]],
    draw_pose: Any,
    frame_dir: Path,
) -> dict[str, Any]:
    source = metadata_source(metadata, frame)
    selections = {method: selected_map(summary, frame) for method, summary in summaries.items()}
    ours = oursv2_map(metadata)
    dense = list((summaries["top_score"].get("all_candidates_per_keyframe") or {}).get(str(frame), []))
    if not dense:
        raise ValueError(f"Top-score summary has no V8 candidate pool for frame {frame}")

    panels: list[tuple[str, np.ndarray]] = []
    image = read_background(source)
    for record in dense:
        draw_v8_candidate(
            draw_pose,
            image,
            record,
            "left" if str(record.get("nearest_object")) == "left_bottle" else "right",
            source,
            color=OBJECT_COLORS.get(str(record.get("nearest_object")), (105, 105, 105)),
            label=f"#{int(record['candidate_idx'])}",
            axis_length=0.024,
            line_thickness=1,
            marker="circle",
            draw_axes=False,
        )
    panels.append(
        (
            "01_v8_dense_physical_targets.png",
            add_header(
                image,
                "V8 CANDIDATE POOL | PHYSICAL PIPER TARGETS",
                f"{len(dense)} targets after physical-axis remap and camera-up branch",
                "local +X is forward | magenta=left object | orange=right object",
                (90, 90, 90),
            ),
        )
    )

    for index, method in enumerate(METHODS, start=2):
        image = read_background(source)
        for arm in ("left", "right"):
            record = selections[method][arm]
            draw_v8_candidate(
                draw_pose,
                image,
                record,
                arm,
                source,
                color=ARM_COLORS[arm],
                label=f"{'L' if arm == 'left' else 'R'} #{int(record['candidate_idx'])}",
                axis_length=0.050,
                marker="square" if arm == "left" else "diamond",
            )
        panels.append(
            (
                f"{index:02d}_{method}_v8_target_both.png",
                add_header(
                    image,
                    f"{METHOD_TITLES[method]} | V8 VIDEO-MATCHED TARGET",
                    candidate_identity(selections[method]),
                    "final candidate pose before IK | X red forward | Y green open | Z blue normal",
                    METHOD_COLORS[method],
                ),
            )
        )

    image = read_background(source)
    for arm in ("left", "right"):
        draw_oursv2(
            draw_pose,
            image,
            ours[arm],
            arm,
            source,
            color=ARM_COLORS[arm],
            label=f"{'L' if arm == 'left' else 'R'} HUMAN",
            axis_length=0.050,
        )
    panels.append(
        (
            "05_oursv2_human_target_both.png",
            add_header(
                image,
                "OURSV2 | ORIGINAL HUMAN TARGET REFERENCE",
                "LEFT HUMAN TARGET | RIGHT HUMAN TARGET",
                "unchanged historical target | native canonical +Z approach | not a V8 AnyGrasp candidate",
                METHOD_COLORS["oursv2"],
            ),
        )
    )

    image = read_background(source)
    styles = {
        "orientation": (False, 4, "square"),
        "fused": (True, 3, "diamond"),
        "top_score": (False, 3, "triangle"),
    }
    for method in METHODS:
        dashed, thickness, marker = styles[method]
        for arm in ("left", "right"):
            record = selections[method][arm]
            draw_v8_candidate(
                draw_pose,
                image,
                record,
                arm,
                source,
                color=METHOD_COLORS[method],
                label=f"{method[:3].upper()}-{'L' if arm == 'left' else 'R'}#{int(record['candidate_idx'])}",
                axis_length=0.031,
                dashed=dashed,
                line_thickness=thickness,
                marker=marker,
            )
    for arm in ("left", "right"):
        draw_oursv2(
            draw_pose,
            image,
            ours[arm],
            arm,
            source,
            color=METHOD_COLORS["oursv2"],
            label=f"OURS-{'L' if arm == 'left' else 'R'}",
            axis_length=0.031,
        )
    panels.append(
        (
            "06_all_methods_overlay.png",
            add_header(
                image,
                "ALL METHODS | EXACT V8 SELECTIONS + OURSV2 REFERENCE",
                "ORI magenta | FUSED orange dashed | TOP black | OURSV2 blue-brown",
                "V8 methods use physical +X forward; OursV2 remains native +Z-forward human target",
                (0, 110, 220),
            ),
        )
    )

    frame_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, panel in panels:
        path = frame_dir / name
        if not cv2.imwrite(str(path), panel):
            raise RuntimeError(f"failed to write {path}")
        paths.append(path)
    sheet = cv2.vconcat([cv2.hconcat([panel for _, panel in panels[:3]]), cv2.hconcat([panel for _, panel in panels[3:]])])
    sheet_path = frame_dir / "all_strategies_contact_sheet_v8_video_matched.png"
    if not cv2.imwrite(str(sheet_path), sheet):
        raise RuntimeError(f"failed to write {sheet_path}")
    return {
        "keyframe": frame,
        "source_image": str(source["foundation_image"]),
        "source_image_sha256": sha256(Path(source["foundation_image"])),
        "candidate_pool_source": "top_score.all_candidates_per_keyframe",
        "candidate_pool_count": len(dense),
        "selected": {
            method: {
                arm: {
                    "candidate_idx": int(selections[method][arm]["candidate_idx"]),
                    "pose_world_wxyz": selections[method][arm]["pose_world_wxyz"],
                    "raw_pose_world_wxyz": selections[method][arm].get("raw_pose_world_wxyz"),
                    "width_m": selections[method][arm].get("width_m"),
                    "depth_m": selections[method][arm].get("depth_m"),
                    "camera_up_flip_applied": selections[method][arm].get("camera_up_flip_applied"),
                }
                for arm in ("left", "right")
            }
            for method in METHODS
        },
        "panels": [{"path": str(path), "sha256": sha256(path)} for path in paths],
        "contact_sheet": {
            "path": str(sheet_path),
            "sha256": sha256(sheet_path),
            "width": int(sheet.shape[1]),
            "height": int(sheet.shape[0]),
        },
    }


def main() -> int:
    args = parse_args()
    args.robotwin_root = args.robotwin_root.expanduser().resolve()
    args.asset_root = args.asset_root.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.publish_dir = None if args.publish_dir is None else args.publish_dir.expanduser().resolve()
    keyframes = sorted(set(args.keyframe))
    method_paths = keyed_paths(args.method, set(METHODS), "method")
    metadata_paths = keyed_paths(args.metadata, {str(frame) for frame in keyframes}, "metadata")
    inputs = [*method_paths.values(), *metadata_paths.values()]
    missing = [str(path) for path in inputs if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing inputs:\n" + "\n".join(missing))
    summaries = {name: load_json(path) for name, path in method_paths.items()}
    metadata = {int(frame): load_json(path) for frame, path in metadata_paths.items()}
    for frame in keyframes:
        for method in METHODS:
            selected_map(summaries[method], frame)
        oursv2_map(metadata[frame])
    print(f"Task: {args.task} / id{args.episode_id}")
    print(f"Keyframes: {keyframes}")
    for method in METHODS:
        ids = []
        for frame in keyframes:
            chosen = selected_map(summaries[method], frame)
            ids.append(f"K{frame}=L{chosen['left']['candidate_idx']}/R{chosen['right']['candidate_idx']}")
        print(f"{method}: {'; '.join(ids)}")
    print(f"Output: {args.output_dir}")
    if args.dry_run:
        print("Dry run complete; no files written.")
        return 0
    if args.output_dir.exists():
        if not args.overwrite:
            raise FileExistsError(args.output_dir)
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True)
    sys.path.insert(0, str(args.robotwin_root / "code_painting"))
    from render_selection_strategy_compare_v4 import draw_pose

    frames = []
    for frame in keyframes:
        frames.append(render_frame(frame, metadata[frame], summaries, draw_pose, args.output_dir / f"frame_{frame:06d}"))
    manifest = {
        "schema": "v8_video_matched_candidate_contact_sheets.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": args.task,
        "episode_id": args.episode_id,
        "axis_contract": {
            "v8_candidate_forward": "local +X / red",
            "v8_candidate_opening": "local +Y / green",
            "v8_candidate_normal_camera_back": "local +Z / blue",
            "oursv2_reference": "native canonical local +Z approach; not remapped or relabeled",
        },
        "pose_contract": "V8 pose_world_wxyz after physical-axis remap, camera-up branch, and configured candidate target offset; before IK",
        "method_plan_summaries": {
            method: {"path": str(path), "sha256": sha256(path)} for method, path in method_paths.items()
        },
        "metadata": {frame: str(metadata_paths[str(frame)]) for frame in keyframes},
        "frames": frames,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.publish_dir is not None:
        args.publish_dir.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(keyframes, start=2):
            source = args.output_dir / f"frame_{frame:06d}" / "all_strategies_contact_sheet_v8_video_matched.png"
            destination = args.publish_dir / (
                f"v8_{args.task}_{args.episode_id}_{index:02d}_keyframe_{frame:06d}_candidates_2x3_physical_targets.png"
            )
            if destination.exists() or destination.is_symlink():
                if not args.overwrite:
                    raise FileExistsError(destination)
                destination.unlink()
            destination.symlink_to(source)
        published_manifest = args.publish_dir / f"v8_{args.task}_{args.episode_id}_candidate_sheets_manifest.json"
        if published_manifest.exists() and not args.overwrite:
            raise FileExistsError(published_manifest)
        shutil.copy2(manifest_path, published_manifest)
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, KeyError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}")
        raise SystemExit(1)
