# Long-lived Decisions

## 2026-07-14: keep the Dense Replay correction isolated

- Preserve the legacy renderer, runner, and paper assets so historical experiments remain reproducible.
- Name the new implementation `Dense Replay URDF-match v2` and write it under the separate `h2_pure_d435_urdfmatch_v2` output root.
- Keep joint order as `joint1..joint6`; fix the constant error with an explicit frame adapter, not joint swapping or manual joint offsets.
- Interpret the HaMeR fingertip midpoint consistently as TCP; link6 is only an internal IK target frame.
- Dense remains the dense-retargeting baseline. Human orientations unreachable by the robot are not presented as an Ours-v2 capability.
- Six-task batch outputs remain under the same isolated v2 root, with episode-level completeness checks for safe resume; no v1 file is created or overwritten.
- v2 raw replay must not be silently mixed with existing v1 Stage-2 repaint/HDF5 artifacts. A paper diagnostic may display them side by side only with an explicit `NOT V2` label; training-data promotion requires rebuilding the full downstream chain under a new identifier.

## 2026-07-14: keep Selection Strategy V4 read-only

- Preserve legacy OursV2, Orientation, Fused, and Top-score algorithms, summaries, and visualizations; V4 never writes corrections back into historical results.
- Treat `plan_summary.json -> selected_candidates_by_executed_arm` as the actual Top-score selection. Legacy rank previews remain only as evidence of the historical mismatch.
- Preserve raw/legacy Top-score and the canonical reconstruction together. Label the canonical pose audit-only rather than presenting it as historical execution.
- When resolved frames differ, use separate Foundation background columns; never silently project a pose onto another frame.
- Do not displace identical Orientation/Fused poses for visualization. Use thick-solid/thin-dashed lines and distinct markers at the same pose so data semantics remain unchanged.
- Use `<TASK>/id<ID>_keyframe_<FRAME>_*` task outputs without an episode directory; keep the old nested output as a separate rollback backup.
- Keep batch PNG/JSON/reports ignored by Git, and version only the two scripts and bilingual documentation.

## 2026-07-15: PiperCanonicalTCP-v1

- Keep OursV2 fully independent; new Real-TCP semantics live only in `piper_canonical_tcp_v1/`.
- Frame names must distinguish `L6_SIM`, `L6_URDF`, `RTCP`, and `CGRASP`, with explicit world/local axis labels.
- Use the runtime same-q exact signed-axis matrix for `T_L6SIM_L6URDF`. Keep literal server `-1.57` and `0.19` instead of substituting an ideal angle.
- Orientation/Fused convert canonical preview axes back to raw/RTCP; Top-score raw source uses identity. The two numerically identical 90-degree matrices retain separate semantics.
- Continue the batch after a strategy IK miss and record failure. Videos may be composed, but no failed strategy receives a SUCCESS marker.
- Version code and tests; keep smoke, batch videos, logs, and large artifacts ignored.
- Canonical generated videos use the VS Code/Chromium-decodable contract: H.264, `yuv420p`, and faststart. OpenCV-readable does not imply browser-compatible; validate temporary format, geometry/frame count, and full decode before replacement.
- Video provenance must distinguish raw/preview D435 input, a simulated head camera driven by D435 calibration, and simulated third/wrist/composed views. A `d435` path component alone does not make every MP4 raw D435 footage.

## 2026-07-16: keep the three-chain real-control comparison isolated

- Do not modify OursV2. Its branch must faithfully preserve the legacy numeric-pose-to-link6-IK semantics.
- Joint and EE-pose comparisons use common real q and common real `T_B_RTCP`, respectively. A foundation candidate strategy must never be presented as a controller comparison.
- Do not evaluate an IK q trace with OursV2's own TCP definition. Convert both q traces to physical Canonical RTCP before comparing against measured endPose.
- Preserve failed-arm masks and exclude failures from curves; never present the reference-q fallback as a successful result.
- Write only to isolated `outputs_real_control_compare_20260716`; preserve the existing Canonical candidate batch and V1-V5 videos.
- Define the requested four methods as four Canonical methods (Orientation/Fused/Top-score/Human Replay). Legacy OursV2 retreat is only a fifth baseline.
- Canonical Human Replay fixes final `target_retreat_m` at zero while retaining the 0.12 m pregrasp. The Legacy runner requires an explicit retreat so the current zero default and historical 12 cm experiment cannot be confused.

