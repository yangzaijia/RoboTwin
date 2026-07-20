# Piper Gripper Orientation Rules

## 2026-07-20 V8 authoritative chain (corrects V7's IK-boundary interpretation)

- AnyGrasp raw: red `+X` approach, green `+Y` opening, blue `+Z` plane normal.
- robot_replay canonical: blue `+Z = raw +X` approach, green `+Y = raw +Y` opening, and `-red -X = raw +Z` plane normal.
- Raw and canonical are two bases for the same physical gripper, not a physical 90-degree gripper rotation. Their silhouettes must overlap when rendered with their respective `local_x` and `local_z` actors.
- Candidate remapping expresses the canonical task target in Piper's physical gripper axes. The Curobo-to-SAPIEN link6 adapter maps solver and renderer model frames. Their semantics are independent and the correct chain applies each exactly once.
- The 0515 camera-back direction is raw/Piper blue `+Z`; an upward-facing camera requires that blue axis to point downward in world. Equivalent parameters are `forward=local_x, top=z, sign=-1`, and target/pregrasp offsets follow raw/Piper local X.
- V6's `robot_replay rotation + local-X forward` is a historical error. Successful execution only proves that the incorrect target was reachable.

The V7 audit measures `0 deg` for all three basis mappings, so the image remains correct. Its execution video did not convert the canonical target to the physical Piper TCP and is not valid execution evidence. See `COMMANDS/candidate_frame_contract_v8.en.md`.

## Current Takeaway

For the current `pnp_star_pear_hamer_output_v2/hand_detections_0.npz` and calibrated `PiperPika` scene, the RGB axes in the debug boards can be read as:

- Red `+X`: a side/normal axis derived from the finger skeleton plane, not the main approach axis.
- Green `+Y`: thumb-tip to index-tip direction, closest to the gripper opening axis.
- Blue `+Z`: computed by `X cross Y`, currently closest to the gripper approach direction.

So your observation that blue is the forward/approach axis, green is the opening axis, and red is the remaining side axis matches the current code and visualization.

## Why Recent Debug Runs Defaulted To Left Hand

The recent debug wrappers default to:

- `ARM=left`
- or `ARMS=left`

This was only to reduce variables while debugging axis semantics. Single-arm IK is faster and easier to interpret. The tools are not left-hand only.

Use:

```bash
ARM=right ...
```

or:

```bash
ARMS=right ...
```

For both arms:

```bash
ARMS=both ...
```

Running both arms can make the board harder to read because one unreachable side may dominate the status. The recommended flow is left first, then right separately.

## HaMeR / NPZ Gripper Local Axes

Main code:

- `code_painting/render_hand_retarget_r1_npz.py`
- `calc_gripper_pose_from_keypoints(...)`

If the NPZ contains `left_gripper_rotation_matrix` / `right_gripper_rotation_matrix`, the script uses those directly. Otherwise it recomputes the same convention from keypoints.

Formula:

```text
gripper_position = 0.5 * (thumb_tip + index_tip)

+Y = normalize(thumb_tip - index_tip)
temp = index_joint - index_tip
+X = normalize(cross(temp, +Y))
+Z = normalize(cross(+X, +Y))

rotation_matrix = [ +X  +Y  +Z ]  # columns are local x/y/z axes
retreat_position = gripper_position - retreat_distance * +Z
```

Interpretation:

- `+Y` is the fingertip-to-fingertip direction, so it is closest to the opening axis.
- `+Z` is used for retreat: `retreat = center - d * Z`, so `+Z` points from the retreat/wrist side toward the gripper center/approach side.
- `+X` completes the right-handed frame and is closer to a side/normal axis.

## Orientation Fix Order

Each frame starts from `rotation_cam`.

Code:

- `remap_target_rotation(...)`

Formula:

```text
R_cam_fixed = R_cam * R_post * R_remap
```

Where:

- `R_cam`: HaMeR/NPZ gripper rotation.
- `R_post`: command-line `--stored_orientation_post_rot_xyz_deg RX RY RZ`.
- `R_remap`: fixed axis remap from `--orientation_remap_label`.

This is right multiplication, so `R_post` and `R_remap` act in the local gripper frame.

## Head Camera To World

Code:

- `camera_to_world_pose(...)`

Current calibrated command values:

```text
--camera_cv_axis_mode legacy_r1
--head_camera_local_pos 0.107882 -0.2693875 0.464396
--head_camera_local_quat_wxyz 0.85401166 0.01255256 0.51885652 -0.0359783
```

Formula:

```text
pos_world = p_head_world + R_head_world * C_legacy * pos_cam
R_world = R_head_world * C_legacy * R_cam_fixed
```

`legacy_r1` matrix:

```text
C_legacy =
[[ 0,  0,  1],
 [-1,  0,  0],
 [ 0, -1,  0]]
```

