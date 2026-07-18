# Piper AnyGrasp red-forward camera-back-up V6 commands

## Current axis contract

- Red `+X`: gripper forward/approach.
- Green `+Y`: parallel-jaw opening.
- Blue `+Z`: normal of the forward--opening plane.
- Only the 180-degree finger-swap roll about red `+X` is allowed; require `-blue` toward world up.
- Camera-up is a hard constraint at every keyframe. Rotation continuity is optimized only after that constraint is satisfied.

The V5 local-Z-forward and `-X` mount-normal conclusions are withdrawn.

## Parameter template (documentation only; not directly runnable)

```bash
bash /home/zaijia001/ssd/RoboTwin/code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --tasks <TASK> --ids <EPISODE_ID> --max_per_task 1 \
  --output_root <NEW_ISOLATED_OUTPUT_ROOT> \
  --preview_root <D435_PREVIEW_ROOT> \
  --reuse_preview_candidate_group <orientation|fused> \
  --manual_candidate <K1_FRAME> left <LEFT_K1_ID> \
  --manual_candidate <K1_FRAME> right <RIGHT_K1_ID> \
  --manual_candidate <K2_FRAME> left <LEFT_K2_ID> \
  --manual_candidate <K2_FRAME> right <RIGHT_K2_ID> \
  --trajectory_mode joint_interp --joint_interp_waypoints 40 \
  --execute_interp_steps 40 --joint_target_wait_steps 300 \
  --ik_num_seeds 64 --ik_solution_selection joint_continuity \
  --piper_apply_global_trans_to_ik 1 \
  --piper_apply_curobo_to_sapien_link_rotation 1 \
  --candidate_keep_camera_up 1 \
  --candidate_camera_forward_axis local_x \
  --candidate_camera_top_axis z --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m -0.05 \
  --candidate_target_local_z_offset_m 0 \
  --approach_axis local_x --approach_offset_m 0.12 \
  --debug_gripper_actor_forward_axis local_x \
  --disable_execution_collisions --target_axes_only \
  --piper_calibration_bundle /home/zaijia001/ssd/RoboTwin/calibration_bundle_piper_new_table_0515.json
```

## Runnable example: pick_diverse_bottles/id0

```bash
cd /home/zaijia001/ssd/RoboTwin && \
bash code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --tasks pick_diverse_bottles --ids 0 --max_per_task 1 \
  --output_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v6_red_forward_camera_back_up_final_l6r5_20260718 \
  --preview_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_h2o_preview_d435_robot_frame_approach_axis_v3_full \
  --reuse_preview_candidate_group orientation \
  --manual_candidate 38 left 16 --manual_candidate 38 right 18 \
  --manual_candidate 78 left 6 --manual_candidate 78 right 5 \
  --trajectory_mode joint_interp --joint_interp_waypoints 40 \
  --execute_interp_steps 40 --joint_command_scene_steps 10 \
  --settle_steps 30 --joint_target_wait_steps 300 --reach_rot_tol_deg 30 \
  --ik_max_position_threshold_m 0.02 --ik_max_rotation_threshold_rad 0.8 \
  --ik_num_seeds 64 --ik_solution_selection joint_continuity \
  --piper_apply_global_trans_to_ik 1 \
  --piper_apply_curobo_to_sapien_link_rotation 1 \
  --candidate_keep_camera_up 1 \
  --candidate_camera_forward_axis local_x \
  --candidate_camera_top_axis z --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m -0.05 --candidate_target_local_z_offset_m 0 \
  --approach_axis local_x --approach_offset_m 0.12 \
  --debug_gripper_actor_forward_axis local_x \
  --disable_execution_collisions --target_axes_only \
  --piper_calibration_bundle /home/zaijia001/ssd/RoboTwin/calibration_bundle_piper_new_table_0515.json
```

This episode uses K1 `L16/R18` and K2 `L6/R5`. Orientation, Fused, and constrained Top-score all fall back to this same feasible set after camera-back-up, IK, and joint-limit constraints.

## Grid and validation

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python compose_pipeline_grid.py \
  --config outputs/keyframe_candidates/pick_diverse_bottles/id0/v6_red_forward_camera_back_up_candidate_videos/candidate_retarget_grid_2x2_red_forward_camera_back_up_v6_config.json
```

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python tests/test_anygrasp_camera_up.py && \
python -m py_compile code_painting/plan_anygrasp_keyframes_r1.py && \
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,pix_fmt,avg_frame_rate,nb_frames:format=duration \
  /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v6_red_forward_camera_back_up_candidate_videos/candidate_retarget_grid_2x2_red_forward_camera_back_up_v6.mp4
```

Object collisions are disabled. This video validates candidate frames, camera-side orientation, and retargeting; it is not a physical grasp-success benchmark.
