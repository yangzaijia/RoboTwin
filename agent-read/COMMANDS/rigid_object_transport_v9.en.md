# V9 rigid K2 object-transport commands

## Purpose

Keep V8 candidate selection and K1 targets unchanged, preserve `T_EE_object` after actual K1 arrival, move the object to FoundationPose K2, and generate the six-panel transform audit plus 2x2 video.

## Non-runnable template

```bash
bash /home/zaijia001/ssd/RoboTwin/code_painting/run_v9_rigid_object_transport_pick_diverse_id0.sh \
  --gpu <GPU_ID> \
  --run-tag <ISOLATED_RUN_TAG> \
  --strategy <orientation|fused|topscore>
```

Omit `--strategy` to run all three strategies sequentially. No V8 file is modified or overwritten.

## Runnable example

```bash
cd /home/zaijia001/ssd/RoboTwin
bash code_painting/run_v9_rigid_object_transport_pick_diverse_id0.sh \
  --gpu 2 \
  --run-tag v9_ee_rigid_object_transport_20260723
```

## Export the six-panel transform audit

```bash
cd /home/zaijia001/ssd/RoboTwin
/home/zaijia001/ssd/miniconda3/bin/conda run -n RoboTwin_bw \
python code_painting/export_v9_candidate_to_robotwin_transform_audit.py \
  --robotwin-root /home/zaijia001/ssd/RoboTwin \
  --plan-summary code_painting/anygrasp_plan_keyframes_piper_d435_replay_axes/paper_v9_ee_rigid_object_transport_20260723_orientation/pick_diverse_bottles/foundation_input_0/plan_summary.json \
  --metadata-k1 code_painting/selection_strategy_compare_v4/pick_diverse_bottles/id0_keyframe_000038_metadata.json \
  --metadata-k2 code_painting/selection_strategy_compare_v4/pick_diverse_bottles/id0_keyframe_000078_metadata.json \
  --method-label orientation \
  --output /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/v9_pick_diverse_bottles_0_04_candidate_to_robotwin_transform_2x3.png
```

## Compose the 2x2 video

```bash
cd /home/zaijia001/ssd/RoboTwin
python3 code_painting/compose_v9_rigid_object_transport_grid.py \
  --robotwin-root /home/zaijia001/ssd/RoboTwin \
  --asset-root /home/zaijia001/ssd/data/piper/paper_qualitative_assets \
  --run-tag v9_ee_rigid_object_transport_20260723 \
  --output-dir /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722
```

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
