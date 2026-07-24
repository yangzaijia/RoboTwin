#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/zaijia001/ssd/RoboTwin
DATA_ROOT=/home/zaijia001/ssd/data/piper/hand/pick_diverse_bottles
PLANNER_ROOT="$ROOT/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes"
RUN_TAG=v9_ee_rigid_object_transport_20260723
GPU=2
DRY_RUN=0
PURE_SCENE=0
DEBUG_VISUALIZE_TARGETS=1
STRATEGIES=(orientation fused topscore)

while (($# > 0)); do
  case "$1" in
    --gpu) GPU="$2"; shift 2 ;;
    --run-tag) RUN_TAG="$2"; shift 2 ;;
    --strategy) STRATEGIES=("$2"); shift 2 ;;
    --pure-scene)
      PURE_SCENE=1
      DEBUG_VISUALIZE_TARGETS=0
      shift
      ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "ERROR unknown argument: $1" >&2; exit 2 ;;
  esac
done

source /home/zaijia001/ssd/miniconda3/etc/profile.d/conda.sh
cd "$ROOT"

ANY="$DATA_ROOT/pick_diverse_bottles_output/foundation_input_0"
REPLAY="$DATA_ROOT/foundation_replay_d435/foundation_input_0"
HAND="$DATA_ROOT/harmer_output/hand_detections_0.npz"
LOG_ROOT="$PLANNER_ROOT/_logs_${RUN_TAG}"
mkdir -p "$LOG_ROOT"

run_strategy() {
  local strategy="$1"
  local source_suffix="$strategy"
  [[ "$strategy" == "topscore" ]] && source_suffix=topscore
  local source_summary="$PLANNER_ROOT/paper_v8_physical_axes_raw_batch_6x2_20260720_${source_suffix}/pick_diverse_bottles/foundation_input_0/plan_summary.json"
  local output_root="$PLANNER_ROOT/paper_${RUN_TAG}_${strategy}"
  local output_dir="$output_root/pick_diverse_bottles/foundation_input_0"
  local log="$LOG_ROOT/pick_diverse_bottles_id0_${strategy}.log"

  [[ -f "$source_summary" ]] || { echo "ERROR missing source summary: $source_summary" >&2; return 3; }
  if [[ -s "$output_dir/plan_summary.json" && -s "$output_dir/head_cam_plan.mp4" ]]; then
    echo "[skip-existing] strategy=$strategy output=$output_dir"
    return 0
  fi

  local command=(
    env CUDA_VISIBLE_DEVICES="$GPU"
    /home/zaijia001/ssd/miniconda3/bin/conda run -n RoboTwin_bw
    python "$ROOT/code_painting/plan_anygrasp_keyframes_piper.py"
    --anygrasp_dir "$ANY"
    --replay_dir "$REPLAY"
    --hand_npz "$HAND"
    --output_dir "$output_dir"
    --reuse_plan_summary_json "$source_summary"
    --image_width 640 --image_height 480 --fovy_deg 42.499880046655484
    --arm auto --execute_both_arms 1
    --dual_stage_require_all_plans 1
    --require_keyframe1_reached_before_close 1
    --require_keyframe1_reached_before_action 1
    --planner_backend urdfik
    --urdfik_trajectory_mode joint_interp
    --urdfik_joint_interp_waypoints 40
    --urdfik_cartesian_interp_steps -1
    --urdfik_cartesian_interp_auto_step_m 0.01
    --execute_partial_cartesian_plan 0
    --urdfik_max_position_threshold_m 0.02
    --urdfik_max_rotation_threshold_rad 0.8
    --urdfik_num_seeds 64
    --urdfik_solution_selection joint_continuity
    --piper_urdfik_apply_global_trans_to_ik 1
    --piper_urdfik_apply_curobo_to_sapien_link_rotation 1
    --candidate_selection_mode planner
    --candidate_input_frame_contract anygrasp_raw
    --candidate_frame_contract anygrasp_raw
    --candidate_orientation_remap_label identity
    --candidate_keep_camera_up 1
    --candidate_camera_forward_axis local_x
    --candidate_camera_top_axis z
    --candidate_camera_top_axis_sign -1
    --candidate_target_local_x_offset_m -0.05
    --candidate_target_local_z_offset_m 0
    --left_target_object left_bottle
    --right_target_object right_bottle
    --approach_axis local_x
    --approach_offset_m 0.12
    --debug_gripper_actor_forward_axis local_x
    --action_target_mode rigid_object_transport
    --reach_error_pose_source ee
    --replan_until_reached 1
    --replan_until_reached_max_attempts 1
    --save_debug_preview 1
    --save_debug_execution_preview 0
    --save_pose_debug 1
    --debug_visualize_targets "$DEBUG_VISUALIZE_TARGETS"
    --debug_candidate_top_k 0
    --debug_common_candidate_top_k 0
    --debug_visualize_selected_keyframe_axes 0
    --debug_visualize_ik_waypoints 0
    --reach_pos_tol_m 0.03
    --reach_rot_tol_deg 30
    --enable_grasp_action_object_collision 0
    --execute_interp_steps 40
    --joint_command_scene_steps 10
    --settle_steps 30
    --joint_target_wait_steps 300
    --joint_target_wait_tol_rad 0.01
    --hold_frames_after_stage 8
    --pure_scene_output "$PURE_SCENE"
    --overlay_text 0
    --head_only 0
    --third_person_view 1
    --vscode_compatible_video 1
    --lighting_mode front_no_shadow
    --robot_config "$ROOT/robot_config_PiperPika_agx_dual_table_0515.json"
    --camera_cv_axis_mode legacy_r1
    --piper_calibration_bundle "$ROOT/calibration_bundle_piper_new_table_0515.json"
    --head_camera_local_pos 0.11210396690038413 -0.39189397826604927 0.4753892624100325
    --head_camera_local_quat_wxyz 0.8524694864910365 -0.0011011947849308937 0.5226654778798345 0.010740586780925399
    --enable_viewer 0 --viewer_wait_at_end 0 --viewer_show_camera_frustums 0
    --object_mesh_override left_bottle=/home/zaijia001/ssd/data/R1/hand/obj_mesh/cola/cola.obj
    --object_mesh_override right_bottle=/home/zaijia001/ssd/data/R1/hand/obj_mesh/bottle/bottle.obj
  )
  printf '[command] '
  printf '%q ' "${command[@]}"
  printf '\n'
  if ((DRY_RUN)); then
    return 0
  fi
  mkdir -p "$output_dir"
  printf '%q ' "${command[@]}" >"$output_dir/command.sh.txt"
  printf '\n' >>"$output_dir/command.sh.txt"
  set +e
  timeout --foreground 900 "${command[@]}" </dev/null >"$log" 2>&1
  local status=$?
  set -e
  printf '%s\n' "$status" >"$output_dir/exit_code.txt"
  if ((status != 0)); then
    echo "ERROR strategy=$strategy status=$status log=$log" >&2
    return "$status"
  fi
  echo "[done] strategy=$strategy output=$output_dir log=$log"
}

for strategy in "${STRATEGIES[@]}"; do
  run_strategy "$strategy"
done
