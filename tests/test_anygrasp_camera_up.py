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


def test_later_keyframe_keeps_camera_up_before_rotation_continuity() -> None:
    # Raw identity is perfectly continuous with the previous keyframe but has
    # camera-back (-Z) pointing down.  Its 180-degree roll-equivalent branch is
    # discontinuous but camera-up, so the physical constraint must win.
    rotation = np.eye(3, dtype=np.float64)
    quat_wxyz = planner.base.quat_xyzw_to_wxyz(planner.R.from_matrix(rotation).as_quat())
    raw_pose = np.concatenate([np.zeros(3, dtype=np.float64), quat_wxyz])
    candidate = planner.CandidatePose(
        candidate_idx=8,
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
    args = SimpleNamespace(
        candidate_camera_forward_axis="local_x",
        candidate_camera_top_axis="z",
        candidate_camera_top_axis_sign=-1,
        candidate_target_local_x_offset_m=0.0,
        candidate_target_local_z_offset_m=0.0,
    )

    result = planner.choose_roll_variant_with_previous(np.eye(3), candidate, args)

    assert result.top_axis_up_dot == 1.0
    assert result.camera_up_flip_applied == 1
    assert result.forward_axis_change_deg == 0.0
    np.testing.assert_allclose(result.pose_world_matrix[:3, 0], rotation[:, 0], atol=1e-12)


def test_robot_replay_contract_accepts_consistent_local_z_chain() -> None:
    args = SimpleNamespace(
        candidate_frame_contract="robot_replay",
        candidate_camera_forward_axis="local_z",
        candidate_camera_top_axis="x",
        approach_axis="local_z",
        debug_gripper_actor_forward_axis="local_z",
        candidate_target_local_x_offset_m=0.0,
    )

    planner.validate_candidate_frame_contract(args)


def test_robot_replay_contract_rejects_v6_mixed_local_x_chain() -> None:
    args = SimpleNamespace(
        candidate_frame_contract="robot_replay",
        candidate_camera_forward_axis="local_x",
        candidate_camera_top_axis="z",
        approach_axis="local_x",
        debug_gripper_actor_forward_axis="local_x",
        candidate_target_local_x_offset_m=-0.05,
    )

    try:
        planner.validate_candidate_frame_contract(args)
    except ValueError as exc:
        message = str(exc)
        assert "candidate_frame_contract=robot_replay is inconsistent" in message
        assert "candidate_camera_forward_axis='local_x'" in message
        assert "candidate_target_local_x_offset_m=-0.05" in message
    else:
        raise AssertionError("V6 mixed local-X chain must be rejected")


def test_robot_replay_contract_rejects_raw_preview_data() -> None:
    args = SimpleNamespace(
        candidate_frame_contract="robot_replay",
        candidate_input_frame_contract="robot_replay",
        candidate_orientation_remap_matrix=np.eye(3),
        candidate_orientation_remap_label="identity",
        candidate_post_rot_matrix=np.eye(3),
    )

    try:
        planner.validate_preview_candidate_frame_contract(
            args,
            {"candidate_frame_mode": "anygrasp_raw"},
        )
    except ValueError as exc:
        assert "requested_input=robot_replay, preview=anygrasp_raw" in str(exc)
    else:
        raise AssertionError("robot_replay planner must reject anygrasp_raw preview data")


def test_robot_replay_source_can_convert_to_anygrasp_piper_tcp() -> None:
    args = SimpleNamespace(
        candidate_frame_contract="anygrasp_raw",
        candidate_input_frame_contract="robot_replay",
        candidate_orientation_remap_matrix=np.array(
            [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]],
            dtype=np.float64,
        ),
        candidate_orientation_remap_label="x_from_zp_y_from_yp_z_from_xm",
        candidate_post_rot_matrix=np.eye(3),
        piper_urdfik_apply_curobo_to_sapien_link_rotation=0,
    )

    planner.validate_preview_candidate_frame_contract(
        args,
        {"candidate_frame_mode": "robot_replay"},
    )


def test_robot_replay_to_anygrasp_piper_tcp_rejects_identity_remap() -> None:
    args = SimpleNamespace(
        candidate_frame_contract="anygrasp_raw",
        candidate_input_frame_contract="robot_replay",
        candidate_orientation_remap_matrix=np.eye(3),
        candidate_orientation_remap_label="identity",
        candidate_post_rot_matrix=np.eye(3),
        piper_urdfik_apply_curobo_to_sapien_link_rotation=0,
    )

    try:
        planner.validate_preview_candidate_frame_contract(
            args,
            {"candidate_frame_mode": "robot_replay"},
        )
    except ValueError as exc:
        assert "source-to-planner remap mismatch" in str(exc)
    else:
        raise AssertionError("robot_replay source must not enter a +X-forward Piper TCP unchanged")


def test_robot_replay_to_anygrasp_rejects_second_link6_adapter() -> None:
    args = SimpleNamespace(
        candidate_frame_contract="anygrasp_raw",
        candidate_input_frame_contract="robot_replay",
        candidate_orientation_remap_matrix=np.array(
            [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]],
            dtype=np.float64,
        ),
        candidate_orientation_remap_label="x_from_zp_y_from_yp_z_from_xm",
        candidate_post_rot_matrix=np.eye(3),
        piper_urdfik_apply_curobo_to_sapien_link_rotation=1,
    )

    try:
        planner.validate_preview_candidate_frame_contract(
            args,
            {"candidate_frame_mode": "robot_replay"},
        )
    except ValueError as exc:
        assert "double frame compensation" in str(exc)
    else:
        raise AssertionError("candidate remap and link6 adapter must not apply the same frame change twice")


if __name__ == "__main__":
    test_legacy_local_x_forward_behavior_is_preserved()
    test_canonical_local_z_forward_flips_plane_normal_only()
    test_canonical_upward_plane_normal_is_left_unchanged()
    test_canonical_negative_x_plane_normal_uses_opposite_equivalent_branch()
    test_first_keyframe_postprocess_preserves_raw_flip_provenance()
    test_later_keyframe_keeps_camera_up_before_rotation_continuity()
    test_robot_replay_contract_accepts_consistent_local_z_chain()
    test_robot_replay_contract_rejects_v6_mixed_local_x_chain()
    test_robot_replay_contract_rejects_raw_preview_data()
    test_robot_replay_source_can_convert_to_anygrasp_piper_tcp()
    test_robot_replay_to_anygrasp_piper_tcp_rejects_identity_remap()
    test_robot_replay_to_anygrasp_rejects_second_link6_adapter()
    print("camera-up and frame-contract regression tests: 12 passed")
