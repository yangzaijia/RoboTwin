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

The six-panel compatibility layer `export_keyframe_candidate_comparison_v3_active_arms.py` derives active arms from real OursV2 metadata. Single-arm frames draw only LEFT or RIGHT, while dual-arm frames draw BOTH; an inactive hand must never be copied or invented to satisfy the legacy exporter's fixed dual-arm assumption. If legacy metadata lacks Orientation/Fused, only the real active arm receives a reconstructed strategy record using the same V3 approach-axis scoring.

Per-frame target objects come from that frame's V8 `object_distance_debug.json`. The publisher uses the configured `arm_target_mapping` target when its candidate partition is nonempty. If that target has no candidate and exactly one nonempty object partition remains, the sole available object is used and `sole_available_object_fallback`, the configured target, and the reason are recorded in both config and `flat_manifest.json`. A legacy V3 metadata candidate index must never be looked up in the V8 pool: candidate frames and indices are not stable across those versions. Ambiguous multi-object cases fail instead of guessing.

The formal publication is complete. The flat directory contains 12 MP4s, 38 PNGs at 1920x1152, `README.md`, and `flat_manifest.json`, with no subdirectories. All twelve former structured MP4 paths are valid absolute symbolic links to the flat files.

## V8 IK-target versus actual-EE audit video

Legacy `*_strategies_2x3_legacy_v3.png` files use the V3 canonical reranker and are not candidate-for-candidate matches for V8 execution videos. `overlay_v8_execution_pose_audit.py` reads each V8 planner's `plan_summary.json` and `debug_execution_metrics.jsonl` directly. A colored C-gripper is the exact per-frame IK target; a white C-gripper is the measured EE. Target axes are red `+X` physical forward, green `+Y` opening, and blue `+Z` normal. The final grasp/action frame receives a one-second arrival hold with per-arm PASS/FAIL and errors.

Parameter template (not directly runnable):

```bash
python code_painting/overlay_v8_execution_pose_audit.py \
  --task <TASK> --episode-id <ID> \
  --method orientation=<ORIENTATION_PLAN_SUMMARY> \
  --method fused=<FUSED_PLAN_SUMMARY> \
  --method top_score=<TOPSCORE_PLAN_SUMMARY> \
  --ours-video <OURS_V2_VIDEO> \
  --asset-root <PAPER_ASSET_ROOT> \
  --work-output-dir <AUDIT_WORK_DIR> \
  --flat-output-dir <FLAT_RELEASE_DIR>
```

Runnable `pick_diverse_bottles/id0` example:

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python code_painting/overlay_v8_execution_pose_audit.py \
  --task pick_diverse_bottles --episode-id 0 \
  --method orientation=/home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v8_physical_axes_raw_batch_6x2_20260720_orientation/pick_diverse_bottles/foundation_input_0/plan_summary.json \
  --method fused=/home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v8_physical_axes_raw_batch_6x2_20260720_fused/pick_diverse_bottles/foundation_input_0/plan_summary.json \
  --method top_score=/home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v8_physical_axes_raw_batch_6x2_20260720_topscore/pick_diverse_bottles/foundation_input_0/plan_summary.json \
  --ours-video /home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/L16_de_human_replay_clean_right_cam/pick_diverse_bottles/foundation_input_0/head_cam_plan.mp4 \
  --asset-root /home/zaijia001/ssd/data/piper/paper_qualitative_assets \
  --work-output-dir /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/v8_execution_pose_audit_20260721/pick_diverse_bottles/id0 \
  --flat-output-dir /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/v8_6x2_flat_release_20260721
```

The candidates differ in this episode. At frame 38, the V3 image uses Orientation/Fused `L16/R5` and Top-score `L0/R3`, while frame 78 uses Orientation/Fused `L3/R10` and Top-score `L0/R1`. The V8 video uses Orientation/Fused `L16/R5`, then `L14/R16`, and Top-score `L8/R3`, then `L3/R2`. The legacy images therefore describe an older canonical selection, not the V8 execution orientation.

## D435 candidate sheets matched exactly to the V8 video

`export_v8_video_matched_candidate_contact_sheets.py` reads the three V8 video `plan_summary.json` files directly. Orientation, Fused, and Top-score panels use the saved final `pose_world_wxyz`, after physical-axis remap, camera-up branch selection, and the configured candidate target offset, but before IK. Red `+X` is Piper forward, green `+Y` is opening, and blue `+Z` is the gripper-plane normal/camera-back direction. The OursV2 panel explicitly keeps the native canonical `+Z`-forward human target as a reference and never relabels it as a V8 AnyGrasp candidate.

Parameter template (not directly runnable):

```bash
python code_painting/export_v8_video_matched_candidate_contact_sheets.py \
  --task <TASK> --episode-id <ID> \
  --keyframe <FRAME> [--keyframe <FRAME> ...] \
  --method orientation=<ORIENTATION_PLAN_SUMMARY> \
  --method fused=<FUSED_PLAN_SUMMARY> \
  --method top_score=<TOPSCORE_PLAN_SUMMARY> \
  --metadata <FRAME>=<SELECTION_METADATA_JSON> \
  --robotwin-root <ROBOTWIN_ROOT> --asset-root <PAPER_ASSET_ROOT> \
  --output-dir <WORK_OUTPUT_DIR> [--publish-dir <MATCHED_RELEASE_DIR>] \
  [--dry-run] [--overwrite]
```

Runnable `pick_diverse_bottles/id0` example:

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python code_painting/export_v8_video_matched_candidate_contact_sheets.py \
  --task pick_diverse_bottles --episode-id 0 --keyframe 38 --keyframe 78 \
  --method orientation=/home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v8_physical_axes_raw_batch_6x2_20260720_orientation/pick_diverse_bottles/foundation_input_0/plan_summary.json \
  --method fused=/home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v8_physical_axes_raw_batch_6x2_20260720_fused/pick_diverse_bottles/foundation_input_0/plan_summary.json \
  --method top_score=/home/zaijia001/ssd/RoboTwin/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v8_physical_axes_raw_batch_6x2_20260720_topscore/pick_diverse_bottles/foundation_input_0/plan_summary.json \
  --metadata 38=/home/zaijia001/ssd/RoboTwin/code_painting/selection_strategy_compare_v4/pick_diverse_bottles/id0_keyframe_000038_metadata.json \
  --metadata 78=/home/zaijia001/ssd/RoboTwin/code_painting/selection_strategy_compare_v4/pick_diverse_bottles/id0_keyframe_000078_metadata.json \
  --robotwin-root /home/zaijia001/ssd/RoboTwin \
  --asset-root /home/zaijia001/ssd/data/piper/paper_qualitative_assets \
  --output-dir /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/v8_video_matched_candidate_sheets_20260722/pick_diverse_bottles/id0 \
  --publish-dir /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722 \
  --overwrite
```

The six panels are the V8 physical target pool, Orientation, Fused, Top-score, the OursV2 human-target reference, and an all-method overlay. This sheet answers “which gripper target did the video plan?” The separate `*_video_matched_arrivals_2x3.png` answers “where did the robot actually arrive?” and must not be conflated with the candidate sheet.