## 2026-07-16: paper-grid headers and keyframe-candidate images

- Preserve all 480x270 video content and add a separate 38 px header above each cell, making the 4x5 grid 1920x1540. Preserve the former title-overlay version as a separate backup.
- Paper candidate images draw only the Selection Pose recorded by V4 metadata. Planner offset, retreat, pregrasp, and TCP compensation are excluded so strategy selection is not conflated with downstream planning.
- Use one requested-keyframe replay background per strategy/keyframe and overlay both grippers on it. Mark a dual-arm keyframe `BOTH`, and list LEFT/RIGHT candidate identities on the second header line. Local axes remain X red, Y green, Z blue.
- The OursV2 point is a synthetic human-retarget target and must be labeled `HUMAN TARGET`; only Orientation/Fused/Top-score are AnyGrasp candidates.

## 2026-07-16: group the 6×2 paper batch by episode

- Fix the selection at handover 1/3, pick 0/1, place 0/1, pnp_bread 7/8, pnp_tray 2/3, and stack 0/1. Put each episode's keyframe images and 4×5 video in the same `<TASK>/id<ID>/` directory.
- Derive image scope from V4 metadata: LEFT/RIGHT draw only that arm and BOTH draws both arms on one replay background. A missing strategy record is labeled `MISSING`; no default pose is invented.
- Derive a D435 AnyGrasp video only from D435 PNGs for the same episode. Do not replace missing `place_bread_basket` D435 output with legacy wide-camera output, and do not present V1 or another episode as missing `pnp_tray` Dense-v2.
- Record large source videos as absolute paths in configs/manifests. An episode package stores generated images, derived AnyGrasp, the composed video, and metadata rather than copying source videos.

## 2026-07-17: choose the canonical camera-up branch about local Z

- Canonical `robot_replay` candidates define local `+Z` as approach, local `+Y` as jaw opening, and local `+X=+Y x +Z` as the camera/wrist-top normal.
- Camera-up chooses only between the parallel-jaw-equivalent `R` and `R @ diag(-1,-1,+1)`, requiring nonnegative local-`+X` dot world-`+Z`. The legacy local-X-forward `diag(+1,-1,-1)` must not be reused.
- The new axis arguments are explicit. Defaults remain `local_x/top=z`, preserving historical planners, OursV2, and candidate ranking.
- Camera-up resolves a discrete roll ambiguity; it does not reinterpret an IK miss as a frame failure. Paper videos retain failure labels and V4 outputs remain isolated from V3.

## 2026-07-17: formal V5 mount-up uses the calibrated 0515 camera-side `-X`

- The preceding local-`+X`-up rule is retained only as V4 history and must not be used for the 0515 wrist camera. Formal mount-up is `dot(-R[:,0], world +Z)>0`; axis colors remain X red, Y green, Z blue.
- The Curobo-link6 to SAPIEN-link6 local `Ry(-90 deg)` is a frame adapter independent of camera-up. Candidate IK must explicitly apply both the Piper global-axis conversion and this link adapter.
- Formal qualitative replays use stage-endpoint IK plus joint-space interpolation, not Cartesian waypoint IK with an approximately 180-degree relaxed rotation threshold.
- A selected pose must pass mount-up, IK, and physical joint-limit checks. If raw top-1 lies on a hard limit, the next feasible candidate in the same strategy ranking may be used only when the title, config, and manifest label the result constrained/feasible.
- V5 writes to an isolated output and never overwrites V4, OursV2, or legacy strategy results. With object collisions disabled, V5 is qualitative retargeting evidence, not a physical grasp-success benchmark.

## 2026-07-20: candidate coordinates permit exactly one frame adapter

- The preview source and planner local-axis contract must be declared separately. Non-legacy commands may not infer a frame from a path name or actor color.
- A robot_replay candidate remains canonical `+Z` forward in candidate space. The Curobo-to-SAPIEN link6 `Ry(-90 deg)` is applied once, only at the IK boundary.
- Raw/canonical comparison images must use the correct actor for each frame and verify physical equivalence through silhouette overlap and mapped-axis errors; a basis change must not be drawn as a physical rotation.
- Historical V6 remains untouched. V7 uses an isolated output, and collision-disabled execution is coordinate-chain/reachability evidence only.

