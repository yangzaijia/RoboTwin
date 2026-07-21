#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/zaijia001/ssd/RoboTwin
ASSET_ROOT=/home/zaijia001/ssd/data/piper/paper_qualitative_assets
GPU=2
DRY_RUN=0
RUN_TAG=v8_physical_axes_raw_batch_6x2_20260720
SOURCE_RUN_TAG=
COMPOSE_ONLY=0

while (($# > 0)); do
  case "$1" in
    --gpu) GPU="$2"; shift 2 ;;
    --run-tag) RUN_TAG="$2"; shift 2 ;;
    --source-run-tag) SOURCE_RUN_TAG="$2"; shift 2 ;;
    --compose-only) COMPOSE_ONLY=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "ERROR unknown argument: $1" >&2; exit 2 ;;
  esac
done

SOURCE_RUN_TAG="${SOURCE_RUN_TAG:-$RUN_TAG}"

source /home/zaijia001/ssd/miniconda3/etc/profile.d/conda.sh
cd "$ROOT"

PREVIEW_ROOT="$ROOT/code_painting/anygrasp_h2o_preview_d435_robot_frame_approach_axis_${SOURCE_RUN_TAG}"
PLANNER_BASE="$ROOT/code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes"
ORIENTATION_ROOT="$PLANNER_BASE/paper_${SOURCE_RUN_TAG}_orientation"
FUSED_ROOT="$PLANNER_BASE/paper_${SOURCE_RUN_TAG}_fused"
TOPSCORE_ROOT="$PLANNER_BASE/paper_${SOURCE_RUN_TAG}_topscore"
OURS_ROOT="$PLANNER_BASE/L16_de_human_replay_clean_right_cam"
OUTPUT_ROOT="$ASSET_ROOT/outputs/${RUN_TAG}"
SOURCE_OUTPUT_ROOT="$ASSET_ROOT/outputs/${SOURCE_RUN_TAG}"
RUN_ROOT="$OUTPUT_ROOT/_run"
LOG_ROOT="$RUN_ROOT/logs"
STATUS_TSV="$RUN_ROOT/planner_status.tsv"
COMPOSE_STATUS_TSV="$RUN_ROOT/compose_status.tsv"
BATCH_LOG="$RUN_ROOT/batch.log"

EPISODES=(
  handover_bottle:1 handover_bottle:3
  pick_diverse_bottles:0 pick_diverse_bottles:1
  place_bread_basket:0 place_bread_basket:1
  pnp_bread:7 pnp_bread:8
  pnp_tray:2 pnp_tray:3
  stack_cups:0 stack_cups:1
)

if ((DRY_RUN == 0)); then
  if [[ -e "$RUN_ROOT/DONE" ]]; then
    echo "ERROR completed batch already exists: $RUN_ROOT/DONE" >&2
    exit 3
  fi
  mkdir -p "$LOG_ROOT"
  exec > >(tee -a "$BATCH_LOG") 2>&1
  if [[ ! -f "$STATUS_TSV" ]]; then
    if ((COMPOSE_ONLY)) && [[ -f "$SOURCE_OUTPUT_ROOT/_run/planner_status.tsv" ]]; then
      cp "$SOURCE_OUTPUT_ROOT/_run/planner_status.tsv" "$STATUS_TSV"
    else
      printf 'task\tepisode_id\tstrategy\tcommand_rc\tsummary\tvideo\n' > "$STATUS_TSV"
    fi
  fi
  if [[ ! -f "$COMPOSE_STATUS_TSV" ]]; then
    printf 'task\tepisode_id\tcommand_rc\tvideo\tmanifest\tstatus\n' > "$COMPOSE_STATUS_TSV"
  fi
fi

print_command() {
  printf '%q ' "$@"
  printf '\n'
}

task_objects() {
  case "$1" in
    pick_diverse_bottles) printf '%s\n' left_bottle right_bottle ;;
    place_bread_basket) printf '%s\n' basket bread ;;
    stack_cups) printf '%s\n' left_light_pink_cup right_dark_red_cup ;;
    handover_bottle) printf '%s\n' right_bottle right_bottle ;;
    pnp_bread) printf '%s\n' left_bread right_bread ;;
    pnp_tray) printf '%s\n' left_dark_red_cup right_bottle ;;
    *) return 1 ;;
  esac
}

