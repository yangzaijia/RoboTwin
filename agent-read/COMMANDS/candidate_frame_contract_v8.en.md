# V8 physical-axis candidate execution for Piper

## Frames and solver

- Input `robot_replay`: canonical blue `+Z` is candidate approach.
- Output `anygrasp_raw`: Piper red `+X` is physical approach, green `+Y` is jaw opening, and blue `+Z` is camera-back.
- `swap_red_blue_keep_green` only changes the candidate target basis.
- `piper_apply_curobo_to_sapien_link_rotation=1` only adapts the solver-URDF and renderer-URDF link6 model frames. Both transforms must remain enabled.
- The current comparison performs no IK-feasible reranking and preserves raw-candidate failures under a strict 30-degree orientation gate.

## Parameter template (documentation only; not directly runnable)

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

`execute_partial_cartesian_plan` already defaults to `0`. Do not pass `--execute_partial_cartesian_plan`; in this wrapper it is a value-less flag that only enables the feature.

## Runnable raw-Orientation example for one episode

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

## Generated one-episode results

- Orientation: `paper_v8_physical_axes_orientation_raw_20260720/pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4`
- Fused: `paper_v8_physical_axes_fused_raw_20260720/pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4`
- Top-score: `paper_v8_physical_axes_topscore_raw_20260720/pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4`
- 2x2: `/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v8_physical_axes_raw_strategy_videos/candidate_retarget_grid_2x2_physical_axes_raw_v8.mp4`

The 2x2 preserves native speed. Orientation/Fused end at 15.2 s and Top-score at 10.2 s, then freeze to the 21.4 s common timeline rather than stretching failed execution. The OursV2 tile is explicitly labeled as a historical 180-degree reach-tolerance result, not strict orientation-IK success.

## 6 tasks x 2 episodes tmux batch

The batch first generates isolated `approach_axis` previews for the fixed 12 episodes, executes raw Orientation, Fused, and Top-score candidates, then composes a native-speed 2x2 per episode. A planning failure is recorded and the batch continues without candidate fallback.

```bash
cd /home/zaijia001/ssd/RoboTwin && \
bash code_painting/run_v8_physical_axes_raw_batch_6x2.sh --gpu 2 --dry-run
```

Background launch template:

```bash
tmux new-session -d -s v8_raw_axes_6x2_20260720 \
  "cd /home/zaijia001/ssd/RoboTwin && bash code_painting/run_v8_physical_axes_raw_batch_6x2.sh --gpu 2"
```

The first batch root, `/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/v8_physical_axes_raw_batch_6x2_20260720/`, is retained only as failure evidence. All 12 compositions hit the old 300-second timeout, while the old wrapper ignored the return code and incorrectly wrote `DONE`; that directory contains no usable 2x2 MP4.

Runnable recomposition command that reuses all 36 generated strategy videos and writes a new output root:

```bash
cd /home/zaijia001/ssd/RoboTwin && \
bash code_painting/run_v8_physical_axes_raw_batch_6x2.sh \
  --compose-only \
  --source-run-tag v8_physical_axes_raw_batch_6x2_20260720 \
  --run-tag v8_physical_axes_raw_batch_6x2_20260721_recomposed
```

The corrected wrapper writes `_run/DONE` only after all 12 MP4s, per-episode manifests, `execution_status_v8.json` files, and full decodes succeed. On failure it writes `_run/FAILED` and exits nonzero; `_run/compose_status.tsv` records each episode. The corrected batch root is `/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/v8_physical_axes_raw_batch_6x2_20260721_recomposed/`.

Composition inside tmux must use `timeout --foreground ... </dev/null`. Plain `timeout` places FFmpeg in a non-foreground process group; when FFmpeg reads terminal control input it receives `SIGTTIN` and enters `T` (stopped) state, which superficially looks like a slow encode timeout.

Tile status labels follow actual `reached` state: a failure-free execution is `STRICT PASS`; a failed run whose action reached is `ACTION REACHED`; a skipped or missed action is `ACTION NOT REACHED`. Merely having an `action` key in the summary does not mean that action executed successfully.

## Flat publication of the 6x2 paper assets

Naming: videos use `{task}_{id}_00_retarget_2x2_v8.mp4`; six-panel images use `{task}_{id}_{order}_keyframe_{frame}_strategies_2x3_legacy_v3.png`. Filename sorting keeps each episode's video and keyframe sheets adjacent.

Documentation template (not directly runnable):

```bash
python code_painting/publish_v8_flat_qualitative_assets.py \
  --source-video-root <STRUCTURED_V8_VIDEO_ROOT> \
  --preview-root <V8_PREVIEW_ROOT> \
  --metadata-root <LEGACY_V3_METADATA_ROOT> \
  --output-root <NEW_FLAT_RELEASE_ROOT> \
  [--move-videos] [--dry-run]
```

Runnable formal commands:

```bash
source /home/zaijia001/ssd/miniconda3/etc/profile.d/conda.sh
conda activate RoboTwin_bw
cd /home/zaijia001/ssd/RoboTwin
python code_painting/publish_v8_flat_qualitative_assets.py --dry-run --move-videos
python code_painting/publish_v8_flat_qualitative_assets.py --move-videos
```

`--move-videos` moves all 12 formal MP4s into the flat release and creates symbolic links at their former structured paths, keeping existing manifest paths valid. The 38 PNGs are real 2-row x 3-column sheets, but intentionally use the previous canonical/V3 approach-axis debug semantics requested for this release; they must not be described as current Piper physical-axis V8 debug images. The default output is `/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/v8_6x2_flat_release_20260721/`.
