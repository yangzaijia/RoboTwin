#!/usr/bin/env bash
set -u -o pipefail

ROOT=/home/zaijia001/ssd/RoboTwin
ASSET_ROOT=/home/zaijia001/ssd/data/piper/paper_qualitative_assets
RELEASE_ROOT="$ASSET_ROOT/outputs/matched_candidate_image_video_release_20260722"
DATA_ROOT=/home/zaijia001/ssd/data/piper/hand/pick_diverse_bottles
V8_ROOT="$ROOT/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes"
MODE=""
GPU=0
DRY_RUN=0
PURE_SCENE=0
DEBUG_VISUALIZE_TARGETS=1

while (($#)); do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --gpu) GPU="$2"; shift 2 ;;
    --pure-scene)
      PURE_SCENE=1
      DEBUG_VISUALIZE_TARGETS=0
      shift
      ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "ERROR unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ "$MODE" =~ ^(canonical|oursv2-5|canonical17)$ ]] || {
  echo "Usage: $0 --mode canonical|oursv2-5|canonical17 [--gpu N] [--dry-run]" >&2
  exit 2
}

case "$MODE" in
  canonical)
    RUN_ROOT="$RELEASE_ROOT/v9_1_planning_runs_close03"
    PREP_LOGIC=canonical
    TOOL_LENGTH_M=0.19
    ;;
  oursv2-5)
    RUN_ROOT="$RELEASE_ROOT/v9_1_planning_runs_close03_grasp_retreat05"
    PREP_LOGIC=oursv2-5
    TOOL_LENGTH_M=0.19
    ;;
  canonical17)
    RUN_ROOT="$RELEASE_ROOT/v9_2_planning_runs_canonical17_close03"
    PREP_LOGIC=canonical
    TOOL_LENGTH_M=0.17
    ;;
esac

if ((PURE_SCENE)); then
  case "$MODE" in
    oursv2-5)
      RUN_ROOT="$RELEASE_ROOT/v9p_planning_runs_oursv2_close03_pure"
      ;;
    canonical17)
      RUN_ROOT="$RELEASE_ROOT/v9p_planning_runs_canonical17_close03_pure"
      ;;
    canonical)
      echo "ERROR pure-scene release is defined for oursv2-5 and canonical17" >&2
      exit 2
      ;;
  esac
fi

source /media/mldadmin/home/s126mdg34_08/zaijia/miniconda3/etc/profile.d/conda.sh
cd "$ROOT"

ANY="$DATA_ROOT/pick_diverse_bottles_output/foundation_input_0"
REPLAY="$DATA_ROOT/foundation_replay_d435/foundation_input_0"
HAND="$DATA_ROOT/harmer_output/hand_detections_0.npz"
PY=/media/mldadmin/home/s126mdg34_08/zaijia/miniconda3/envs/RoboTwin_bw/bin/python3.10
PREP="$ROOT/code_painting/prepare_v9_1_reuse_summary.py"
BASE_PLANNER="$ROOT/code_painting/plan_anygrasp_keyframes_piper.py"
CANONICAL_PLANNER="$ROOT/code_painting/piper_canonical_tcp_v1/planner.py"

source_for() {
  case "$1" in
    orientation|fused|topscore)
      echo "$V8_ROOT/paper_v8_physical_axes_raw_batch_6x2_20260720_$1/pick_diverse_bottles/foundation_input_0/plan_summary.json"
      ;;
    oursv2)
      echo "$V8_ROOT/L16_de_human_replay_clean_right_cam/pick_diverse_bottles/foundation_input_0/plan_summary_human_replay.json"
      ;;
  esac
}