## 2026-07-20: V8 separates candidate basis conversion from the link6 model adapter

- Withdraw the V7 claim that candidate remapping and the Curobo-to-SAPIEN link6 adapter are duplicate compensation. The former defines the physical Piper TCP axes for a task target; the latter reconciles two URDF link6 model frames.
- The main chain is `robot_replay -> anygrasp_raw/Piper +X`, followed by the same Piper URDFIK with global/link6 adapters enabled.
- The current comparison executes each strategy's raw top selection only. IK-feasible reranking, replacement candidates, and automatic fallback are deferred. Preserve unreachable failures and short videos; never manufacture success with a 180-degree orientation tolerance.

## 2026-07-23: rigid K2 transport is an opt-in action mode

- Keep `independent_keyframe_candidate` as the historical V8 default. Enable the new behavior only with `--action_target_mode rigid_object_transport`; never overwrite V8 or OursV2.
- Candidate basis conversion and K1 targets remain unchanged. After K1 arrival and object attachment, measure `T_EE_object` from the current EE/link6 origin and current actor pose, then convert the FoundationPose K2 object pose into an EE target.
- Do not send a desired TCP position directly as the current Piper planner target. This chain's target point is the EE/link6 origin with physical gripper-axis orientation. Treating it as TCP creates an approximately 9–12 cm fixed offset.
- Rigid transport is not IK-feasible candidate filtering. If Top-score fails K1 reach, preserve the failure and stop; K2 correction must not hide a K1 failure.
- V9 remains on the 0515 Piper/OursV2 URDFIK path and never switches to the Canonical 19 cm RTCP. Although the config has `gripper_bias=0.12 m`, `_trans_from_gripper_to_endlink` contributes `0.12-gripper_bias=0` translation. Keep the 12 cm model bias, 12 cm pregrasp distance, and AnyGrasp `-5 cm` target offset explicitly separate.
- Export transform audits per method. Keep separate provenance sheets for Orientation and Fused even when their selections coincide; show `NOT EXECUTED` when Top-score never creates a rigid K2 target; never depict OursV2 as an AnyGrasp-remap chain.

## 2026-07-24: V9.1 rigid-transport frame follows planner-target semantics

- The rigid reference frame must match the planner target: use `ee` for the legacy Piper EE/link6 chain and `tcp` for the Canonical Real-TCP chain.
- The default remains `ee`, so historical V9 numbers and outputs do not change. Canonical runs must explicitly select `tcp`; an EE target must never be reinterpreted as RTCP.
- Record `0.12 m pregrasp`, the historical `0.14 m OursV2 target retreat`, the `0.05 m candidate offset`, and the `0.19 m Canonical tool transform` as separate quantities in configs, manifests, and documentation.
- The simulated gripper command is normalized to `[0,1]`. The current paper comparison uses `close=0.3`, meaning 30% of fully open width, not 0.3 meters.

## 2026-07-24: correct the V9.1 retreat and isolate the V9.2 17 cm tool experiment

- Apply the `oursv2-5` 5 cm addition only to the Orientation/Fused/Top-score V9 grasp targets. Their V8 targets already contain 5 cm, so the total retreat from the raw candidate center is 10 cm.
- Restore the fourth OursV2 pane to its original V9 14 cm human-target retreat, with no extra 5 cm.
- Canonical 17 cm is a run-scoped experimental override. It does not change the Piper server literal, the Canonical-v1 19 cm default, or prior V9.1 output.
- V9.2 keeps RTCP targets and candidates identical. The 17 cm value changes only the link6 IK target produced by the inverse RTCP tool transform.

## 2026-07-24: V9p is a clean render, not a new planning method

- V9p must reuse V9 candidates, IK, K1/K2 targets, retreat, and rigid-object-transport parameters. The only first-three-pane differences are `pure_scene_output=1` and `debug_visualize_targets=0`.
- Keep the historical OursV2 fourth-pane video unchanged rather than rerunning it solely for visual uniformity.
- The V9p compositor must verify that all first-three-pane summaries are pure-scene and reject invalid inputs.
- Deliver paper videos as H.264 Constrained Baseline, `yuv420p`, and faststart to avoid client-specific High Profile playback differences.
