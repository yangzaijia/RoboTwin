# Piper robot-only material recoloring

## Semantics

`--piper_robot_gray_material_override 1` edits render materials only on the two Piper articulations. It does not threshold final-frame RGB and never reads or changes bottle, table, or background materials. By default, near-neutral robot materials with mean linear RGB in `[0.10, 0.80]` become `[0.06, 0.06, 0.06]`.

The option currently supports `--planner_backend urdfik` only and is disabled by default, so existing pipelines remain unchanged unless explicitly enabled.

## Parameter template (not directly runnable)

```bash
python code_painting/plan_anygrasp_keyframes_piper.py \
  <existing V9p arguments> \
  --output_dir <new isolated output directory> \
  --piper_robot_gray_material_override 1 \
  --piper_robot_gray_material_target 0.06 \
  --piper_robot_gray_material_min 0.10 \
  --piper_robot_gray_material_max 0.80
```

## Runnable Orientation example for this episode

```bash
cd /home/zaijia001/ssd/RoboTwin
ROOT=/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722
SRC="$ROOT/v9p_planning_runs_oursv2_close03_pure/oursv2-5/orientation"
DST="$ROOT/v10_robot_material_override_oursv2_20260730/orientation_reproduce/planner_output"
mkdir -p "$DST"
CMD=$(sed "s#--output_dir $SRC/planner_output#--output_dir $DST#" "$SRC/command.sh.txt")
eval "$CMD --piper_robot_gray_material_override 1 --piper_robot_gray_material_target 0.06 --piper_robot_gray_material_min 0.10 --piper_robot_gray_material_max 0.80"
```

## Validation

```bash
ffprobe -v error \
  -show_entries stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_frames \
  -of json \
  /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/v10_robot_material_override_oursv2_20260730/orientation/planner_output/head_cam_plan.mp4

ffmpeg -nostdin -v error \
  -i /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/v9p_stage12_realbg_20260725/v10_oursv2_aligned_debug_robot_material_dark_4x6.mp4 \
  -f null -
```
