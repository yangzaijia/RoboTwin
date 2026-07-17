# Current Feature Summary

## Current main line

- The repository default remains the latest v1.x iteration. Foundation, AnyGrasp, OursV2, Dense Replay, Piper IK V3, and PiperCanonicalTCP-v1 are separate experiment lines.
- `PiperCanonicalTCP-v1` is the current Real-Piper-TCP comparison entry and does not modify OursV2.

## Added in this change

- Canonical `robot_replay` candidates now have an explicit camera-up equivalent-pose constraint: blue local `+Z` remains the approach axis, green local `+Y` is the jaw-opening axis, and red local `+X = +Y x +Z` is the opening--approach-plane normal. The rule chooses between `R` and `R @ diag(-1,-1,+1)` so red points toward world `+Z`.
- `--candidate_camera_forward_axis local_z --candidate_camera_top_axis x` acts only when explicitly requested. Legacy defaults remain `local_x/top=z`; historical wrapper behavior and OursV2 are unchanged.
- The `pick_diverse_bottles/id0` V4 2x2 is under `paper_qualitative_assets/.../id0/v4_camera_up_candidate_videos/candidate_retarget_grid_2x2_camera_up_v4.mp4`. Orientation/Fused flip both left keyframes and neither right keyframe; Top-score flips only left frame 38. Every applied flip changes local `+Z` by 0 degrees.
- V4 fixes only the redundant wrist-roll branch; it does not make single-seed Cartesian IK deterministic. Orientation completes the sequence with recorded left-arm misses. Top-score safely stops after a `35.7 mm` right grasp miss and freezes its final frame. A three-replan retry was worse and is excluded from the deliverable.
- The `pick_diverse_bottles/id0` approach-axis Orientation, Fused, and canonical Top-score selections now have isolated planner replays. The wrapper accepts `--reuse_preview_candidate_group=orientation|fused` while retaining `orientation` as its default.
- New paper assets include a 2x2 strategy-execution video and a 4x5 full-pipeline video with separate headers. Orientation/Fused succeed; Top-score has a `53.6 mm` left-arm action miss that is explicitly labeled. Historical Stage-2 repaints are not paired with the new candidates.
- Planner targets, current readback, reach checks, and visualization all use `T_W_RTCP`.
- SAPIEN `L6_SIM` and CuRobo/server `L6_URDF` share an origin but differ by exact local-axis `Ry(+pi/2)`. Adapted same-q FK error is below `7.5e-8 m / 0.000016 deg`.
- The server tool remains literal `T_L6URDF_RTCP = Ry(-1.57) @ Tx(0.19)`. Preview `CGRASP -> RTCP` remapping is a separate transform.
- Corrected same-q OursV2 TCP versus Real TCP has about `70.0001 mm` mean/max distance on both arms: the 12 cm versus 19 cm difference along the shared forward axis. The old 224.6 mm conclusion is invalid.
- EE-pose comparison supports Orientation, Fused, and Top-score. All three strategies plus corrected joint comparison pass media, ffprobe, and visual QA on `pnp_bread/id8/left`.
- A direct three-chain control comparison is now available. Joint mode applies the same Piper real q to measured Piper endPose, the OursV2 0.12 m TCP, and the Canonical 0.19 m RTCP. EE-pose mode applies the same Piper real `T_B_RTCP` target to OursV2's legacy numeric-link6 pass-through and Canonical server inverse-tool IK, then evaluates both as physical RTCP.
- In the eight-frame `handover_bottle/episode0` smoke, Canonical same-q position error is `9.77/9.59 mm` left/right. Canonical EE-pose IK is `0.011/0.004 mm`, while legacy OursV2 semantics are about `195 mm`. Both 1920x1080 MP4s pass H.264/yuv420p/full-decode checks and visual QA.
- The real-control raw manifest is now audited at six tasks x five episodes. All 30 have nonempty D435, both wrist cameras, both jointState streams, and both endPose streams. This is a different sample population from the AnyGrasp six-by-five foundation IDs.
- A 6 tasks x 5 episodes manifest, isolated batch orchestrator, and tmux commands are ready. Strategy IK misses preserve videos and failure TSV entries without fake SUCCESS markers.
- Canonical MP4 outputs now have uniform H.264/`yuv420p`/faststart post-processing with strict atomic-transcode auditing. The 186 `mpeg4` files in the 2026-07-15 batch are converted, and all 258 final files pass full decode. Joint summaries also record the OursV2 human-replay input and simulated head-camera provenance explicitly.
- Selection Strategy Audit V4 and Dense Replay URDF-match v2 remain separate historical lines.

