# Current Feature Summary

## Current main line

- The repository default remains the latest v1.x iteration. Foundation, AnyGrasp, OursV2, Dense Replay, Piper IK V3, and PiperCanonicalTCP-v1 are separate experiment lines.
- `PiperCanonicalTCP-v1` is the current Real-Piper-TCP comparison entry and does not modify OursV2.

## Added in this change

- Added opt-in `--action_target_mode rigid_object_transport`. V8 K1 selection, the `robot_replay -> Piper physical` basis change, camera-up branch, `-5 cm @ local +X`, and IK settings remain unchanged. After actual K1 arrival, the planner measures `T_EE_object` from the current EE and object actor and constructs K2 as `T_W_EE2 = T_W_object2 @ inverse(T_EE_object)`.
- The audit confirms that legacy V8 uses a new independent K2 grasp after the object is already rigidly attached with the K1 relation, changing the gripper-to-object relation. The first V9 attempt incorrectly treated the planner target point as TCP and retained a 9–12 cm fixed error. Formal `v9_ee_rigid_object_transport_20260723` uses the EE/link6 target point; Orientation/Fused end with object errors of `7.8 mm / 6.0 deg` left and `4.7 mm / 1.9 deg` right.
- The new 2x2 video and four method-specific six-panel transform audits are published under `paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/`. Orientation, Fused, and Top-score each show their actual AnyGrasp selection through the fixed axis remap, camera-up branch, `-5 cm @ Piper local +X`, K1 IK target, and K2 action target. Orientation and Fused select the same candidates in this episode, so their geometry is identical. Top-score preserves its K1-right `33.24 deg` miss and explicitly marks panel six `NOT EXECUTED`. The separate OursV2 sheet documents the human-target branch and states that it does not use AnyGrasp remapping, camera-up, `-5 cm`, or V9 rigid transport.
- V9 uses the 0515 Piper/OursV2 URDFIK configuration family, not the Canonical 19 cm RTCP. The config has `gripper_bias=0.12 m`, while the pre-IK link6 translation is `0.12-gripper_bias=0`; V9 therefore does not add another 12 cm to its final IK target. The separate `approach_offset=0.12 m` is pregrasp-only, and `candidate_target_local_x_offset=-0.05 m` applies only to the AnyGrasp K1 target. Neither is a Canonical TCP transform. See `COMMANDS/rigid_object_transport_v9.en.md`.
- V8 corrects V7's conflation of two independent transforms: candidate-side `robot_replay -> anygrasp_raw/Piper physical TCP` is a task-target basis change, while the IK-side Curobo-link6 -> SAPIEN-link6 adapter maps between the solver and renderer URDF frames. The correct chain applies both, exactly once each.
- A `robot_replay` input uses canonical `+Z` approach. `swap_red_blue_keep_green` converts it to the Piper physical `+X` approach before the existing Piper URDFIK; the global and Curobo-to-SAPIEN link6 adapters remain enabled. There is no separate "canonical IK" solver.
- The physical-axis equivalence is `raw +X = canonical +Z`, `raw +Y = canonical +Y`, and `raw +Z = -canonical +X`. All three mapped-axis errors are `0 deg` on `pick_diverse_bottles/id0`; camera-back-up uses `-canonical X = raw +Z` toward world up.
- The V7 six-panel raw/canonical orientation correspondence remains valid, but the V7 four-view execution video used the wrong planner-target frame chain and is retained only as historical evidence. V8 fixes raw strategy candidates, performs no IK-feasible fallback, and preserves real failures under a strict 30-degree reach gate.
- V8 has run `pick_diverse_bottles/id0` with raw selections: Orientation/Fused both use K1 `L16/R5` and K2 `L14/R16`; left pregrasp misses at `35.44 deg`, while grasp/action complete. In the current 6x2 flat-release video, Top-score uses K1 `L8/R3` and K2 `L3/R2`; the K1 right grasp still ends with a `33.22 deg` rotation error and safely stops before close, so K2 is not executed. The native-speed 2x2 grid and manifest are under `paper_qualitative_assets/.../id0/v8_physical_axes_raw_strategy_videos/`.
- Added the read-only `overlay_v8_execution_pose_audit.py`. It reads the V8 `plan_summary.json` and `debug_execution_metrics.jsonl`, overlays the colored target C-gripper, white measured EE, and physical Piper `+X/+Y/+Z` RGB axes, and holds grasp/action arrival frames for one second. Flat outputs are `*_00b_retarget_2x2_v8_pose_audit.mp4`, `*_03_v8_video_matched_arrivals_2x3.png`, and `*_pose_audit_manifest.json`; historical `legacy_v3` images are not candidate-exact matches for this V8 video.
- Added the read-only `export_v8_video_matched_candidate_contact_sheets.py`. It projects the exact final candidate targets from V8 plan summaries onto the corresponding D435/Foundation frames and produces 2x3 sheets matching the old `all_strategies_contact_sheet.png` layout. The frame-38/frame-78 outputs for `pick_diverse_bottles/id0` are published under `matched_candidate_image_video_release_20260722/`; these sheets show planned targets, while the arrival sheet shows measured EE arrivals.
- The V6 candidate-geometry audit overturns the claim that V6 unified the AnyGrasp axis semantics. Input candidates remain `candidate_frame_mode=robot_replay`, where canonical blue `+Z = raw AnyGrasp +X approach`, but V6 consumes that same rotation as red `+X = forward`. Every selected V6 stored rotation is exactly `90 deg` from `anygrasp_raw`.
- V6 applies its `-0.05 m` candidate offset along stored red `+X`, not along raw AnyGrasp approach. For `pick_diverse_bottles/id0/frame78/right #5`, raw-center distance to the object anchor is `4.68 cm`, while the current target is `9.62 cm`. The V6 video therefore proves only that IK/joint execution can reach the incorrect target, not that the candidate-coordinate chain is correct.
- Added read-only exporter `code_painting/export_v6_candidate_geometry_audit.py`. For frames 38/78 it produces 2x3 boards containing raw dense candidates, selected raw poses, V6 stored remap, current `-5 cm` target, object-anchor distances, and a raw-vs-target overlay. It never invokes IK and never overwrites historical assets.
- Audit output is under `paper_qualitative_assets/.../id0/v6_red_forward_camera_back_up_candidate_videos/candidate_audit_v6/`. Both contact sheets are 1920x1152; frame 38 uses `L16/R18` and frame 78 uses `L6/R5`.
- The later-keyframe fix that hard-filters camera-up before continuity remains valid in isolation, but the local axis to which it applies must wait for a subsequent unified `anygrasp_raw` versus `robot_replay` contract. OursV2 is unchanged.
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
7. `COMMANDS/candidate_frame_contract_v8.en.md`
8. `COMMANDS/piper_v6_candidate_geometry_audit.en.md`
9. `COMMANDS/candidate_camera_mount_up_v6.en.md` (historical V6 reproduction with a known axis-semantic mix)

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

