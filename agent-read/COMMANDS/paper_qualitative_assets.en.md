# Paper Qualitative Assets: 6×2 Episode Images and 4×5 Videos

## Purpose

Maintain the paper video grids and keyframe-candidate images under `/home/zaijia001/ssd/data/piper/paper_qualitative_assets`. The tools only read existing videos, Foundation/AnyGrasp images, and Selection Strategy Audit V4 metadata. They do not run IK, modify OursV2, or overwrite source data.

Formal outputs are grouped by episode:

```text
outputs/keyframe_candidates/<TASK>/id<ID>/
├── frame_<FRAME>/
│   ├── 01_orientation_<left|right|both>.png
│   ├── 02_fused_<left|right|both>.png
│   ├── 03_top_score_<left|right|both>.png
│   ├── 04_oursv2_<left|right|both>.png
│   └── all_strategies_contact_sheet.png
├── _derived/06_anygrasp_candidates.mp4   # only when D435 PNGs exist
├── pipeline_grid_4x5.mp4
├── pipeline_grid_4x5_config.json
├── pipeline_grid_4x5_manifest.json
└── README.md
```

## Parameter template (not directly runnable)

```json
{
  "metadata_root": "<SELECTION_STRATEGY_COMPARE_V4>",
  "output_root": "<PAPER_ASSET_ROOT>/outputs/keyframe_candidates",
  "base_grid_config": "<PAPER_ASSET_ROOT>/pipeline_grid_expanded_dense_urdfmatch_v2_config.json",
  "strategies": ["orientation", "fused", "top_score", "oursv2"],
  "episodes": [{"task": "<TASK>", "id": 0, "keyframes": [38, 78]}],
  "allow_missing": true
}
```

## Current 6×2 selection

| Task | Episodes | Keyframes |
|---|---:|---|
| handover_bottle | 1, 3 | 39/80/103; 23/44/57 |
| pick_diverse_bottles | 0, 1 | 38/78; 46/79 |
| place_bread_basket | 0, 1 | 34/64/103/119; 32/52/79/85 |
| pnp_bread | 7, 8 | 32/80/83/108; 32/49/50/74 |
| pnp_tray | 2, 3 | 52/83; 29/59 |
| stack_cups | 0, 1 | 51/106/139/195; 40/45/84/141 |

## Runnable commands

Dry-run first; this only probes paths, metadata, and video properties:

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python3.10 \
  export_keyframe_candidate_images.py \
  --config paper_episode_batch_config.json --dry-run
python3 generate_paper_episode_batch.py \
  --config paper_episode_batch_config.json --dry-run
```

Formal rebuild:

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python3.10 \
  export_keyframe_candidate_images.py \
  --config paper_episode_batch_config.json --overwrite
python3 generate_paper_episode_batch.py \
  --config paper_episode_batch_config.json --overwrite
```

Use candidate exporter's `--output-root <SMOKE_DIR>` for isolated image checks. For the video generator, use `--only <TASK>:<ID> --output-root <SMOKE_DIR>` for an isolated episode and `--skip-existing` for batch resume. Its `--require-complete` fails when any source stage is absent. The formal config uses `allow_missing=true` so genuine omissions remain explicit `MISSING` tiles.

## Image semantics

- Each strategy/keyframe uses one requested-keyframe Foundation replay background.
- LEFT/RIGHT events draw only the corresponding gripper. BOTH events draw both grippers on one image, never split panels.
- A missing arm/strategy metadata record is labeled `MISSING / NO SELECTION RECORD`; no pose is fabricated.
- Local axes are always `X=red, Y=green, Z=blue`.
- Orientation/Fused/Top-score show a selected AnyGrasp candidate. OursV2 shows a synthetic human-retarget target labeled `HUMAN TARGET`.
- The old split-panel export remains under `outputs/keyframe_candidates_split_panels_v1/`.

## Video semantics and genuine missing inputs

- Every 4×5 video is H.264, `yuv420p`, 1920×1540, and 30 fps. Each cell preserves 480×270 content below a separate 38 px header.
- The episode target duration is the longer of Foundation replay and OursV2. Each stream is normalized over its full progress and freezes its final frame.
- AnyGrasp MP4s are derived only from existing D435 `grasp_result_*.png`; inference is not rerun.
- `place_bread_basket/id0,id1` lack D435 AnyGrasp and human-guided preview. The cells are `MISSING`; legacy wide-camera results are not substituted.
- `pnp_tray/id2,id3` lack Dense URDF-match-v2 raw and the adjacent legacy Dense repaint. The cells are `MISSING`; Dense results are not fabricated.
- The other eight episodes have all 17 video-source stages.

## Validation

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets
python3 -m json.tool outputs/keyframe_candidates/manifest.json >/dev/null
python3 -m json.tool outputs/keyframe_candidates/episode_batch_manifest.json >/dev/null
find outputs/keyframe_candidates -name pipeline_grid_4x5.mp4 -print0 | \
  xargs -0 -n1 ffprobe -v error -select_streams v:0 \
  -show_entries 'stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames:format=duration,size' -of json
for video in outputs/keyframe_candidates/*/id*/pipeline_grid_4x5.mp4; do
  ffmpeg -v error -i "$video" -f null -
done
```

The formal result contains 12 episodes, 152 640×576 strategy PNGs, 38 1280×1152 contact sheets, 12 primary videos, and 10 AnyGrasp MP4s derived from existing D435 PNGs. Pine2's default `python3` lacks OpenCV, so candidate export and image validation must use the `RoboTwin_bw` Python shown above.

## `pick_diverse_bottles/id0` V3 candidate-reuse videos

The six-panel candidate image is:

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/frame_000038/all_strategies_contact_sheet.png
```

The corresponding candidates were replayed by the planner without overwriting previous results. The isolated outputs are:

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v3_candidate_videos/
├── candidate_retarget_grid_2x2.mp4
├── candidate_retarget_grid_2x2_config.json
├── candidate_retarget_grid_2x2_manifest.json
├── pipeline_grid_4x5_v3_candidates.mp4
├── pipeline_grid_4x5_v3_candidates_config.json
└── pipeline_grid_4x5_v3_candidates_manifest.json
```

The 2x2 video contains Orientation, Fused, Top-score, and OursV2. The 4x5 video retains Human RGB, HaMeR, inpainting, FoundationPose, Foundation replay, AnyGrasp, Dense V2, OursV2, and its matched repaint. No new Stage-2 repaint was generated for Top/Orientation/Fused, so their adjacent cells are explanatory cards; historical repaints are not mispaired with the new candidates.

Method videos are normalized over full progress to 21.4 seconds: Orientation/Fused are 10.3 seconds, Top-score is 10.5 seconds, and OursV2 is 21.4 seconds. Both outputs are H.264, `yuv420p`, 30 fps, and pass full decode. Top-score has a `53.6 mm` final left-arm action miss, explicitly recorded in the header and manifest.