In the Piper dual-arm scene, the head camera is fixed relative to the left base:

```text
world_T_head = world_T_left_base * left_base_T_head_camera
```

## Piper Base And Dual-Arm Placement

Current config:

- `robot_config_PiperPika_agx_dual_table.json`
- `dual_arm_embodied=false`
- `embodiment_dis=0.60`

The scene loads two independent Piper instances:

```text
left_base  ~= [-0.3, -0.25, 0.75]
right_base ~= [ 0.3, -0.25, 0.75]
base_quat  = [0.70710678, 0, 0, 0.70710678]
```

Each target is converted from world to the corresponding arm base:

```text
target_base = inv(world_T_arm_base) * target_world
```

## Gripper Target To Piper Link6 / URDFIK

Key code:

- `render_hand_retarget_piper_dual_npz_urdfik.py`
- `_target_tcp_world_to_ee_base(...)`
- `envs/robot/robot.py`
- `_trans_from_gripper_to_endlink(...)`

Piper URDFIK solves:

```text
base_link -> link6
```

Before IK:

```text
target_pose_base = world_pose_to_base_pose_for_arm(target_world, arm)
target_pose_ee = robot._trans_from_gripper_to_endlink(target_pose_base, arm)
```

Current config values:

```text
gripper_bias = 0.12
delta_matrix = I
global_trans_matrix = diag(1, -1, -1)
```

Inside `_trans_from_gripper_to_endlink(...)`:

```text
position += R_gripper * [0.12 - gripper_bias, 0, 0]
R_ee = R_gripper * inv(delta_matrix)
```

With the current config:

```text
position offset = 0
R_ee = R_gripper
```

So in the current `PiperPika` setup, the pose sent to URDFIK is effectively the retarget target pose itself.

## Important Frame Asymmetry

`get_left_tcp_pose()` / `get_right_tcp_pose()` read back TCP through `_trans_endpose(..., is_endpose=True)`:

```text
R_tcp_readback = R_link6 * global_trans_matrix * delta_matrix
```

Currently:

```text
global_trans_matrix = diag(1, -1, -1)
delta_matrix = I
```

So the readback TCP frame has flipped local Y/Z relative to `link6`.

However, `_trans_from_gripper_to_endlink(...)` currently applies only `inv(delta_matrix)` when feeding the IK target, not the inverse of `global_trans_matrix`.

Practical impact:

- The target axis actor shows the retarget target axes.
- URDFIK receives nearly the same target axes.
- Post-execution debug from `get_*_tcp_pose()` may include an extra `diag(1,-1,-1)` frame conversion.

Use target-axis boards for axis semantics. Treat post-execution TCP frame comparisons with this frame asymmetry in mind.

## Debug Recommendation

Current observations imply:

- HaMeR/recomputed gripper blue `+Z` is closest to approach direction.
- Green `+Y` is closest to opening direction.
- Robot/IK conventions do not naturally assume that `+Z` is the approach axis.

Recommended sequence:

1. Use `run_piper_retarget_postrot_board_video.sh` with `CASE_MODE=standard`.
2. Expand to `CASE_MODE=axis90`.
3. Run longer sequences or right-hand checks only for visually plausible candidates.
4. If a candidate looks right but succeeds rarely, tune `TARGET_DY/TARGET_DZ` and the IK initial state before continuing to scan more rotations.

## 2026-07-17: camera-up rule for canonical local-Z approach (V4; 0515 mount criterion corrected by V5)

> Note: the local-`+X`-up conclusion below is retained only as V4 history. The 0515 calibration places the wrist camera primarily on the link6 local `-X` side; formal V5 outputs use the `-X` mount-up rule at the end of this section.

Canonical `robot_replay` candidate axes are:

```text
local +Z (blue)  = gripper approach axis
local +Y (green) = parallel-jaw opening axis
local +X (red)   = (+Y) x (+Z), the opening--approach-plane normal
world +Z         = up
```

The discrete preference that keeps the wrist-camera/top side above the wrist is therefore:

```text
dot(R[:, 0], world_up) >= 0
```

A parallel-jaw gripper may exchange its fingers without changing the physical grasp. Canonical local-Z mode compares:

```text
R_base = R
R_flip = R @ diag(-1, -1, +1)
```

`R_flip` is a 180-degree roll about local `+Z`: it preserves the blue approach axis exactly and flips only red/green. The first keyframe establishes the upward branch; later keyframes select between the two equivalent branches for rotational continuity. `plan_summary.json` records `original_top_axis_up_dot`, `top_axis_up_dot`, `camera_up_flip_applied`, `forward_axis_change_deg`, and the selection mode.

