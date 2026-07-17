from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "code_painting"))

import plan_anygrasp_keyframes_r1 as planner  # noqa: E402


def test_legacy_local_x_forward_behavior_is_preserved() -> None:
    rotation = np.diag([1.0, -1.0, -1.0])
    chosen, debug = planner.constrain_roll_keep_top_axis_up(
        rotation,
        top_axis="z",
        forward_axis="local_x",
    )

    np.testing.assert_allclose(chosen, np.eye(3), atol=1e-12)
    assert debug["camera_up_flip_applied"] == 1
    assert debug["original_top_axis_up_dot"] == -1.0
    assert debug["forward_axis_change_deg"] == 0.0


def test_canonical_local_z_forward_flips_plane_normal_only() -> None:
    # Columns are local X (downward plane normal), local Y (jaw opening),
    # and local Z (forward). The canonical 180-degree finger swap must flip
    # X/Y while leaving the forward Z column exactly unchanged.
    rotation = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    chosen, debug = planner.constrain_roll_keep_top_axis_up(
        rotation,
        top_axis="x",
        forward_axis="local_z",
    )

    assert debug["camera_up_flip_applied"] == 1
    assert debug["original_top_axis_up_dot"] == -1.0
    assert debug["forward_axis_change_deg"] == 0.0
    np.testing.assert_allclose(chosen[:, 2], rotation[:, 2], atol=1e-12)
    assert planner.top_axis_up_dot(chosen, "x") == 1.0


def test_canonical_upward_plane_normal_is_left_unchanged() -> None:
    rotation = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    chosen, debug = planner.constrain_roll_keep_top_axis_up(
        rotation,
        top_axis="x",
        forward_axis="local_z",
    )

    np.testing.assert_allclose(chosen, rotation, atol=1e-12)
    assert debug["camera_up_flip_applied"] == 0
    assert debug["forward_axis_change_deg"] == 0.0


def test_canonical_negative_x_plane_normal_uses_opposite_equivalent_branch() -> None:
    rotation = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    chosen, debug = planner.constrain_roll_keep_top_axis_up(
        rotation,
        top_axis="x",
        top_axis_sign=-1,
        forward_axis="local_z",
    )

    assert debug["original_top_axis_up_dot"] == -1.0
    assert debug["camera_up_flip_applied"] == 1
    assert debug["forward_axis_change_deg"] == 0.0
    assert planner.top_axis_up_dot(chosen, "x", -1) == 1.0
    np.testing.assert_allclose(chosen[:, 2], rotation[:, 2], atol=1e-12)


def test_first_keyframe_postprocess_preserves_raw_flip_provenance() -> None:
    rotation = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    quat_wxyz = planner.base.quat_xyzw_to_wxyz(planner.R.from_matrix(rotation).as_quat())
    raw_pose = np.concatenate([np.zeros(3, dtype=np.float64), quat_wxyz])
    candidate = planner.CandidatePose(
        candidate_idx=7,
        score=1.0,
        translation_cam=np.zeros(3, dtype=np.float64),
        rotation_cam=rotation,
        width_m=0.08,
        depth_m=0.04,
        raw_pose_world_wxyz=raw_pose,
        raw_pose_world_matrix=planner.pose_wxyz_to_matrix(raw_pose),
        pose_world_wxyz=raw_pose.copy(),
        pose_world_matrix=planner.pose_wxyz_to_matrix(raw_pose),
        nearest_object="object",
        nearest_object_distance_m=0.0,
        rotation_distance_deg=0.0,
        top_axis_up_dot=-1.0,
        original_top_axis_up_dot=-1.0,
        camera_up_flip_applied=0,
        forward_axis_change_deg=0.0,
    )
    selected = planner.SelectedKeyframe(
        source_frame=38,
        arm="left",
        candidate=candidate,
        hand_rotation_cam=np.eye(3, dtype=np.float64),
    )
    args = SimpleNamespace(
        candidate_keep_camera_up=1,
        candidate_camera_forward_axis="local_z",
        candidate_camera_top_axis="x",
        candidate_camera_top_axis_sign=1,
        candidate_target_local_x_offset_m=0.0,
        candidate_target_local_z_offset_m=0.0,
    )

    result = planner.postprocess_selected_keyframe_rolls([selected], args)[0].candidate

    assert result.original_top_axis_up_dot == -1.0
    assert result.top_axis_up_dot == 1.0
    assert result.camera_up_flip_applied == 1
    assert result.forward_axis_change_deg == 0.0
    np.testing.assert_allclose(result.pose_world_matrix[:, 2], candidate.raw_pose_world_matrix[:, 2], atol=1e-12)


if __name__ == "__main__":
    test_legacy_local_x_forward_behavior_is_preserved()
    test_canonical_local_z_forward_flips_plane_normal_only()
    test_canonical_upward_plane_normal_is_left_unchanged()
    test_canonical_negative_x_plane_normal_uses_opposite_equivalent_branch()
    test_first_keyframe_postprocess_preserves_raw_flip_provenance()
    print("camera-up regression tests: 5 passed")
