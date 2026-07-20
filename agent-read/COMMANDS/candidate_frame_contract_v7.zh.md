# V7 候选坐标契约与单次 link6 映射

## 参数模板（说明用，不可直接运行）

```bash
bash code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --tasks <TASK> --ids <ID> --output_root <NEW_OUTPUT_ROOT> \
  --preview_root <ROBOT_REPLAY_PREVIEW_ROOT> \
  --candidate_input_frame_contract robot_replay \
  --candidate_frame_contract robot_replay \
  --candidate_orientation_remap_label identity \
  --candidate_keep_camera_up 1 \
  --candidate_camera_forward_axis local_z \
  --candidate_camera_top_axis x --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m 0 \
  --candidate_target_local_z_offset_m -0.05 \
  --approach_axis local_z --debug_gripper_actor_forward_axis local_z \
  --piper_apply_global_trans_to_ik 1 \
  --piper_apply_curobo_to_sapien_link_rotation 1
```

不要再加 `swap_red_blue_keep_green`；IK 边界已经包含一次 link6 adapter。

## 已验证可运行示例

```bash
cd /home/zaijia001/ssd/RoboTwin && \
bash code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --gpu 2 --tasks pick_diverse_bottles --ids 0 \
  --output_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v7_single_mapping_consistent_20260720 \
  --preview_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_h2o_preview_d435_robot_frame_approach_axis_v3_full \
  --reuse_preview_candidate_group orientation \
  --candidate_input_frame_contract robot_replay --candidate_frame_contract robot_replay \
  --candidate_orientation_remap_label identity \
  --candidate_keep_camera_up 1 --candidate_camera_forward_axis local_z \
  --candidate_camera_top_axis x --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m 0 --candidate_target_local_z_offset_m -0.05 \
  --approach_axis local_z --debug_gripper_actor_forward_axis local_z \
  --manual_candidate 38 left 16 --manual_candidate 38 right 9 \
  --manual_candidate 78 left 19 --manual_candidate 78 right 16 \
  --trajectory_mode joint_interp --joint_interp_waypoints 40 \
  --execute_interp_steps 40 --joint_command_scene_steps 10 \
  --settle_steps 30 --joint_target_wait_steps 300 --reach_error_pose_source ee \
  --reach_rot_tol_deg 30 --ik_max_position_threshold_m 0.02 \
  --ik_max_rotation_threshold_rad 0.8 --ik_num_seeds 64 \
  --ik_solution_selection joint_continuity \
  --piper_apply_global_trans_to_ik 1 --piper_apply_curobo_to_sapien_link_rotation 1 \
  --disable_execution_collisions --target_axes_only \
  --piper_calibration_bundle /home/zaijia001/ssd/RoboTwin/calibration_bundle_piper_new_table_0515.json
```

图片复现使用 `code_painting/export_v7_candidate_frame_consistency.py` 和 `paper_qualitative_assets/piper_v7_candidate_frame_consistency_id0.json`。正式输出路径记录在对应 manifest。
