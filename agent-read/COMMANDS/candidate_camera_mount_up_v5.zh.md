# Calibrated camera-mount-up V5 命令

## 用途与轴定义

用于 canonical local-Z-forward AnyGrasp 候选的 Piper 定性 replay。局部轴颜色为 X 红、Y 绿、Z 蓝；0515 腕部相机位于 link6 local `-X` 一侧，所以 mount-up 使用 `-X·world_Z > 0`。V5 不修改 OursV2/V4，并写入独立目录。

## 参数模板（说明用，不可直接运行）

```bash
bash /home/zaijia001/ssd/RoboTwin/code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --tasks <TASK> --ids <EPISODE_ID> --max_per_task 1 \
  --output_root <NEW_ISOLATED_OUTPUT_ROOT> \
  --preview_root <CANONICAL_PREVIEW_ROOT> \
  --reuse_preview_candidate_group <orientation|fused> \
  --manual_candidate <FRAME> <left|right> <CANDIDATE_ID> \
  --trajectory_mode joint_interp --joint_interp_waypoints 40 \
  --execute_interp_steps 40 --joint_command_scene_steps 10 \
  --joint_target_wait_steps 300 --reach_rot_tol_deg 30 \
  --ik_max_position_threshold_m 0.02 --ik_max_rotation_threshold_rad 0.8 \
  --ik_num_seeds 64 --ik_solution_selection <pose_error|joint_continuity> \
  --piper_apply_global_trans_to_ik 1 \
  --piper_apply_curobo_to_sapien_link_rotation 1 \
  --candidate_keep_camera_up 1 \
  --candidate_camera_forward_axis local_z \
  --candidate_camera_top_axis x --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m 0 \
  --candidate_target_local_z_offset_m -0.05 \
  --approach_axis local_z --approach_offset_m 0.12 \
  --debug_gripper_actor_forward_axis local_z \
  --disable_execution_collisions --target_axes_only \
  --piper_calibration_bundle /home/zaijia001/ssd/RoboTwin/calibration_bundle_piper_new_table_0515.json
```

`--disable_execution_collisions` 只适合本论文定性候选重定向可视化；不要把该输出当作物理抓取成功率。

## 可运行示例：Orientation/Fused

本 episode 两种排序在 mount-up/IK/关节限位约束后使用相同候选：K1 `L16/R9`、K2 `L19/R16`，因此 Fused 格复用同一执行视频。

```bash
cd /home/zaijia001/ssd/RoboTwin && bash code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --tasks pick_diverse_bottles --ids 0 --max_per_task 1 \
  --output_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v5_orientation_camera_mount_up_linkmatch_20260717 \
  --preview_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_h2o_preview_d435_robot_frame_approach_axis_v3_full \
  --reuse_preview_candidate_group orientation \
  --manual_candidate 38 left 16 --manual_candidate 38 right 9 \
  --manual_candidate 78 left 19 --manual_candidate 78 right 16 \
  --trajectory_mode joint_interp --joint_interp_waypoints 40 \
  --execute_interp_steps 40 --joint_command_scene_steps 10 \
  --settle_steps 30 --joint_target_wait_steps 300 --reach_rot_tol_deg 30 \
  --ik_max_position_threshold_m 0.02 --ik_max_rotation_threshold_rad 0.8 \
  --ik_num_seeds 64 --ik_solution_selection pose_error \
  --piper_apply_global_trans_to_ik 1 \
  --piper_apply_curobo_to_sapien_link_rotation 1 \
  --candidate_keep_camera_up 1 --candidate_camera_forward_axis local_z \
  --candidate_camera_top_axis x --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m 0 --candidate_target_local_z_offset_m -0.05 \
  --approach_axis local_z --approach_offset_m 0.12 \
  --debug_gripper_actor_forward_axis local_z \
  --disable_execution_collisions --target_axes_only \
  --piper_calibration_bundle /home/zaijia001/ssd/RoboTwin/calibration_bundle_piper_new_table_0515.json
```

## 可运行示例：Top-score + feasible constraint

Raw K2-left `#0` 会把 J5 推到上限；正式 V5 使用同一 Top-score 排序中下一项 feasible `#3`。候选为 K1 `L1/R3`、K2 `L3/R1`。

```bash
cd /home/zaijia001/ssd/RoboTwin && bash code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --tasks pick_diverse_bottles --ids 0 --max_per_task 1 \
  --output_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v5_topscore_camera_mount_up_linkmatch_feasible_20260717 \
  --preview_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_h2o_preview_d435_robot_frame_topscore_canonical_v3_full \
  --reuse_preview_candidate_group fused \
  --manual_candidate 38 left 1 --manual_candidate 38 right 3 \
  --manual_candidate 78 left 3 --manual_candidate 78 right 1 \
  --trajectory_mode joint_interp --joint_interp_waypoints 40 \
  --execute_interp_steps 40 --joint_command_scene_steps 10 \
  --settle_steps 30 --joint_target_wait_steps 300 --reach_rot_tol_deg 30 \
  --ik_max_position_threshold_m 0.02 --ik_max_rotation_threshold_rad 0.8 \
  --ik_num_seeds 64 --ik_solution_selection joint_continuity \
  --piper_apply_global_trans_to_ik 1 \
  --piper_apply_curobo_to_sapien_link_rotation 1 \
  --candidate_keep_camera_up 1 --candidate_camera_forward_axis local_z \
  --candidate_camera_top_axis x --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m 0 --candidate_target_local_z_offset_m -0.05 \
  --approach_axis local_z --approach_offset_m 0.12 \
  --debug_gripper_actor_forward_axis local_z \
  --disable_execution_collisions --target_axes_only \
  --piper_calibration_bundle /home/zaijia001/ssd/RoboTwin/calibration_bundle_piper_new_table_0515.json
```

## 四宫格 dry-run 与正式合成

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python compose_pipeline_grid.py \
  --config outputs/keyframe_candidates/pick_diverse_bottles/id0/v5_camera_mount_up_candidate_videos/candidate_retarget_grid_2x2_camera_mount_up_v5_config.json \
  --dry-run
```

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python compose_pipeline_grid.py \
  --config outputs/keyframe_candidates/pick_diverse_bottles/id0/v5_camera_mount_up_candidate_videos/candidate_retarget_grid_2x2_camera_mount_up_v5_config.json
```

成品：

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v5_camera_mount_up_candidate_videos/candidate_retarget_grid_2x2_camera_mount_up_v5.mp4
```

## 最小验证

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python tests/test_anygrasp_camera_up.py && \
bash -n code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh && \
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,pix_fmt,avg_frame_rate,nb_frames:format=duration \
  /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v5_camera_mount_up_candidate_videos/candidate_retarget_grid_2x2_camera_mount_up_v5.mp4
```