## Reading order

1. `README.en.md`
2. `CURRENT_FEATURE_SUMMARY.en.md`
3. `VERSION_SUMMARY.en.md`
4. `PIPER_CANONICAL_TCP_V1.en.md`
5. `COMMANDS/piper_canonical_tcp_v1.en.md`
6. `SELECTION_STRATEGY_AUDIT_V4.en.md`

## 2026-07-16 addendum

- Canonical Human Replay maps human/CGRASP local axes explicitly to RTCP, forces final `target_retreat=0`, and retains only the 0.12 m pregrasp on local RTCP +X.
- `canonical_four_method_d435.mp4` compares four Canonical methods; `canonical_vs_legacy_five_method_d435.mp4` appends an explicit 0.12 m Legacy retreat baseline. The manifest records source semantics and video properties.
- `run_ik_logic_grid.sh` is upgraded to a 2x4 semantic-source V2. The top row restores original Legacy candidate offsets, Human retreat, and EE reach; the bottom row converts the same candidate or Human center to Canonical RTCP. This is a native-pipeline comparison, not a one-variable link6 ablation.
- The earlier five-way video is not a complete Legacy/Canonical 2x4. The formal old Human Replay records 0.14 m retreat; the five-way 0.12 m value is an explicit ablation.
- Conclusions from the old `outputs_ik_logic_grid_20260716` V1 are withdrawn. V1 removed the Legacy `-0.05 m @ local +Z`/Human 0.14 m adapters and incorrectly assumed the Human remap label affected reuse-plan-summary. Corrected output is under `outputs_ik_semantic_grid_v2_20260716`.
- The `handover_bottle/id1` V2 audit has zero world-xyz delta for every semantic source and at most `4.2e-16` axis error. Legacy Orientation/Top targets exactly match historical outputs. Canonical Human completes the internal handover, although the generic summary still returns failure for an earlier action miss. The final 1920x648, 265-frame video passes full decode and visual QA.
- Quick references: `OUTPUTS_REAL_CONTROL_COMPARE_GUIDE.en.md` and `PIPER_CANONICAL_REPLAY_METHOD_COMPARE.en.md`.

## 2026-07-16 paper qualitative asset addendum

- The Dense URDF-match-v2 4x5 grid now places titles in separate 38 px headers. Video content remains 480x270 per cell, making the final output 1920x1540; the former title-overlay version is preserved separately.
- Paper assets now cover 6 tasks × 2 episodes: 38 interaction keyframes produce 152 four-strategy images and 38 contact sheets. Each `<TASK>/id<ID>/` directory also contains its episode-specific 4×5 video, config, manifest, and README. LEFT/RIGHT/BOTH are drawn dynamically from keyframe metadata. OursV2 is a `HUMAN TARGET`, not an AnyGrasp candidate, and the old split-panel version remains separate.
- All twelve 4×5 videos are H.264/yuv420p, 1920×1540, 30 fps, and full-decode clean. Genuine omissions remain `MISSING`: D435 AnyGrasp/human-filtered for `place_bread_basket/id0,id1`, and Dense-v2/legacy repaint for `pnp_tray/id2,id3`. Nothing is cross-paired or fabricated.
- See `COMMANDS/paper_qualitative_assets.en.md` for reproduction and validation.
