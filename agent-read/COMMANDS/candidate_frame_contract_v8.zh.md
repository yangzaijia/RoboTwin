# V8 Piper 物理轴候选执行

## 坐标与求解器

- 输入 `robot_replay`：canonical 蓝 `+Z` 是候选 approach。
- 输出 `anygrasp_raw`：Piper 红 `+X` 是实体 approach，绿 `+Y` 是开合，蓝 `+Z` 是相机背向。
- `swap_red_blue_keep_green` 只负责候选目标换基。
- `piper_apply_curobo_to_sapien_link_rotation=1` 只负责求解 URDF 与渲染 URDF 的 link6 模型帧适配。两者必须同时保留。
- 当前不做 IK-feasible 重排；严格 30° 姿态门限下保留原始候选失败。

## 参数模板（说明用，不可直接运行）

```bash
bash code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --tasks <TASK> --ids <ID> --output_root <NEW_OUTPUT_ROOT> \
  --preview_root <ROBOT_REPLAY_PREVIEW_ROOT> \
  --reuse_preview_candidate_group <orientation|fused> \
  --candidate_input_frame_contract robot_replay \
  --candidate_frame_contract anygrasp_raw \
  --candidate_orientation_remap_label swap_red_blue_keep_green \
  --candidate_keep_camera_up 1 \
  --candidate_camera_forward_axis local_x \
  --candidate_camera_top_axis z --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m -0.05 --candidate_target_local_z_offset_m 0 \
  --approach_axis local_x --debug_gripper_actor_forward_axis local_x \
  --piper_apply_global_trans_to_ik 1 \
  --piper_apply_curobo_to_sapien_link_rotation 1 \
  --reach_rot_tol_deg 30
```

`execute_partial_cartesian_plan` 默认即为 `0`；不要传 `--execute_partial_cartesian_plan`，该 wrapper 参数是只用于开启功能的无值 flag。

## 单集 Orientation 原始候选示例

```bash
cd /home/zaijia001/ssd/RoboTwin && \
bash code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh \
  --gpu 2 --tasks pick_diverse_bottles --ids 0 \
  --output_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v8_physical_axes_orientation_raw_20260720 \
  --preview_root /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_h2o_preview_d435_robot_frame_approach_axis_v3_full \
  --reuse_preview_candidate_group orientation \
  --candidate_input_frame_contract robot_replay --candidate_frame_contract anygrasp_raw \
  --candidate_orientation_remap_label swap_red_blue_keep_green \
  --candidate_keep_camera_up 1 --candidate_camera_forward_axis local_x \
  --candidate_camera_top_axis z --candidate_camera_top_axis_sign -1 \
  --candidate_target_local_x_offset_m -0.05 --candidate_target_local_z_offset_m 0 \
  --approach_axis local_x --debug_gripper_actor_forward_axis local_x \
  --manual_candidate 38 left 16 --manual_candidate 38 right 5 \
  --manual_candidate 78 left 14 --manual_candidate 78 right 16 \
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

## 已生成的单集结果

- Orientation：`paper_v8_physical_axes_orientation_raw_20260720/pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4`
- Fused：`paper_v8_physical_axes_fused_raw_20260720/pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4`
- Top-score：`paper_v8_physical_axes_topscore_raw_20260720/pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4`
- 2×2：`/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v8_physical_axes_raw_strategy_videos/candidate_retarget_grid_2x2_physical_axes_raw_v8.mp4`

2×2 保持原始播放速度；15.2 秒的 Orientation/Fused 和 10.2 秒的 Top-score 冻结末帧到 21.4 秒，不拉伸失败过程。OursV2 格明确标为历史 `180°` reach tolerance，不能作为严格姿态 IK 成功。

## 6 tasks × 2 episodes tmux 批处理

批处理先为固定 12 集生成独立的 `approach_axis` preview，再依次执行 Orientation、Fused、Top-score 原始候选，最后为每集生成原速 2×2。任一规划失败只写入状态并继续，不做候选 fallback。

```bash
cd /home/zaijia001/ssd/RoboTwin && \
bash code_painting/run_v8_physical_axes_raw_batch_6x2.sh --gpu 2 --dry-run
```

后台启动模板：

```bash
tmux new-session -d -s v8_raw_axes_6x2_20260720 \
  "cd /home/zaijia001/ssd/RoboTwin && bash code_painting/run_v8_physical_axes_raw_batch_6x2.sh --gpu 2"
```

首次批次根目录 `/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/v8_physical_axes_raw_batch_6x2_20260720/` 只保留为失败审计：12 次合成都触发旧版 300 秒 timeout，但旧 wrapper 忽略返回码并错误写入 `DONE`，该目录没有可用的 2×2 MP4。

只复用已生成的 36 条策略视频、写入新目录的可运行重合成命令：

```bash
cd /home/zaijia001/ssd/RoboTwin && \
bash code_painting/run_v8_physical_axes_raw_batch_6x2.sh \
  --compose-only \
  --source-run-tag v8_physical_axes_raw_batch_6x2_20260720 \
  --run-tag v8_physical_axes_raw_batch_6x2_20260721_recomposed
```

修正版只有在 12/12 个 MP4、每集 manifest、`execution_status_v8.json` 和完整解码全部成功时才写 `_run/DONE`。失败时写 `_run/FAILED` 并以非零状态退出；`_run/compose_status.tsv` 记录逐集状态。新批次根目录为 `/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/v8_physical_axes_raw_batch_6x2_20260721_recomposed/`。

tmux 中的 compose 必须使用 `timeout --foreground ... </dev/null`。普通 `timeout` 会把 FFmpeg 放进非前台进程组；FFmpeg读取终端控制输入时会收到 `SIGTTIN` 并进入 `T`（stopped）状态，看起来像编码超时。

格子状态标签以真实 `reached` 为准：严格无失败显示 `STRICT PASS`；有失败但 action 到达显示 `ACTION REACHED`；action 被跳过或未到达统一显示 `ACTION NOT REACHED`。不能仅因 summary 中存在 `action` 键就标为已执行。