render_preview_task() {
  local task="$1" id1="$2" id2="$3"
  local left_obj right_obj
  mapfile -t objects < <(task_objects "$task")
  left_obj="${objects[0]}"; right_obj="${objects[1]}"
  local ann="$ROOT/code_painting/h2o_manual_review/$task/hand_keyframes_all.json"
  local any_root="/home/zaijia001/ssd/data/piper/hand/$task/${task}_output"
  [[ -d "$any_root" ]] || any_root="/home/zaijia001/ssd/data/piper/hand/$task/${task}_output_old_cam"
  local replay_root="/home/zaijia001/ssd/data/piper/hand/$task/foundation_replay_d435"
  local hand_root="/home/zaijia001/ssd/data/piper/hand/$task/harmer_output"
  local out_root="$PREVIEW_ROOT/$task"
  local command=(
    env VIDEO_PREFIX=foundation_input CUDA_VISIBLE_DEVICES="$GPU"
    bash "$ROOT/code_painting/run_render_anygrasp_ranked_preview_keyframes_batch.sh"
    "$any_root" "$replay_root" "$hand_root" "$out_root"
    --ids "$id1" "$id2" --hand_keyframes_json "$ann"
    --left_target_object "$left_obj" --right_target_object "$right_obj"
    --anygrasp_score_weight 0.25 --orientation_score_weight 0.75
    --max_rotation_distance_deg 90 --orientation_metric approach_axis
    --candidate_frame_mode robot_replay
    --candidate_target_local_x_offset_m 0.0 --candidate_target_local_z_offset_m -0.05
    --candidate_orientation_remap_label identity
    --draw_object_overlay 1 --draw_hand_reference 1 --debug_dump_object_distances 1
    --top_k 20 --camera_cv_axis_mode legacy_r1
  )
  if ((DRY_RUN)); then
    print_command "${command[@]}"
    return 0
  fi
  if [[ -f "$out_root/foundation_input_${id1}/summary.json" && -f "$out_root/foundation_input_${id2}/summary.json" ]]; then
    echo "[preview-skip] task=$task ids=$id1,$id2"
    return 0
  fi
  echo "[preview-run] task=$task ids=$id1,$id2"
  timeout 900 "${command[@]}"
}

run_planner() {
  local task="$1" episode_id="$2" strategy="$3" output_root="$4" group="$5" selection_mode="$6"
  local preview="$PREVIEW_ROOT/$task/foundation_input_${episode_id}/summary.json"
  local summary="$output_root/$task/foundation_input_${episode_id}/plan_summary.json"
  local video="$output_root/$task/foundation_input_${episode_id}/head_cam_plan.mp4"
  local command=(
    bash "$ROOT/code_painting/run_plan_anygrasp_keyframes_piper_d435_six_tasks.sh"
    --gpu "$GPU" --tasks "$task" --ids "$episode_id" --output_root "$output_root"
    --preview_root "$PREVIEW_ROOT" --reuse_preview_candidate_group "$group"
    --candidate_selection_mode "$selection_mode"
    --candidate_input_frame_contract robot_replay --candidate_frame_contract anygrasp_raw
    --candidate_orientation_remap_label swap_red_blue_keep_green
    --candidate_keep_camera_up 1 --candidate_camera_forward_axis local_x
    --candidate_camera_top_axis z --candidate_camera_top_axis_sign -1
    --candidate_target_local_x_offset_m -0.05 --candidate_target_local_z_offset_m 0
    --approach_axis local_x --debug_gripper_actor_forward_axis local_x
    --trajectory_mode joint_interp --joint_interp_waypoints 40
    --execute_interp_steps 40 --joint_command_scene_steps 10
    --settle_steps 30 --joint_target_wait_steps 300 --reach_error_pose_source ee
    --reach_rot_tol_deg 30 --ik_max_position_threshold_m 0.02
    --ik_max_rotation_threshold_rad 0.8 --ik_num_seeds 64
    --ik_solution_selection joint_continuity
    --piper_apply_global_trans_to_ik 1 --piper_apply_curobo_to_sapien_link_rotation 1
    --disable_execution_collisions --target_axes_only
    --piper_calibration_bundle "$ROOT/calibration_bundle_piper_new_table_0515.json"
    --continue_on_error
  )
  if ((DRY_RUN)); then
    if [[ ! -f "$preview" ]]; then
      echo "[dry-run-preview-pending] $preview"
    fi
    print_command "${command[@]}"
    return 0
  fi
  if [[ ! -f "$preview" ]]; then
    echo "[planner-skip] task=$task id=$episode_id strategy=$strategy missing_preview=$preview"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$task" "$episode_id" "$strategy" 4 "$summary" "$video" >> "$STATUS_TSV"
    return 0
  fi
  if [[ -f "$summary" && -f "$video" ]]; then
    echo "[planner-skip-existing] task=$task id=$episode_id strategy=$strategy"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$task" "$episode_id" "$strategy" 0 "$summary" "$video" >> "$STATUS_TSV"
    return 0
  fi
  echo "[planner-run] task=$task id=$episode_id strategy=$strategy"
  local log="$LOG_ROOT/${task}_id${episode_id}_${strategy}.log"
  timeout 900 "${command[@]}" > "$log" 2>&1
  local rc=$?
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$task" "$episode_id" "$strategy" "$rc" "$summary" "$video" >> "$STATUS_TSV"
  echo "[planner-done] task=$task id=$episode_id strategy=$strategy rc=$rc summary=$(test -f "$summary" && echo 1 || echo 0) video=$(test -f "$video" && echo 1 || echo 0)"
  return 0
}