Do not reuse legacy `diag(+1,-1,-1)` for canonical local-Z candidates. That matrix rolls about local `+X`; it is correct for the historical local-X-forward contract but reverses canonical local `+Z`. The implementation therefore adds explicit `--candidate_camera_forward_axis=local_x|local_z`, retaining `local_x` as the backward-compatible default.

This rule only resolves the parallel-jaw wrist-roll ambiguity. It does not change candidate identity, approach direction, or target position, and it does not replace IK reachability or collision checks. OursV2 human-target replay does not use this AnyGrasp-candidate post-processing.

## ~~2026-07-17: V5 calibrated camera mount side and link6 adapter~~ (withdrawn)

> V5 treated wrist-camera mount translation as camera orientation and mislabeled Piper AnyGrasp forward as local `+Z`. The text below is retained only to reproduce old V5 outputs and is not the current axis rule.

The 0515 wrist extrinsic translations in link6 local coordinates are left `[-0.0743,+0.0207,+0.0936] m` and right `[-0.0600,-0.0274,+0.0894] m`, placing the camera body primarily on local `-X`. The correct mount-up criterion is:

```text
camera_mount_normal = -R[:, 0]
dot(camera_mount_normal, world_up) > 0
```

Debug colors remain red/green/blue for local `+X/+Y/+Z`. A downward red `+X` arrow is expected when the camera side is upward and must not be interpreted as an upside-down camera.

Candidate targets also require two independent Piper adapters before IK:

```text
Piper replay global axis conversion
R_sapien_link6 = R_curobo_link6 @ Ry(-90 deg)
```

V5 uses `--candidate_camera_top_axis x --candidate_camera_top_axis_sign -1`, `--piper_apply_global_trans_to_ik 1`, and `--piper_apply_curobo_to_sapien_link_rotation 1`. To remove V4 Cartesian-waypoint wrist-branch jumps, formal routes use stage-endpoint IK, 40-waypoint joint interpolation, and 64 seeds. The constrained Top-score run additionally uses `joint_continuity`, while the successful Orientation/Fused run retains `pose_error`. Camera-up does not imply executability: a candidate at a hard joint limit must be replaced by the next candidate in the same strategy ranking that satisfies mount-up, IK, and joint-limit feasibility, and the output must be labeled constrained/feasible.

## 2026-07-18: V6 formal red-forward and camera-back-up rule

Candidate geometry and rendered colors establish the actual contract: red `+X` is gripper forward/approach, green `+Y` is parallel-jaw opening, and blue `+Z` is the normal of that plane. A 0515 camera translation says where the camera is mounted, not where it points, so the V5 `-X` mount-normal inference is invalid.

V6 preserves red `+X` and only chooses between the two 180-degree finger-swap branches about red:

```text
forward = R[:, 0]                 # red +X
camera_back_or_plane_normal = -R[:, 2]
dot(camera_back_or_plane_normal, world_up) >= 0
```

The first keyframe selects a `-blue up` branch. Later keyframes must first hard-filter for `top_axis_up_dot >= 0`, then minimize rotation from the previous keyframe. Camera-up cannot remain a continuity tie-breaker, because that permits the 6--10 second transition to flip back to the inverted branch. Formal parameters are `--candidate_camera_forward_axis local_x --candidate_camera_top_axis z --candidate_camera_top_axis_sign -1`; candidate offset and pregrasp also use local `+X`.

Feasible V6 IDs for `pick_diverse_bottles/id0` are K1 `L16/R18` and K2 `L6/R5`. Orientation, Fused, and constrained Top-score converge to this same set after axis, camera-back-up, IK, and joint-limit constraints. Old V5 media remains available but must not be used to infer the axis definition.

## 2026-07-18: V6 candidate-geometry recheck (correction to the formal rule above)

The earlier V6 conclusion inferred red-axis semantics only from the rendered actor and did not inspect the candidate input's `candidate_frame_mode`. Matrix-level verification shows that V6 still reuses `robot_replay` candidates:

```text
robot_replay local +Z = raw AnyGrasp local +X approach
R_v6_stored = R_anygrasp_raw @ RAW_TO_CANONICAL
rotation_distance(R_v6_stored, R_anygrasp_raw) = 90 deg
```

Treating stored red `+X` as forward therefore uses a canonical side/normal axis as approach, and the `-0.05 m` offset follows that wrong stored X. For frame 78 right candidate `#5`, raw-center distance to the right-bottle anchor is `4.68 cm`; the current V6 target is `9.62 cm` away.

The V6 ordering rule—hard-filter camera-up before continuity—remains algorithmically valid. The error is applying it to mixed local-axis semantics. A successor must choose one contract end-to-end across selection, offset, camera-up, actor rendering, and IK: retain `anygrasp_raw` with red X approach, or retain `robot_replay` with blue Z approach. Current V6 is historical diagnostic output, not the final axis conclusion.