run_one() {
  local strategy="$1"
  local source_summary
  source_summary="$(source_for "$strategy")"
  local strategy_root="$RUN_ROOT/$MODE/$strategy"
  local prepared="$strategy_root/prepared_plan_summary.json"
  local output_dir="$strategy_root/planner_output"
  local log="$strategy_root/run.log"
  mkdir -p "$strategy_root"
  [[ -f "$source_summary" ]] || {
    echo "ERROR missing source summary: $source_summary" >&2
    return 3
  }

  local prepare_cmd=(
    "$PY" "$PREP"
    --input "$source_summary"
    --output "$prepared"
    --strategy "$strategy"
    --logic "$PREP_LOGIC"
  )
  printf '[prepare] '; printf '%q ' "${prepare_cmd[@]}"; printf '\n'
  if ((DRY_RUN == 0)); then
    "${prepare_cmd[@]}"
  fi

  local planner reach_source approach_axis debug_forward global_adapter sapien_adapter
  if [[ "$MODE" == canonical || "$MODE" == canonical17 ]]; then
    planner="$CANONICAL_PLANNER"
    reach_source=tcp
    approach_axis=local_x
    debug_forward=local_x
    global_adapter=0
    sapien_adapter=0
  else
    planner="$BASE_PLANNER"
    reach_source=ee
    if [[ "$strategy" == oursv2 ]]; then
      approach_axis=local_z
      debug_forward=local_z
      global_adapter=0
      sapien_adapter=0
    else
      approach_axis=local_x
      debug_forward=local_x
      global_adapter=1
      sapien_adapter=1
    fi
  fi

  local command=(
    env CUDA_VISIBLE_DEVICES="$GPU"
    PIPER_CANONICAL_TOOL_LENGTH_M="$TOOL_LENGTH_M"
    "$PY" -u "$planner"
    --anygrasp_dir "$ANY"
    --replay_dir "$REPLAY"
    --hand_npz "$HAND"
    --output_dir "$output_dir"
    --reuse_plan_summary_json "$prepared"
    --image_width 640 --image_height 480 --fovy_deg 42.499880046655484 --fps 5
    --arm auto --execute_both_arms 1
    --dual_stage_require_all_plans 0
    --dual_stage_freeze_reached_arms_on_replan 1
    --require_keyframe1_reached_before_close 0
    --require_keyframe1_reached_before_action 0
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
    --piper_urdfik_apply_global_trans_to_ik "$global_adapter"
    --piper_urdfik_apply_curobo_to_sapien_link_rotation "$sapien_adapter"
    --candidate_selection_mode planner
    --candidate_input_frame_contract auto
    --candidate_frame_contract legacy_unchecked
    --candidate_orientation_remap_label identity
    --candidate_keep_camera_up 0
    --candidate_target_local_x_offset_m 0
    --candidate_target_local_z_offset_m 0
    --left_target_object left_bottle
    --right_target_object right_bottle
    --approach_axis "$approach_axis"
    --approach_offset_m 0.12
    --debug_gripper_actor_forward_axis "$debug_forward"
    --action_target_mode rigid_object_transport
    --reach_error_pose_source "$reach_source"
    --open_gripper 1.0
    --close_gripper 0.3
    --replan_until_reached 1
    --replan_until_reached_max_attempts 1
    --fail_on_execution_failure 0
    --save_debug_preview 0
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
  printf '[run] '; printf '%q ' "${command[@]}"; printf '\n'
  if ((DRY_RUN)); then
    return 0
  fi
  if [[ -s "$output_dir/head_cam_plan.mp4" && -s "$output_dir/plan_summary.json" ]]; then
    echo "[skip-existing] $output_dir"
    return 0
  fi
  mkdir -p "$output_dir"
  printf '%q ' "${command[@]}" >"$strategy_root/command.sh.txt"; printf '\n' >>"$strategy_root/command.sh.txt"
  timeout --foreground 1200 "${command[@]}" </dev/null >"$log" 2>&1
  local status=$?
  printf '%s\n' "$status" >"$strategy_root/exit_code.txt"
  if [[ ! -s "$output_dir/head_cam_plan.mp4" ]]; then
    echo "ERROR no video produced: mode=$MODE strategy=$strategy status=$status" >&2
    return "$status"
  fi
  echo "[done] mode=$MODE strategy=$strategy status=$status video=$output_dir/head_cam_plan.mp4"
}

overall=0
for strategy in orientation fused topscore oursv2; do
  run_one "$strategy" || overall=$?
done
exit "$overall"
