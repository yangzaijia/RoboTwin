# V9 rigid K2 object-transport commands

## Purpose

Keep V8 candidate selection and K1 targets unchanged, preserve `T_EE_object` after actual K1 arrival, move the object to FoundationPose K2, and generate the six-panel transform audit plus 2x2 video.

## Non-runnable template

```bash
bash /home/zaijia001/ssd/RoboTwin/code_painting/run_v9_rigid_object_transport_pick_diverse_id0.sh \
  --gpu <GPU_ID> \
  --run-tag <ISOLATED_RUN_TAG> \
  [--pure-scene] \
  --strategy <orientation|fused|topscore>
```

Omit `--strategy` to run all three strategies sequentially. No V8 file is modified or overwritten.
`--pure-scene` is disabled by default. When enabled, it uses both
`pure_scene_output=1` and `debug_visualize_targets=0`, removing only rendered
debug grippers, target axes, and overlays without changing candidates, IK,
retreat, or rigid transport.

## Runnable example

```bash
cd /home/zaijia001/ssd/RoboTwin
bash code_painting/run_v9_rigid_object_transport_pick_diverse_id0.sh \
  --gpu 2 \
  --run-tag v9_ee_rigid_object_transport_20260723
```

Historical single pure-scene experiment (uses original V9's default
`close=0.0` and is no longer the formal V9p deliverable):

```bash
cd /home/zaijia001/ssd/RoboTwin
bash code_painting/run_v9_rigid_object_transport_pick_diverse_id0.sh \
  --gpu 2 \
  --run-tag v9p_ee_rigid_object_transport_clean_20260724 \
  --pure-scene
```

## Export four method-specific six-panel transform audits

Orientation, Fused, and Top-score each read their own V9 `plan_summary.json`. OursV2 reads the historical human-replay summary with `--pipeline-kind oursv2_historical`; it is never depicted as an AnyGrasp remap.

```bash
cd /home/zaijia001/ssd/RoboTwin
OUT=/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722
ROOT=code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes
K1=code_painting/selection_strategy_compare_v4/pick_diverse_bottles/id0_keyframe_000038_metadata.json
K2=code_painting/selection_strategy_compare_v4/pick_diverse_bottles/id0_keyframe_000078_metadata.json
PY="/home/zaijia001/ssd/miniconda3/bin/conda run -n RoboTwin_bw python"

for spec in \
  "orientation Orientation 04a_orientation" \
  "fused Fused 04b_fused" \
  "topscore Top-score 04c_topscore"
do
  set -- $spec
  strategy=$1
  label=$2
  stem=$3
  $PY code_painting/export_v9_candidate_to_robotwin_transform_audit.py \
    --robotwin-root /home/zaijia001/ssd/RoboTwin \
    --plan-summary "$ROOT/paper_v9_ee_rigid_object_transport_20260723_${strategy}/pick_diverse_bottles/foundation_input_0/plan_summary.json" \
    --metadata-k1 "$K1" \
    --metadata-k2 "$K2" \
    --method-label "$label" \
    --pipeline-kind anygrasp_v9 \
    --output "$OUT/v9_pick_diverse_bottles_0_${stem}_candidate_to_robotwin_transform_2x3.png"
done

$PY code_painting/export_v9_candidate_to_robotwin_transform_audit.py \
  --robotwin-root /home/zaijia001/ssd/RoboTwin \
  --plan-summary "$ROOT/L16_de_human_replay_clean_right_cam/pick_diverse_bottles/foundation_input_0/plan_summary.json" \
  --metadata-k1 "$K1" \
  --metadata-k2 "$K2" \
  --method-label OursV2 \
  --pipeline-kind oursv2_historical \
  --output "$OUT/v9_pick_diverse_bottles_0_04d_oursv2_human_target_to_robotwin_2x3.png"
```

Each PNG has a same-stem JSON recording source summary/metadata hashes, K1/K2 IDs, pipeline kind, and whether K2 really executed. Top-score currently marks panel six `NOT EXECUTED`; no missing rigid target is fabricated.

## Current IK/TCP semantics

- V9 uses `robot_config_PiperPika_agx_dual_table_0515.json` and Piper URDFIK. It belongs to the OursV2/0515 12 cm configuration family and does not use `T_L6URDF_RTCP = Ry(-1.57) @ Tx(0.19)`.
- `_trans_from_gripper_to_endlink` translates by `0.12-gripper_bias`; with `gripper_bias=0.12`, the extra translation into link6 IK is `0`.
- Runner `--approach_offset_m 0.12` is pregrasp-only. The final grasp target does not retain that 12 cm separation.
- `--candidate_target_local_x_offset_m -0.05` constructs an AnyGrasp target along physical `local +X`; it is not a TCP length.
- V9 rigid K2 targets the EE/link6 origin while interpreting orientation as the physical Piper gripper axes.

## Compose the 2x2 video

```bash
cd /home/zaijia001/ssd/RoboTwin
python3 code_painting/compose_v9_rigid_object_transport_grid.py \
  --robotwin-root /home/zaijia001/ssd/RoboTwin \
  --asset-root /home/zaijia001/ssd/data/piper/paper_qualitative_assets \
  --run-tag v9_ee_rigid_object_transport_20260723 \
  --output-dir /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722
```

Compose the historical single pure-scene experiment:

```bash
cd /home/zaijia001/ssd/RoboTwin
python3 code_painting/compose_v9_rigid_object_transport_grid.py \
  --robotwin-root /home/zaijia001/ssd/RoboTwin \
  --asset-root /home/zaijia001/ssd/data/piper/paper_qualitative_assets \
  --run-tag v9p_ee_rigid_object_transport_clean_20260724 \
  --variant v9p \
  --output-dir /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722
```

Historical output:

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/v9p_pick_diverse_bottles_0_05_rigid_object_transport_clean_2x2.mp4
```

For the formal `close=0.3` OursV2 and Canonical-17 V9p videos, use
`COMMANDS/planning_compare_v9_1.en.md`.

## Validation

```bash
ffprobe -v error \
  -show_entries stream=codec_name,pix_fmt,width,height,r_frame_rate,duration \
  -of json \
  /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/v9_pick_diverse_bottles_0_05_rigid_object_transport_2x2.mp4

ffmpeg -v error \
  -i /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/v9_pick_diverse_bottles_0_05_rigid_object_transport_2x2.mp4 \
  -f null -
```