compose_episode() {
  local task="$1" episode_id="$2"
  local episode_dir="$OUTPUT_ROOT/$task/id${episode_id}"
  local output_video="$episode_dir/candidate_retarget_grid_2x2_physical_axes_raw_v8.mp4"
  local output_manifest="$episode_dir/candidate_retarget_grid_2x2_physical_axes_raw_v8_manifest.json"
  local output_status="$episode_dir/execution_status_v8.json"
  local log="$LOG_ROOT/${task}_id${episode_id}_compose.log"
  local command=(
    python3 "$ROOT/code_painting/compose_v8_physical_axes_raw_batch.py"
    --task "$task" --episode-id "$episode_id"
    --orientation-root "$ORIENTATION_ROOT" --fused-root "$FUSED_ROOT"
    --topscore-root "$TOPSCORE_ROOT" --ours-root "$OURS_ROOT"
    --output-root "$OUTPUT_ROOT" --asset-root "$ASSET_ROOT" --allow-missing
  )
  if ((DRY_RUN)); then
    print_command "${command[@]}" --dry-run
    return 0
  fi
  echo "[compose-run] task=$task id=$episode_id"
  timeout --foreground 300 "${command[@]}" </dev/null > "$log" 2>&1
  local rc=$?
  if ((rc != 0)); then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$task" "$episode_id" "$rc" "$output_video" "$output_manifest" "$output_status" \
      >> "$COMPOSE_STATUS_TSV"
    echo "[compose-failed] task=$task id=$episode_id rc=$rc log=$log"
    return 1
  fi
  if [[ ! -s "$output_video" || ! -s "$output_manifest" || ! -s "$output_status" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$task" "$episode_id" 4 "$output_video" "$output_manifest" "$output_status" \
      >> "$COMPOSE_STATUS_TSV"
    echo "[compose-failed] task=$task id=$episode_id rc=4 missing_output=1 log=$log"
    return 1
  fi
  if ! ffmpeg -v error -i "$output_video" -f null -; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$task" "$episode_id" 5 "$output_video" "$output_manifest" "$output_status" \
      >> "$COMPOSE_STATUS_TSV"
    echo "[compose-failed] task=$task id=$episode_id rc=5 decode_failed=1 log=$log"
    return 1
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$task" "$episode_id" 0 "$output_video" "$output_manifest" "$output_status" \
    >> "$COMPOSE_STATUS_TSV"
  echo "[compose-done] task=$task id=$episode_id video=$output_video"
  return 0
}

echo "[batch-start] run_tag=$RUN_TAG source_run_tag=$SOURCE_RUN_TAG compose_only=$COMPOSE_ONLY gpu=$GPU dry_run=$DRY_RUN episodes=${#EPISODES[@]}"

if ((COMPOSE_ONLY == 0)); then
  render_preview_task handover_bottle 1 3
  render_preview_task pick_diverse_bottles 0 1
  render_preview_task place_bread_basket 0 1
  render_preview_task pnp_bread 7 8
  render_preview_task pnp_tray 2 3
  render_preview_task stack_cups 0 1
fi

COMPOSE_FAILURES=0
for pair in "${EPISODES[@]}"; do
  task="${pair%%:*}"; episode_id="${pair##*:}"
  if ((COMPOSE_ONLY == 0)); then
    run_planner "$task" "$episode_id" orientation "$ORIENTATION_ROOT" orientation planner
    run_planner "$task" "$episode_id" fused "$FUSED_ROOT" fused planner
    run_planner "$task" "$episode_id" top_score "$TOPSCORE_ROOT" orientation top_score_auto
  fi
  if ! compose_episode "$task" "$episode_id"; then
    ((COMPOSE_FAILURES += 1))
  fi
done

if ((DRY_RUN)); then
  echo "[batch-dry-run-complete]"
  exit 0
fi

if ! python3 - "$OUTPUT_ROOT" "$STATUS_TSV" "$COMPOSE_STATUS_TSV" "${#EPISODES[@]}" "$COMPOSE_FAILURES" <<'PY'
import json,sys
from datetime import datetime,timezone
from pathlib import Path
root=Path(sys.argv[1]); status_tsv=Path(sys.argv[2]); compose_status_tsv=Path(sys.argv[3])
expected=int(sys.argv[4]); compose_failures=int(sys.argv[5])
statuses=[]
for path in sorted(root.glob("*/id*/execution_status_v8.json")):
    statuses.append(json.loads(path.read_text(encoding="utf-8")))
manifest={
    "schema_version":1,
    "completed_at_utc":datetime.now(timezone.utc).isoformat(),
    "expected_episode_count":expected,
    "episode_count":len(statuses),
    "compose_failure_count":compose_failures,
    "planner_status_tsv":str(status_tsv),
    "compose_status_tsv":str(compose_status_tsv),
    "episodes":statuses,
}
(root/"episode_batch_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if len(statuses) != expected or compose_failures:
    (root/"_run"/"FAILED").write_text(
        f"expected={expected} completed={len(statuses)} compose_failures={compose_failures}\n",
        encoding="utf-8",
    )
    print(f"[batch-failed] expected={expected} completed={len(statuses)} compose_failures={compose_failures}")
    raise SystemExit(1)
(root/"_run"/"DONE").touch()
print(f"[batch-complete] episodes={len(statuses)}/{expected} manifest={root/'episode_batch_manifest.json'}")
PY
then
  exit 5
fi
