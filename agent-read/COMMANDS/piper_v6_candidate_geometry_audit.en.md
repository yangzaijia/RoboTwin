# Piper V6 candidate-geometry audit

## Purpose

Read raw AnyGrasp, V6 `plan_summary.json`, the Foundation background, and object spatial anchors to produce one 2x3 candidate board per keyframe. The exporter never invokes IK, planning, or execution and never overwrites historical assets.

Panels are: raw dense candidates, V6-selected raw AnyGrasp poses, V6 stored `robot_replay` rotation, current `-5 cm @ stored +X` target, raw-center to object-anchor distance, and raw-versus-current-target overlay.

## Parameter template (not directly runnable)

```bash
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python \
  /home/zaijia001/ssd/RoboTwin/code_painting/export_v6_candidate_geometry_audit.py \
  --config <AUDIT_CONFIG_JSON> \
  [--dry-run] [--overwrite]
```

## Runnable example

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python \
  code_painting/export_v6_candidate_geometry_audit.py \
  --config /home/zaijia001/ssd/data/piper/paper_qualitative_assets/piper_v6_candidate_geometry_audit.json \
  --dry-run
```

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python \
  code_painting/export_v6_candidate_geometry_audit.py \
  --config /home/zaijia001/ssd/data/piper/paper_qualitative_assets/piper_v6_candidate_geometry_audit.json \
  --overwrite
```

Formal output is under:

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v6_red_forward_camera_back_up_candidate_videos/candidate_audit_v6
```

`manifest.json` records per-frame candidate IDs, raw/target distances to each object anchor, panel paths, board dimensions, and SHA-256 hashes. An anchor is the object-pose origin rather than the nearest surface; a tall-bottle top grasp can be far from the anchor without necessarily being off-object, so interpret the number together with the projection.
