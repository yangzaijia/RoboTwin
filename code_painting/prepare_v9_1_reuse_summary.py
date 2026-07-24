#!/usr/bin/env python3
"""Prepare fixed V8/OursV2 targets for the isolated V9.1 IK comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

from piper_canonical_tcp_v1.frame_contract import (
    R_CGRASP_RTCP,
    matrix_to_pose_wxyz,
    pose_wxyz_to_matrix,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--strategy",
        choices=["orientation", "fused", "topscore", "oursv2"],
        required=True,
    )
    parser.add_argument(
        "--logic",
        choices=["canonical", "oursv2-5"],
        required=True,
    )
    return parser.parse_args()


def shift_local(pose_wxyz: list[float], axis: int, distance_m: float) -> np.ndarray:
    transform = pose_wxyz_to_matrix(pose_wxyz)
    transform[:3, 3] += transform[:3, axis] * float(distance_m)
    return matrix_to_pose_wxyz(transform)


def human_center_to_rtcp(pose_wxyz: list[float], historical_retreat_m: float) -> np.ndarray:
    # Historical OursV2 stores link6/planner = human center - 0.14 m local +Z.
    source_center = pose_wxyz_to_matrix(
        shift_local(pose_wxyz, axis=2, distance_m=historical_retreat_m)
    )
    source_center[:3, :3] = source_center[:3, :3] @ R_CGRASP_RTCP
    return matrix_to_pose_wxyz(source_center)


def selected_entries(summary: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[int] = set()
    containers: list[Any] = [summary.get("selected_candidates", [])]
    containers.extend(
        (summary.get("selected_candidates_by_executed_arm") or {}).values()
    )
    for container in containers:
        for entry in container or []:
            if not isinstance(entry, dict) or id(entry) in seen:
                continue
            seen.add(id(entry))
            entries.append(entry)
    return entries


def transform_entry(
    entry: dict[str, Any],
    transform: Callable[[list[float]], np.ndarray],
    contract: str,
) -> None:
    pose = transform(list(entry["pose_world_wxyz"]))
    entry["v9_1_source_pose_world_wxyz"] = list(entry["pose_world_wxyz"])
    entry["pose_world_wxyz"] = pose.tolist()
    entry["raw_pose_world_wxyz"] = pose.tolist()
    entry["v9_1_target_contract"] = contract


def main() -> int:
    args = parse_args()
    summary = json.loads(args.input.read_text(encoding="utf-8"))
    historical_retreat_m = float(summary.get("human_replay_target_retreat_m", 0.14))

    if args.strategy == "oursv2":
        if args.logic == "canonical":
            transform = lambda pose: human_center_to_rtcp(pose, historical_retreat_m)
            contract = (
                "historical OursV2 target +0.14m local +Z -> human center; "
                "CGRASP_HUMAN axes -> canonical RTCP axes; no final retreat"
            )
            final_retreat_m = 0.0
        else:
            transform = lambda pose: shift_local(pose, axis=2, distance_m=-0.05)
            contract = (
                "historical OursV2 target already includes 0.14m local +Z retreat; "
                "add 0.05m in the same retreat direction (0.19m total)"
            )
            final_retreat_m = historical_retreat_m + 0.05
    elif args.logic == "canonical":
        transform = lambda pose: shift_local(pose, axis=0, distance_m=0.05)
        contract = (
            "undo V8 -0.05m Piper local +X candidate offset; "
            "preserve physical axes and candidate center as canonical RTCP"
        )
        final_retreat_m = 0.0
    else:
        transform = lambda pose: np.asarray(pose, dtype=np.float64)
        contract = (
            "preserve V8 physical-axis target with -0.05m Piper local +X "
            "candidate offset already materialized"
        )
        final_retreat_m = 0.05

    entries = selected_entries(summary)
    if not entries:
        raise ValueError(f"No selected candidates in {args.input}")
    for entry in entries:
        transform_entry(entry, transform, contract)

    summary["v9_1_prepared_input"] = {
        "source_summary": str(args.input.resolve()),
        "strategy": args.strategy,
        "logic": args.logic,
        "transform": contract,
        "historical_oursv2_target_retreat_m": (
            historical_retreat_m if args.strategy == "oursv2" else None
        ),
        "final_target_retreat_or_offset_m": final_retreat_m,
        "pregrasp_retreat_m": 0.12,
        "open_gripper_normalized": 1.0,
        "close_gripper_normalized": 0.3,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
