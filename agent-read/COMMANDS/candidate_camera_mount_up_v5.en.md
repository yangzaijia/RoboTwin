# Calibrated camera-mount-up V5 commands

> **Withdrawn; historical reproduction only.** V5 inferred orientation from camera mount translation and used the wrong `local_z` forward axis. Do not use this page for new results; use `candidate_camera_mount_up_v6.en.md`.

## Purpose and axes

Use these commands for qualitative Piper replay of canonical local-Z-forward AnyGrasp candidates. Debug axes are X red, Y green, Z blue. The calibrated 0515 wrist camera is on link6 local `-X`, so mount-up is `-X dot world_Z > 0`. V5 leaves OursV2/V4 untouched and writes to isolated roots.

## Parameter template (documentation only; not directly runnable)

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

`--disable_execution_collisions` is only for this qualitative candidate-retargeting figure and must not be presented as physical grasp success.

## Runnable Orientation/Fused example

The two rankings share the same mount-up/IK/joint-limit-feasible candidates for this episode: K1 `L16/R9`, K2 `L19/R16`. The Fused tile therefore reuses the same execution.

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

## Runnable constrained Top-score example

Raw K2-left `#0` saturates J5. Formal V5 uses the next feasible candidate `#3` in the same Top-score ranking. Candidates are K1 `L1/R3`, K2 `L3/R1`.

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

## Grid dry run and composition

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

Deliverable:

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v5_camera_mount_up_candidate_videos/candidate_retarget_grid_2x2_camera_mount_up_v5.mp4
```

## Minimal validation

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python tests/test_anygrasp_camera_up.py && \
bash -n code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh && \
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,pix_fmt,avg_frame_rate,nb_frames:format=duration \
  /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v5_camera_mount_up_candidate_videos/candidate_retarget_grid_2x2_camera_mount_up_v5.mp4
```