## Isolated V9.1 RTCP / OursV2+5 cm comparison

- `rigid_object_transport` can preserve either `EE→object` or `RTCP→object` according to target semantics. Legacy V9 remains EE by default; the new four-strategy Canonical comparison uses RTCP.
- The comparison fixes `pregrasp=0.12 m` and normalized gripper commands `open=1.0 / close=0.3`, preserving unreachable candidates without fallback.
- `v9-1_oursv2-5.mp4` now means that the first three AnyGrasp methods retreat another 5 cm from the old V9 grasp target, while the fourth pane preserves the historical OursV2 14 cm retreat without an extra 5 cm.
- New `v9-2_canonical.mp4` reuses unchanged RTCP targets and changes only the isolated active tool length from 19 cm to 17 cm. Canonical-v1 and the Piper server literal remain 19 cm by default.
- See `COMMANDS/planning_compare_v9_1.en.md` for generation, composition, and validation commands.

## V9p clean qualitative video

- Formal V9p has two videos: `v9p_oursv2.mp4` matches corrected `v9-1_oursv2-5`, and `v9p_canonical.mp4` matches the 17 cm `v9-2_canonical`.
- All four panes in both videos explicitly use `open=1.0 / close=0.3 / pure_scene_output=1 / debug_visualize_targets=0`. Candidates, prepared poses, stage targets, and reach/miss outcomes match the corresponding non-clean videos.
- Both videos use H.264 Constrained Baseline, `yuv420p`, and faststart. The earlier single original-V9 pure-scene experiment used default `close=0.0`; it remains legacy and is not formal V9p.
- See `COMMANDS/planning_compare_v9_1.en.md`.
