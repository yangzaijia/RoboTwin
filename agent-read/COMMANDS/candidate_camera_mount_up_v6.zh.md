# Piper AnyGrasp red-forward camera-back-up V6 命令

## 当前轴规则

- 红 `+X`：夹爪前进/approach。
- 绿 `+Y`：平行两指开合。
- 蓝 `+Z`：前进--开合平面法向。
- 只允许绕红 `+X` 做 180° 两指等价翻转，并要求 `-蓝轴` 朝 world up。
- camera-up 是每个关键帧的硬约束；满足后才优化相邻关键帧旋转连续性。

V5 的 local-Z-forward、`-X` mount-normal 结论已撤销。

## 参数模板（说明用，不可直接运行）

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

## 可运行示例：pick_diverse_bottles/id0

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

本 episode 的候选是 K1 `L16/R18`、K2 `L6/R5`。Orientation、Fused 与 constrained Top-score 在 camera-back-up、IK 和关节限位约束后都回退到同一组可达 ID。

## 四宫格与验证

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

物体碰撞为关闭状态；该视频只验证候选坐标、相机上侧与 retargeting，不是物理抓取成功率。
